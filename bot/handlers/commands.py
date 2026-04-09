"""Bot commands."""
from html import escape
import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from sqlalchemy import select

from bot.database import AsyncSessionLocal
from bot.database.repositories.department_repo import DepartmentRepository
from bot.database.repositories.knowledge_repo import KnowledgeRepository
from bot.database.repositories.request_repo import RequestRepository
from bot.database.repositories.topic_repo import TopicRepository
from bot.database.repositories.user_repo import UserRepository
from bot.services.assistant_service import AssistantService
from bot.services.guidance_service import GuidanceService
from bot.services.notification_service import NotificationService
from bot.services.topic_ai_engine import TopicAIEngine
from models.enums import UserRole
from models.request import Request
from models.telegram_group import TelegramGroup
from models.topic import TelegramTopic
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
    username = f"@{escape(user.username)}" if user.username else "без username"
    full_name = " ".join(part for part in [user.first_name, user.last_name] if part).strip()
    return f"• <b>{escape(full_name or 'Без имени')}</b> — {username}, роль: {escape(role)}"


def _priority_badge(priority: str) -> str:
    return {
        "critical": "🔴",
        "high": "🟠",
        "normal": "🟡",
        "low": "🟢",
    }.get(priority, "⚪")


def _topic_badge(topic: TelegramTopic) -> str:
    return topic.icon_emoji or "•"


def _shorten(text: str | None, *, limit: int = 120) -> str:
    if not text:
        return "—"
    value = " ".join(text.split())
    if len(value) <= limit:
        return value
    return f"{value[: limit - 1]}…"


def _format_topic_rank_line(item: dict, index: int) -> str:
    topic: TelegramTopic = item["topic"]
    metrics = item["metrics"]
    reasons = ", ".join(item["reasons"][:2]) if item["reasons"] else "стабильный поток"
    dominant_signal = item["dominant_signal_type"] or "mixed"
    return (
        f"{index}. {_priority_badge(item['priority'])} {_topic_badge(topic)} <b>{escape(topic.title)}</b>\n"
        f"тип: {escape(topic.topic_kind or 'mixed')} / AI: {escape(dominant_signal)}\n"
        f"сигналы: {metrics['signal_count']}, внимание: {metrics['attention_count']}, "
        f"ситуации: {metrics['open_case_count']} открыто / {metrics['critical_case_count']} критично\n"
        f"почему выше: {escape(reasons)}"
    )


def _rank_group_topics(group: TelegramGroup, metrics: dict[int, dict]) -> list[dict]:
    engine = TopicAIEngine()
    topics = [topic for topic in group.topics if topic.is_active]
    return engine.sort_topics(topics, metrics)


@router.message(CommandStart())
async def cmd_start(message: Message, db_user: User | None) -> None:
    name = db_user.first_name if db_user else message.from_user.first_name
    await message.answer(
        f"Привет, {escape(name)}!\n\n"
        "Я AI-помощник по операционному потоку BeerShop.\n\n"
        "Главное:\n"
        "/assistant <запрос> — AI-помощник по топикам, сводкам и приоритетам\n"
        "/digest [тема] — сводка по группе или теме\n"
        "/next — что сейчас в приоритете\n"
        "/help — краткая справка\n\n"
        "Профили сотрудников и комментарии теперь удобнее смотреть в mini app, в разделе «Команда».",
        parse_mode="HTML",
    )


@router.message(Command("help"))
async def cmd_help(message: Message, db_user: User | None) -> None:
    lines = [
        "<b>Основные команды</b>",
        "/assistant &lt;запрос&gt; — AI-помощник по топикам, сводкам и приоритетам",
        "/digest [тема] — сводка по группе, топику или общему потоку",
        "/next — что сейчас стоит разбирать в первую очередь",
        "",
        "Для справок и инструкций по-прежнему работают:",
        "/ask &lt;вопрос&gt;",
        "/guide &lt;тема&gt;",
        "",
        "Профили сотрудников, заметки и подписки перенесены в mini app, в раздел <b>Команда</b>.",
    ]

    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("ask"))
