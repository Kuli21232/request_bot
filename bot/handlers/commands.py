"""Bot commands."""
import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from bot.database import AsyncSessionLocal
from bot.database.repositories.department_repo import DepartmentRepository
from bot.database.repositories.knowledge_repo import KnowledgeRepository
from bot.database.repositories.request_repo import RequestRepository
from bot.database.repositories.topic_repo import TopicRepository
from bot.database.repositories.user_repo import UserRepository
from bot.services.guidance_service import GuidanceService
from bot.services.notification_service import NotificationService
from models.enums import UserRole
from models.user import User

logger = logging.getLogger(__name__)
router = Router()


class RegisterTopicFSM(StatesGroup):
    waiting_name = State()
    waiting_sla = State()
    waiting_emoji = State()


def _is_staff(user: User | None) -> bool:
    return bool(user and user.role in (UserRole.agent, UserRole.supervisor, UserRole.admin))


async def _resolve_user(query: str, session) -> User | None:
    repo = UserRepository(session)
    matches = await repo.search_users(query, limit=5)
    return matches[0] if matches else None


def _format_user_line(user: User) -> str:
    role = user.role.value
    username = f"@{user.username}" if user.username else "без username"
    return f"• <b>{user.first_name} {user.last_name or ''}</b> — {username}, роль: {role}"


@router.message(CommandStart())
async def cmd_start(message: Message, db_user: User | None) -> None:
    name = db_user.first_name if db_user else message.from_user.first_name
    await message.answer(
        f"Привет, {name}!\n\n"
        "Я бот для разбора операционного потока, ответов на рабочие вопросы и профилей сотрудников.\n\n"
        "Что умею:\n"
        "/ask <вопрос> — ответить по базе знаний\n"
        "/guide <тема> — найти инструкцию\n"
        "/participants [поиск] — показать известных участников\n"
        "/profile <id|@username|имя> — открыть профиль сотрудника\n"
        "/watch <сотрудник> — подписаться на обновления профиля\n"
        "/my — мои задачи\n"
        "/help — полный список команд"
    )


@router.message(Command("help"))
async def cmd_help(message: Message, db_user: User | None) -> None:
    staff_block = (
        "\nДля исполнителей и руководителей:\n"
        "/note <сотрудник> | <текст> — оставить заметку в профиле\n"
        "/list_topics — показать обнаруженные топики\n"
        "/register_topic — привязать топик к отделу для shadow tasks\n"
    ) if _is_staff(db_user) else ""

    await message.answer(
        "Основные команды:\n"
        "/ask <вопрос> — ответ по базе знаний\n"
        "/guide <тема> — найти инструкцию или памятку\n"
        "/participants [поиск] — список известных участников\n"
        "/profile <id|@username|имя> — профиль сотрудника\n"
        "/watch <сотрудник> — подписаться на уведомления по профилю\n"
        "/unwatch <сотрудник> — убрать подписку\n"
        "/status <номер> — статус legacy-задачи\n"
        "/my — мои задачи\n"
        f"{staff_block}"
    )


@router.message(Command("ask"))
async def cmd_ask(message: Message, db_user: User | None) -> None:
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply("Напишите вопрос после команды, например: /ask как работает бот")
        return

    async with AsyncSessionLocal() as session:
        repo = KnowledgeRepository(session)
        service = GuidanceService(repo)
        answer = await service.answer(parts[1], audience=(db_user.role.value if db_user else "all"))

    lines = [answer["answer"]]
    if answer["sources"]:
        lines.append("\nИсточники:")
        lines.extend(f"• {source['title']}" for source in answer["sources"])
    await message.reply("\n".join(lines))


@router.message(Command("guide"))
async def cmd_guide(message: Message, db_user: User | None) -> None:
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply("Укажите тему, например: /guide профили сотрудников")
        return

    async with AsyncSessionLocal() as session:
        repo = KnowledgeRepository(session)
        articles = await repo.list_articles(
            published_only=True,
            search=parts[1],
        )
    if not articles:
        await message.reply("По этой теме пока нет инструкции в базе знаний.")
        return

    top = articles[:5]
    lines = ["Нашел подходящие инструкции:\n"]
    for article in top:
        lines.append(f"• <b>{article.title}</b>\n{(article.summary or article.body)[:180]}")
    await message.reply("\n\n".join(lines), parse_mode="HTML")


@router.message(Command("participants"))
async def cmd_participants(message: Message, db_user: User | None) -> None:
    if not _is_staff(db_user):
        await message.reply("Список участников доступен исполнителям и руководителям.")
        return

    parts = message.text.split(maxsplit=1)
    query = parts[1] if len(parts) > 1 else None
    async with AsyncSessionLocal() as session:
        repo = UserRepository(session)
        users = await repo.search_users(query, limit=15)

    if not users:
        await message.reply("Подходящих участников пока не нашел.")
        return

    lines = ["<b>Известные участники:</b>"]
    lines.extend(_format_user_line(user) for user in users)
    await message.reply("\n".join(lines), parse_mode="HTML")


