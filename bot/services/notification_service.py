"""Уведомления агентам и пользователям через Telegram."""
import logging
from aiogram import Bot

from bot.database import AsyncSessionLocal
from bot.database.repositories.user_repo import UserRepository
from bot.keyboards.inline import build_rating_keyboard
from models.request import Request
from models.department import Department
from models.user import User

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, bot: Bot):
        self.bot = bot

    async def notify_new_request(self, request: Request, department: Department) -> None:
        """Уведомляет всех агентов отдела о новой заявке."""
        async with AsyncSessionLocal() as session:
            repo = UserRepository(session)
            agents = await repo.get_agents_by_department(department.id)

        for agent in agents:
            if agent.telegram_user_id is None:
                continue
            try:
                await self.bot.send_message(
                    chat_id=agent.telegram_user_id,
                    text=(
                        f"🆕 <b>Новая заявка</b>\n"
                        f"Тикет: <code>{request.ticket_number}</code>\n"
                        f"Отдел: {department.icon_emoji or ''} {department.name}\n"
                        f"SLA: до {request.sla_deadline.strftime('%d.%m.%Y %H:%M') if request.sla_deadline else 'н/д'}\n\n"
                        f"{request.body[:300]}{'...' if len(request.body) > 300 else ''}"
                    ),
                    parse_mode="HTML",
                )
            except Exception as e:
                logger.warning("Не удалось уведомить агента %s: %s", agent.id, e)

    async def notify_status_changed(
        self,
        request: Request,
        new_status: str,
        submitter: User,
    ) -> None:
        """Уведомляет подателя заявки об изменении статуса."""
        if submitter.telegram_user_id is None:
            return

        status_labels = {
            "open": "🔵 Открыта",
            "in_progress": "🟡 В работе",
            "waiting_for_user": "⏳ Ожидаем ответа",
            "resolved": "✅ Решена",
            "closed": "🔒 Закрыта",
        }
        label = status_labels.get(new_status, new_status)

        keyboard = None
        if new_status == "resolved":
            keyboard = build_rating_keyboard(request.id)

        try:
            await self.bot.send_message(
                chat_id=submitter.telegram_user_id,
                text=(
                    f"Статус вашей заявки <code>{request.ticket_number}</code> изменён:\n"
                    f"{label}"
                    + ("\n\nОцените качество решения:" if new_status == "resolved" else "")
                ),
                parse_mode="HTML",
                reply_markup=keyboard,
            )
        except Exception as e:
            logger.warning("Не удалось уведомить пользователя %s: %s", submitter.id, e)

    async def notify_sla_breach(self, request: Request, department: Department) -> None:
        """Уведомляет агентов и супервизоров об истечении SLA."""
        async with AsyncSessionLocal() as session:
            repo = UserRepository(session)
            agents = await repo.get_agents_by_department(department.id)

        for agent in agents:
            if agent.telegram_user_id is None:
                continue
            try:
                await self.bot.send_message(
                    chat_id=agent.telegram_user_id,
                    text=(
                        f"🚨 <b>SLA нарушен!</b>\n"
                        f"Тикет <code>{request.ticket_number}</code> просрочен.\n"
                        f"Отдел: {department.name}\n"
                        f"Требует немедленного внимания."
                    ),
                    parse_mode="HTML",
                )
            except Exception as e:
                logger.warning("SLA-уведомление не доставлено агенту %s: %s", agent.id, e)

    async def send_waiting_reminder(self, request: Request, submitter: User) -> None:
        """Напоминание подателю о заявке в статусе waiting_for_user."""
        if submitter.telegram_user_id is None:
            return
        try:
            await self.bot.send_message(
                chat_id=submitter.telegram_user_id,
                text=(
                    f"Ваша заявка <code>{request.ticket_number}</code> ожидает ответа.\n"
                    f"Пожалуйста, сообщите, если вопрос ещё актуален, "
                    f"или заявка будет закрыта автоматически через 48 часов."
                ),
                parse_mode="HTML",
            )
        except Exception as e:
            logger.warning("Не удалось отправить напоминание %s: %s", submitter.id, e)