async def cmd_ask(message: Message, db_user: User | None) -> None:
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.reply("Напишите вопрос после команды, например: /ask как работает бот")
        return

    async with AsyncSessionLocal() as session:
        repo = KnowledgeRepository(session)
        service = GuidanceService(repo)
        answer = await service.answer(parts[1], audience=(db_user.role.value if db_user else "all"), mode="answer")

    lines = [answer["answer"]]
    if answer["sources"]:
        lines.append("\nИсточники:")
        lines.extend(f"• {escape(source['title'])}" for source in answer["sources"])
    await message.reply("\n".join(lines), parse_mode="HTML")


@router.message(Command("guide"))
async def cmd_guide(message: Message, db_user: User | None) -> None:
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.reply("Укажите тему, например: /guide профили сотрудников")
        return

    async with AsyncSessionLocal() as session:
        repo = KnowledgeRepository(session)
        service = GuidanceService(repo)
        answer = await service.answer(parts[1], audience=(db_user.role.value if db_user else "all"), mode="guide")

    lines = [answer["answer"]]
    if answer["sources"]:
        lines.append("\nНа основе материалов:")
        lines.extend(f"• {escape(source['title'])}" for source in answer["sources"])
    await message.reply("\n".join(lines), parse_mode="HTML")


@router.message(Command("assistant"))
async def cmd_assistant(message: Message, db_user: User | None) -> None:
    if not _is_staff(db_user):
        await message.reply("AI-помощник по операционному потоку доступен исполнителям и руководителям.")
        return

    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.reply(
            "Напишите запрос после команды, например:\n"
            "/assistant сделай сводку по доставке\n"
            "/assistant что сейчас в приоритете\n"
            "/assistant что происходит в этой группе"
        )
        return

    async with AsyncSessionLocal() as session:
        service = AssistantService(session)
        result = await service.answer(
            parts[1],
            current_chat_id=(message.chat.id if message.chat.type == "supergroup" else None),
        )

    await message.reply(escape(result.answer), parse_mode="HTML")


@router.message(Command("digest"))
async def cmd_digest(message: Message, db_user: User | None) -> None:
    if not _is_staff(db_user):
        await message.reply("Сводки по потоку доступны исполнителям и руководителям.")
        return

    parts = (message.text or "").split(maxsplit=1)
    prompt = parts[1] if len(parts) > 1 else "сделай сводку по текущей группе"
    if message.chat.type != "supergroup" and len(parts) == 1:
        prompt = "сделай общую сводку по потоку"

    async with AsyncSessionLocal() as session:
        service = AssistantService(session)
        result = await service.answer(
            prompt,
            current_chat_id=(message.chat.id if message.chat.type == "supergroup" else None),
        )

    await message.reply(escape(result.answer), parse_mode="HTML")


@router.message(Command("next"))
async def cmd_next(message: Message, db_user: User | None) -> None:
    if not _is_staff(db_user):
        await message.reply("Приоритеты по потоку доступны исполнителям и руководителям.")
        return

    async with AsyncSessionLocal() as session:
        service = AssistantService(session)
        result = await service.answer(
            "что сейчас нужно сделать в первую очередь",
            current_chat_id=(message.chat.id if message.chat.type == "supergroup" else None),
        )

    await message.reply(escape(result.answer), parse_mode="HTML")


@router.message(Command("participants"))
async def cmd_participants(message: Message, db_user: User | None) -> None:
    if not _is_staff(db_user):
        await message.reply("Список участников доступен исполнителям и руководителям.")
        return

    parts = (message.text or "").split(maxsplit=1)
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

    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.reply("Укажите сотрудника: /profile @username или /profile 15")
        return

    async with AsyncSessionLocal() as session:
        knowledge_repo = KnowledgeRepository(session)
        target = await _resolve_user(parts[1], session)
        if target is None:
            await message.reply("Сотрудник не найден.")
            return
        notes = await knowledge_repo.list_profile_notes(target.id, limit=5)
        subscription = await knowledge_repo.get_subscription(db_user.id, target.id)

    full_name = " ".join(part for part in [target.first_name, target.last_name] if part).strip()
    lines = [
        f"<b>{escape(full_name or 'Без имени')}</b>",
        f"ID: <code>{target.id}</code>",
        f"Username: @{escape(target.username)}" if target.username else "Username: не указан",
        f"Роль: {escape(target.role.value)}",
        f"Последняя активность: {target.last_active_at.strftime('%d.%m.%Y %H:%M') if target.last_active_at else 'нет данных'}",
        f"Подписка: {'включена' if subscription and subscription.is_active else 'нет'}",
    ]
    if notes:
        lines.append("\n<b>Последние заметки:</b>")
        for note in notes:
            author = note.author.first_name if note.author else "Система"
            lines.append(f"• {escape(author)}: {escape(_shorten(note.body, limit=160))}")
    else:
        lines.append("\nЗаметок по профилю пока нет.")
    await message.reply("\n".join(lines), parse_mode="HTML")