@router.message(Command("profile"))
async def cmd_profile(message: Message, db_user: User | None) -> None:
    if not _is_staff(db_user):
        await message.reply("Профили сотрудников доступны исполнителям и руководителям.")
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply("Укажите сотрудника: /profile @username или /profile 15")
        return

    async with AsyncSessionLocal() as session:
        user_repo = UserRepository(session)
        knowledge_repo = KnowledgeRepository(session)
        target = await _resolve_user(parts[1], session)
        if target is None:
            await message.reply("Сотрудник не найден.")
            return
        notes = await knowledge_repo.list_profile_notes(target.id, limit=5)
        subscription = await knowledge_repo.get_subscription(db_user.id, target.id)

    lines = [
        f"<b>{target.first_name} {target.last_name or ''}</b>",
        f"ID: <code>{target.id}</code>",
        f"Username: @{target.username}" if target.username else "Username: не указан",
        f"Роль: {target.role.value}",
        f"Последняя активность: {target.last_active_at.strftime('%d.%m.%Y %H:%M') if target.last_active_at else 'нет данных'}",
        f"Подписка: {'включена' if subscription and subscription.is_active else 'нет'}",
    ]
    if notes:
        lines.append("\n<b>Последние заметки:</b>")
        for note in notes:
            author = note.author.first_name if note.author else "Система"
            lines.append(f"• {author}: {note.body[:160]}")
    else:
        lines.append("\nЗаметок по профилю пока нет.")
    await message.reply("\n".join(lines), parse_mode="HTML")


@router.message(Command("note"))
async def cmd_note(message: Message, db_user: User | None, bot: Bot) -> None:
    if not _is_staff(db_user):
        await message.reply("Заметки по профилям могут оставлять только исполнители и руководители.")
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or "|" not in parts[1]:
        await message.reply("Формат: /note @username | текст заметки")
        return

    query, note_text = [part.strip() for part in parts[1].split("|", maxsplit=1)]
    if not query or not note_text:
        await message.reply("Нужны и сотрудник, и текст заметки.")
        return

    async with AsyncSessionLocal() as session:
        target = await _resolve_user(query, session)
        if target is None:
            await message.reply("Сотрудник не найден.")
            return
        knowledge_repo = KnowledgeRepository(session)
        note = await knowledge_repo.add_profile_note(
            target_user_id=target.id,
            author_id=db_user.id,
            body=note_text,
            notify_target=False,
        )

    service = NotificationService(bot)
    await service.notify_profile_note(target_user=target, author=db_user, note_body=note.body, notify_target=False)
    await message.reply(
        f"Заметка добавлена в профиль <b>{target.first_name}</b>.\n"
        f"Чтобы смотреть обновления, используйте /watch {target.id}",
        parse_mode="HTML",
    )


@router.message(Command("watch"))
async def cmd_watch(message: Message, db_user: User | None) -> None:
    if not _is_staff(db_user):
        await message.reply("Подписки на профили доступны исполнителям и руководителям.")
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply("Укажите сотрудника: /watch @username")
        return

    async with AsyncSessionLocal() as session:
        target = await _resolve_user(parts[1], session)
        if target is None:
            await message.reply("Сотрудник не найден.")
            return
        repo = KnowledgeRepository(session)
        await repo.upsert_subscription(watcher_user_id=db_user.id, target_user_id=target.id, active=True)

    await message.reply(f"Подписка на профиль {target.first_name} включена.")


@router.message(Command("unwatch"))
async def cmd_unwatch(message: Message, db_user: User | None) -> None:
    if not _is_staff(db_user):
        await message.reply("Подписки на профили доступны исполнителям и руководителям.")
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply("Укажите сотрудника: /unwatch @username")
        return

    async with AsyncSessionLocal() as session:
        target = await _resolve_user(parts[1], session)
        if target is None:
            await message.reply("Сотрудник не найден.")
            return
        repo = KnowledgeRepository(session)
        await repo.upsert_subscription(watcher_user_id=db_user.id, target_user_id=target.id, active=False)

    await message.reply(f"Подписка на профиль {target.first_name} отключена.")


@router.message(Command("status"))
async def cmd_status(message: Message) -> None:
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("Укажите номер задачи: /status REQ-2025-00001")
        return

    ticket_number = args[1].strip().upper()

    async with AsyncSessionLocal() as session:
        repo = RequestRepository(session)
        request = await repo.get_by_ticket(ticket_number)

    if request is None:
        await message.reply(f"Задача <code>{ticket_number}</code> не найдена.", parse_mode="HTML")
        return

    status_labels = {
        "new": "Новая",
        "open": "Открыта",
        "in_progress": "В работе",
        "waiting_for_user": "Ожидает ответа",
        "resolved": "Решена",
        "closed": "Закрыта",
        "duplicate": "Дубликат",
    }
    priority_labels = {
        "low": "Низкий",
        "normal": "Обычный",
        "high": "Высокий",
        "critical": "Критический",
    }

    sla_text = ""
    if request.sla_deadline:
        sla_text = f"\nSLA: {request.sla_deadline.strftime('%d.%m.%Y %H:%M')}"
        if request.sla_breached:
            sla_text += " <b>Нарушен</b>"

    await message.reply(
        f"<b>Задача {request.ticket_number}</b>\n"
        f"Статус: {status_labels.get(request.status.value, request.status.value)}\n"
        f"Приоритет: {priority_labels.get(request.priority.value, request.priority.value)}"
        f"{sla_text}\n"
        f"Создана: {request.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
        f"{request.body[:200]}{'...' if len(request.body) > 200 else ''}",
        parse_mode="HTML",
    )


