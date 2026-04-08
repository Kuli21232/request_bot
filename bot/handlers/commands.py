"""Команды бота: /start, /help, /status, /register_topic."""
import logging
from aiogram import Router, F, Bot
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from bot.config import settings
from bot.database import AsyncSessionLocal
from bot.database.repositories.department_repo import DepartmentRepository
from bot.database.repositories.request_repo import RequestRepository
from models.user import User

logger = logging.getLogger(__name__)
router = Router()


class RegisterTopicFSM(StatesGroup):
    waiting_name = State()
    waiting_sla = State()
    waiting_emoji = State()


# ──────────────────── /start ────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message, db_user: User | None) -> None:
    name = db_user.first_name if db_user else message.from_user.first_name
    await message.answer(
        f"Привет, {name}! 👋\n\n"
        "Я бот для управления заявками.\n"
        "Напишите сообщение в нужный топик группы — я автоматически создам заявку.\n\n"
        "Команды:\n"
        "/status <номер> — статус заявки\n"
        "/my — мои заявки\n"
        "/help — помощь"
    )


# ──────────────────── /help ────────────────────

@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "📖 <b>Справка по боту</b>\n\n"
        "<b>Пользователям:</b>\n"
        "• Напишите заявку в нужный топик группы\n"
        "• Бот создаст тикет и уведомит агентов\n"
        "• /status REQ-2025-00001 — проверить статус\n"
        "• /my — ваши заявки\n\n"
        "<b>Администраторам:</b>\n"
        "• /register_topic — зарегистрировать топик как отдел\n"
        "• /list_topics — список зарегистрированных топиков",
        parse_mode="HTML",
    )


# ──────────────────── /status ────────────────────

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
        "new": "🆕 Новая",
        "open": "🔵 Открыта",
        "in_progress": "🟡 В работе",
        "waiting_for_user": "⏳ Ожидание ответа",
        "resolved": "✅ Решена",
        "closed": "🔒 Закрыта",
        "duplicate": "🔁 Дубликат",
    }
    priority_labels = {
        "low": "🟢 Низкий",
        "normal": "🔵 Обычный",
        "high": "🟠 Высокий",
        "critical": "🔴 Критический",
    }

    sla_text = ""
    if request.sla_deadline:
        sla_text = f"\nSLA: {request.sla_deadline.strftime('%d.%m.%Y %H:%M')}"
        if request.sla_breached:
            sla_text += " ⚠️ <b>Нарушен</b>"

    await message.reply(
        f"📋 <b>Заявка {request.ticket_number}</b>\n"
        f"Статус: {status_labels.get(request.status.value, request.status.value)}\n"
        f"Приоритет: {priority_labels.get(request.priority.value, request.priority.value)}"
        f"{sla_text}\n"
        f"Создана: {request.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
        f"{request.body[:200]}{'...' if len(request.body) > 200 else ''}",
        parse_mode="HTML",
    )


# ──────────────────── /my ────────────────────

@router.message(Command("my"))
async def cmd_my_requests(message: Message, db_user: User | None) -> None:
    if db_user is None:
        await message.reply("Вы не зарегистрированы.")
        return

    from sqlalchemy import select
    from models.request import Request
    from models.enums import RequestStatus

    async with AsyncSessionLocal() as session:
        from sqlalchemy.ext.asyncio import AsyncSession
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

    lines = ["📋 <b>Ваши последние заявки:</b>\n"]
    for req in requests:
        emoji = {"new": "🆕", "open": "🔵", "in_progress": "🟡",
                 "resolved": "✅", "closed": "🔒", "duplicate": "🔁"}.get(req.status.value, "•")
        lines.append(f"{emoji} <code>{req.ticket_number}</code> — {req.body[:50]}{'...' if len(req.body) > 50 else ''}")

    await message.reply("\n".join(lines), parse_mode="HTML")


# ──────────────────── /register_topic (admin) ────────────────────

@router.message(Command("register_topic"), F.chat.type == "supergroup")
async def cmd_register_topic_start(
    message: Message, state: FSMContext, db_user: User | None
) -> None:
    from models.enums import UserRole
    if db_user is None or db_user.role not in (UserRole.admin, UserRole.supervisor):
        await message.reply("Только администраторы могут регистрировать топики.")
        return

    if message.message_thread_id is None:
        await message.reply("Используйте эту команду внутри топика (форум).")
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
    await message.reply("Укажите SLA в часах (например: 24). По умолчанию 24:")


@router.message(RegisterTopicFSM.waiting_sla)
async def register_topic_sla(message: Message, state: FSMContext) -> None:
    text = message.text.strip()
    sla = 24
    if text.isdigit():
        sla = int(text)
    await state.update_data(sla_hours=sla)
    await state.set_state(RegisterTopicFSM.waiting_emoji)
    await message.reply("Введите эмодзи для отдела (или '-' чтобы пропустить):")


@router.message(RegisterTopicFSM.waiting_emoji)
async def register_topic_emoji(message: Message, state: FSMContext) -> None:
    text = message.text.strip()
    emoji = None if text == "-" else text[:10]

    data = await state.get_data()
    await state.clear()

    async with AsyncSessionLocal() as session:
        dept_repo = DepartmentRepository(session)
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

    await message.reply(
        f"✅ Топик зарегистрирован!\n"
        f"Отдел: {dept.icon_emoji or ''} <b>{dept.name}</b>\n"
        f"SLA: {dept.sla_hours} ч.\n\n"
        f"Теперь все сообщения в этом топике будут создавать заявки.",
        parse_mode="HTML",
    )


# ──────────────────── /list_topics (admin) ────────────────────

@router.message(Command("list_topics"), F.chat.type == "supergroup")
async def cmd_list_topics(message: Message, db_user: User | None) -> None:
    from models.enums import UserRole
    if db_user is None or db_user.role not in (UserRole.admin, UserRole.supervisor):
        await message.reply("Только администраторы.")
        return

    async with AsyncSessionLocal() as session:
        dept_repo = DepartmentRepository(session)
        from sqlalchemy import select
        from models.telegram_group import TelegramGroup
        result = await session.execute(
            select(TelegramGroup).where(TelegramGroup.telegram_chat_id == message.chat.id)
        )
        group = result.scalar_one_or_none()

        if group is None:
            await message.reply("Группа не зарегистрирована. Используйте /register_topic в любом топике.")
            return

        depts = await dept_repo.get_all_by_group(group.id)

    if not depts:
        await message.reply("Нет зарегистрированных топиков.")
        return

    lines = ["📋 <b>Зарегистрированные топики:</b>\n"]
    for d in depts:
        lines.append(
            f"{d.icon_emoji or '•'} <b>{d.name}</b> — topic_id={d.telegram_topic_id}, SLA={d.sla_hours}ч"
        )

    await message.reply("\n".join(lines), parse_mode="HTML")
