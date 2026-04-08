"""Bot commands."""
import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from bot.database import AsyncSessionLocal
from bot.database.repositories.department_repo import DepartmentRepository
from bot.database.repositories.request_repo import RequestRepository
from bot.database.repositories.topic_repo import TopicRepository
from models.user import User

logger = logging.getLogger(__name__)
router = Router()


class RegisterTopicFSM(StatesGroup):
    waiting_name = State()
    waiting_sla = State()
    waiting_emoji = State()


@router.message(CommandStart())
async def cmd_start(message: Message, db_user: User | None) -> None:
    name = db_user.first_name if db_user else message.from_user.first_name
    await message.answer(
        f"Привет, {name}!\n\n"
        "Я бот для AI-управления инфопотоком.\n"
        "Пишите в любой топик группы: я сам сохраню топик, разберу сообщение как сигнал, попробую объединить его в кейс и при необходимости создам actionable задачу.\n\n"
        "Команды:\n"
        "/status <номер> — статус legacy заявки\n"
        "/my — мои заявки\n"
        "/help — помощь"
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "AI-бот теперь работает в topic-driven режиме.\n\n"
        "Пользователям:\n"
        "• Просто пишите в нужный топик группы\n"
        "• Бот сам подтянет топик в систему\n"
        "• Сообщение попадёт в сигналы, кейсы и дайджесты\n"
        "• /status REQ-2025-00001 — проверить статус legacy заявки\n"
        "• /my — ваши заявки\n\n"
        "Администраторам:\n"
        "• /list_topics — показать обнаруженные топики\n"
        "• /register_topic — опционально привязать топик к отделу для shadow tickets\n"
    )


@router.message(Command("status"))
async def cmd_status(message: Message) -> None:
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("Укажите номер заявки: /status REQ-2025-00001")
        return

    ticket_number = args[1].strip().upper()

    async with AsyncSessionLocal() as session:
        repo = RequestRepository(session)
        request = await repo.get_by_ticket(ticket_number)

    if request is None:
        await message.reply(f"Заявка <code>{ticket_number}</code> не найдена.", parse_mode="HTML")
        return

    status_labels = {
        "new": "Новая",
        "open": "Открыта",
        "in_progress": "В работе",
        "waiting_for_user": "Ожидание ответа",
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
        f"<b>Заявка {request.ticket_number}</b>\n"
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
        await message.reply("Вы не зарегистрированы.")
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
        await message.reply("У вас пока нет заявок.")
        return

    lines = ["<b>Ваши последние заявки:</b>\n"]
    for req in requests:
        lines.append(f"• <code>{req.ticket_number}</code> — {req.body[:50]}{'...' if len(req.body) > 50 else ''}")
    await message.reply("\n".join(lines), parse_mode="HTML")


@router.message(Command("register_topic"), F.chat.type == "supergroup")
async def cmd_register_topic_start(message: Message, state: FSMContext, db_user: User | None) -> None:
    from models.enums import UserRole

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
    await message.reply("Введите название operational отдела для этого топика:")


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
        f"AI продолжит работать автоматически, а actionable сигналы будут создавать shadow tickets в этот отдел.",
        parse_mode="HTML",
    )


@router.message(Command("list_topics"), F.chat.type == "supergroup")
async def cmd_list_topics(message: Message, db_user: User | None) -> None:
    from models.enums import UserRole

    if db_user is None or db_user.role not in (UserRole.admin, UserRole.supervisor):
        await message.reply("Только администраторы.")
        return

    async with AsyncSessionLocal() as session:
        topic_repo = TopicRepository(session)
        topics = await topic_repo.list_topics()

    group_topics = [topic for topic in topics if topic.group and topic.group.telegram_chat_id == message.chat.id]
    if not group_topics:
        await message.reply("Топики ещё не синхронизированы. Напишите хотя бы одно сообщение в нужном топике.")
        return

    lines = ["<b>Обнаруженные топики:</b>\n"]
    for topic in group_topics:
        lines.append(
            f"{topic.icon_emoji or '•'} <b>{topic.title}</b> — thread={topic.telegram_topic_id}, kind={topic.topic_kind}, signals={topic.signal_count}"
        )
    await message.reply("\n".join(lines), parse_mode="HTML")