@router.message(Command("my"))
async def cmd_my_requests(message: Message, db_user: User | None) -> None:
    if db_user is None:
        await message.reply("Вы еще не зарегистрированы в системе.")
        return

    from sqlalchemy import select
    from models.request import Request

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Request)
            .where(Request.submitter_id == db_user.id)
            .order_by(Request.created_at.desc())
            .limit(10)
        )
        requests = list(result.scalars().all())

    if not requests:
        await message.reply("У вас пока нет задач.")
        return

    lines = ["<b>Ваши последние задачи:</b>\n"]
    for req in requests:
        lines.append(f"• <code>{req.ticket_number}</code> — {req.body[:50]}{'...' if len(req.body) > 50 else ''}")
    await message.reply("\n".join(lines), parse_mode="HTML")


@router.message(Command("register_topic"), F.chat.type == "supergroup")
async def cmd_register_topic_start(message: Message, state: FSMContext, db_user: User | None) -> None:
    if db_user is None or db_user.role not in (UserRole.admin, UserRole.supervisor):
        await message.reply("Только администраторы могут привязывать топики к отделам.")
        return

    if message.message_thread_id is None:
        await message.reply("Используйте эту команду внутри топика.")
        return

    await state.update_data(
        chat_id=message.chat.id,
        topic_id=message.message_thread_id,
        chat_title=message.chat.title or "Группа",
    )
    await state.set_state(RegisterTopicFSM.waiting_name)
    await message.reply("Введите название отдела для этого топика:")


@router.message(RegisterTopicFSM.waiting_name)
async def register_topic_name(message: Message, state: FSMContext) -> None:
    await state.update_data(dept_name=message.text.strip())
    await state.set_state(RegisterTopicFSM.waiting_sla)
    await message.reply("Укажите SLA в часах. По умолчанию 24:")


@router.message(RegisterTopicFSM.waiting_sla)
async def register_topic_sla(message: Message, state: FSMContext) -> None:
    text = message.text.strip()
    sla = int(text) if text.isdigit() else 24
    await state.update_data(sla_hours=sla)
    await state.set_state(RegisterTopicFSM.waiting_emoji)
    await message.reply("Введите эмодзи для отдела или '-' чтобы пропустить:")


@router.message(RegisterTopicFSM.waiting_emoji)
async def register_topic_emoji(message: Message, state: FSMContext) -> None:
    text = message.text.strip()
    emoji = None if text == "-" else text[:10]
    data = await state.get_data()
    await state.clear()

    async with AsyncSessionLocal() as session:
        dept_repo = DepartmentRepository(session)
        topic_repo = TopicRepository(session)
        group = await dept_repo.ensure_group_exists(
            chat_id=data["chat_id"],
            title=data["chat_title"],
        )
        dept = await dept_repo.create(
            group_id=group.id,
            telegram_topic_id=data["topic_id"],
            name=data["dept_name"],
            sla_hours=data["sla_hours"],
            icon_emoji=emoji,
        )
        await topic_repo.ensure_topic(
            chat_id=data["chat_id"],
            chat_title=data["chat_title"],
            topic_id=data["topic_id"],
            topic_title=data["dept_name"],
            icon_emoji=emoji,
            department=dept,
        )
        await session.commit()

    await message.reply(
        f"Топик привязан к отделу <b>{dept.name}</b>.\n"
        "AI продолжит обрабатывать поток автоматически, а рабочие сигналы при необходимости будут превращаться в задачи.",
        parse_mode="HTML",
    )


@router.message(Command("list_topics"), F.chat.type == "supergroup")
async def cmd_list_topics(message: Message, db_user: User | None) -> None:
    if db_user is None or db_user.role not in (UserRole.admin, UserRole.supervisor):
        await message.reply("Только администраторы.")
        return

    async with AsyncSessionLocal() as session:
        topic_repo = TopicRepository(session)
        topics = await topic_repo.list_topics()

    group_topics = [topic for topic in topics if topic.group and topic.group.telegram_chat_id == message.chat.id]
    if not group_topics:
        await message.reply("Топики еще не синхронизированы. Достаточно написать хотя бы одно сообщение в нужном топике.")
        return

    lines = ["<b>Обнаруженные топики:</b>\n"]
    for topic in group_topics:
        lines.append(
            f"{topic.icon_emoji or '•'} <b>{topic.title}</b> — thread={topic.telegram_topic_id}, kind={topic.topic_kind}, signals={topic.signal_count}"
        )
    await message.reply("\n".join(lines), parse_mode="HTML")