@router.message(Command("note"))
async def cmd_note(message: Message, db_user: User | None, bot: Bot) -> None:
    if not _is_staff(db_user):
        await message.reply("Заметки по профилям могут оставлять только исполнители и руководители.")
        return

    parts = (message.text or "").split(maxsplit=1)
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
        f"Заметка добавлена в профиль <b>{escape(target.first_name)}</b>.\n"
        f"Чтобы следить за обновлениями, используйте /watch {target.id}",
        parse_mode="HTML",
    )


@router.message(Command("watch"))
async def cmd_watch(message: Message, db_user: User | None) -> None:
    if not _is_staff(db_user):
        await message.reply("Подписки на профили доступны исполнителям и руководителям.")
        return

    parts = (message.text or "").split(maxsplit=1)
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

    await message.reply(f"Подписка на профиль {escape(target.first_name)} включена.", parse_mode="HTML")


@router.message(Command("unwatch"))
async def cmd_unwatch(message: Message, db_user: User | None) -> None:
    if not _is_staff(db_user):
        await message.reply("Подписки на профили доступны исполнителям и руководителям.")
        return

    parts = (message.text or "").split(maxsplit=1)
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

    await message.reply(f"Подписка на профиль {escape(target.first_name)} отключена.", parse_mode="HTML")


@router.message(Command("groups"))
async def cmd_groups(message: Message, db_user: User | None) -> None:
    if not _is_staff(db_user):
        await message.reply("Обзор групп доступен исполнителям и руководителям.")
        return

    async with AsyncSessionLocal() as session:
        topic_repo = TopicRepository(session)
        groups = await topic_repo.list_groups_with_topics()
        metrics = await topic_repo.build_topic_metrics()

    if not groups:
        await message.reply("Группы и топики пока не синхронизированы.")
        return

    lines = ["<b>Обзор групп</b>"]
    for group in groups:
        ranked = _rank_group_topics(group, metrics)
        top_topics = ranked[:3]
        high_topics = sum(1 for item in ranked if item["priority"] in {"high", "critical"})
        total_signals = sum(item["metrics"]["signal_count"] for item in ranked)
        lines.append(
            f"\n<b>{escape(group.title)}</b>\n"
            f"топиков: {len(ranked)}, приоритетных: {high_topics}, сигналов: {total_signals}"
        )
        if top_topics:
            for index, item in enumerate(top_topics, start=1):
                topic = item["topic"]
                lines.append(
                    f"{index}. {_priority_badge(item['priority'])} {_topic_badge(topic)} "
                    f"{escape(topic.title)} — внимание {item['metrics']['attention_count']}, "
                    f"ситуации {item['metrics']['open_case_count']}"
                )
        else:
            lines.append("Пока нет активных топиков.")

    await message.reply("\n".join(lines), parse_mode="HTML")


@router.message(Command("topics"))
async def cmd_topics(message: Message, db_user: User | None) -> None:
    if not _is_staff(db_user):
        await message.reply("Обзор топиков доступен исполнителям и руководителям.")
        return

    async with AsyncSessionLocal() as session:
        topic_repo = TopicRepository(session)
        groups = await topic_repo.list_groups_with_topics()
        metrics = await topic_repo.build_topic_metrics()

    if not groups:
        await message.reply("Топики пока не синхронизированы.")
        return

    target_group = None
    if message.chat.type == "supergroup":
        for group in groups:
            if group.telegram_chat_id == message.chat.id:
                target_group = group
                break

    if target_group is not None:
        ranked = _rank_group_topics(target_group, metrics)
        if not ranked:
            await message.reply("В этой группе пока нет синхронизированных топиков.")
            return
        lines = [f"<b>Топики группы {escape(target_group.title)}</b>"]
        for index, item in enumerate(ranked[:10], start=1):
            lines.append(_format_topic_rank_line(item, index))
        await message.reply("\n\n".join(lines), parse_mode="HTML")
        return

    lines = ["<b>AI-ранжирование топиков по группам</b>"]
    for group in groups:
        ranked = _rank_group_topics(group, metrics)[:5]
        if not ranked:
            continue
        lines.append(f"\n<b>{escape(group.title)}</b>")
        for index, item in enumerate(ranked, start=1):
            topic = item["topic"]
            lines.append(
                f"{index}. {_priority_badge(item['priority'])} {_topic_badge(topic)} "
                f"{escape(topic.title)} — тип {escape(topic.topic_kind or 'mixed')}, "
                f"внимание {item['metrics']['attention_count']}, "
                f"ситуации {item['metrics']['open_case_count']}"
            )

    await message.reply("\n".join(lines), parse_mode="HTML")


@router.message(Command("status"))
async def cmd_status(message: Message) -> None:
    args = (message.text or "").split(maxsplit=1)
    if len(args) < 2:
        await message.reply("Укажите номер задачи: /status REQ-2025-00001")
        return

    ticket_number = args[1].strip().upper()

    async with AsyncSessionLocal() as session:
        repo = RequestRepository(session)
        request = await repo.get_by_ticket(ticket_number)

    if request is None:
        await message.reply(f"Задача <code>{escape(ticket_number)}</code> не найдена.", parse_mode="HTML")
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
        f"<b>Задача {escape(request.ticket_number)}</b>\n"
        f"Статус: {status_labels.get(request.status.value, request.status.value)}\n"
        f"Приоритет: {priority_labels.get(request.priority.value, request.priority.value)}"
        f"{sla_text}\n"
        f"Создана: {request.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
        f"{escape(_shorten(request.body, limit=220))}",
        parse_mode="HTML",
    )


@router.message(Command("my"))
async def cmd_my_requests(message: Message, db_user: User | None) -> None:
    if db_user is None:
        await message.reply("Вы еще не зарегистрированы в системе.")
        return

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

    lines = ["<b>Ваши последние задачи:</b>"]
    for req in requests:
        lines.append(f"• <code>{escape(req.ticket_number)}</code> — {escape(_shorten(req.body, limit=70))}")
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
    await state.update_data(dept_name=(message.text or "").strip())
    await state.set_state(RegisterTopicFSM.waiting_sla)
    await message.reply("Укажите SLA в часах. По умолчанию 24:")


@router.message(RegisterTopicFSM.waiting_sla)
async def register_topic_sla(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    sla = int(text) if text.isdigit() else 24
    await state.update_data(sla_hours=sla)
    await state.set_state(RegisterTopicFSM.waiting_emoji)
    await message.reply("Введите эмодзи для отдела или '-' чтобы пропустить:")


@router.message(RegisterTopicFSM.waiting_emoji)
async def register_topic_emoji(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
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
        f"Топик привязан к отделу <b>{escape(dept.name)}</b>.\n"
        "AI продолжит автоматически разбирать поток, а рабочие сигналы при необходимости "
        "будут становиться задачами.",
        parse_mode="HTML",
    )


@router.message(Command("list_topics"), F.chat.type == "supergroup")
async def cmd_list_topics(message: Message, db_user: User | None) -> None:
    if db_user is None or db_user.role not in (UserRole.admin, UserRole.supervisor):
        await message.reply("Только администраторы.")
        return

    async with AsyncSessionLocal() as session:
        topic_repo = TopicRepository(session)
        groups = await topic_repo.list_groups_with_topics()
        metrics = await topic_repo.build_topic_metrics()

    target_group = None
    for group in groups:
        if group.telegram_chat_id == message.chat.id:
            target_group = group
            break

    if target_group is None:
        await message.reply("Топики этой группы пока не синхронизированы.")
        return

    ranked = _rank_group_topics(target_group, metrics)
    if not ranked:
        await message.reply("Топики еще не синхронизированы. Достаточно одного сообщения в нужном топике.")
        return

    lines = ["<b>Обнаруженные топики:</b>"]
    for item in ranked:
        topic = item["topic"]
        lines.append(
            f"{_topic_badge(topic)} <b>{escape(topic.title)}</b> — "
            f"thread={topic.telegram_topic_id}, kind={escape(topic.topic_kind)}, "
            f"signals={item['metrics']['signal_count']}, attention={item['metrics']['attention_count']}"
        )
    await message.reply("\n".join(lines), parse_mode="HTML")
