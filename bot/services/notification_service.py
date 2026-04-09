"""Telegram notifications for requests, profile notes, and subscriptions."""
import logging

from aiogram import Bot

from bot.database import AsyncSessionLocal
from bot.database.repositories.knowledge_repo import KnowledgeRepository
from bot.database.repositories.user_repo import UserRepository
from bot.keyboards.inline import build_rating_keyboard
from models.department import Department
from models.request import Request
from models.user import User

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, bot: Bot):
        self.bot = bot

    async def notify_new_request(self, request: Request, department: Department) -> None:
        async with AsyncSessionLocal() as session:
            repo = UserRepository(session)
            agents = await repo.get_agents_by_department(department.id)

        for agent in agents:
            if agent.telegram_user_id is None:
                continue
            await self._safe_send(
                agent.telegram_user_id,
                (
                    f"🆕 <b>Новая задача</b>\n"
                    f"Тикет: <code>{request.ticket_number}</code>\n"
                    f"Отдел: {department.icon_emoji or ''} {department.name}\n"
                    f"SLA: {request.sla_deadline.strftime('%d.%m.%Y %H:%M') if request.sla_deadline else 'н/д'}\n\n"
                    f"{request.body[:300]}{'...' if len(request.body) > 300 else ''}"
                ),
            )

    async def notify_status_changed(self, request: Request, new_status: str, submitter: User) -> None:
        if submitter.telegram_user_id is None:
            return

        status_labels = {
            "open": "Открыта",
            "in_progress": "В работе",
            "waiting_for_user": "Ждем ответ",
            "resolved": "Решена",
            "closed": "Закрыта",
        }
        keyboard = build_rating_keyboard(request.id) if new_status == "resolved" else None
        await self._safe_send(
            submitter.telegram_user_id,
            (
                f"Статус вашей задачи <code>{request.ticket_number}</code> изменился:\n"
                f"<b>{status_labels.get(new_status, new_status)}</b>"
            ),
            reply_markup=keyboard,
        )

    async def notify_sla_breach(self, request: Request, department: Department) -> None:
        async with AsyncSessionLocal() as session:
            repo = UserRepository(session)
            agents = await repo.get_agents_by_department(department.id)

        for agent in agents:
            if agent.telegram_user_id is None:
                continue
            await self._safe_send(
                agent.telegram_user_id,
                (
                    f"🚨 <b>SLA нарушен</b>\n"
                    f"Тикет <code>{request.ticket_number}</code> просрочен.\n"
                    f"Отдел: {department.name}\n"
                    f"Нужно внимание."
                ),
            )

    async def send_waiting_reminder(self, request: Request, submitter: User) -> None:
        if submitter.telegram_user_id is None:
            return
        await self._safe_send(
            submitter.telegram_user_id,
            (
                f"Ваша задача <code>{request.ticket_number}</code> ждет ответа.\n"
                "Если вопрос еще актуален, напишите в чат или обновите задачу."
            ),
        )

    async def notify_profile_note(
        self,
        *,
        target_user: User,
        author: User | None,
        note_body: str,
        notify_target: bool = False,
    ) -> None:
        async with AsyncSessionLocal() as session:
            repo = KnowledgeRepository(session)
            watchers = await repo.list_active_watchers(target_user.id)

        recipients = {}
        for watcher in watchers:
            if watcher.telegram_user_id:
                recipients[watcher.telegram_user_id] = watcher
        if notify_target and target_user.telegram_user_id:
            recipients[target_user.telegram_user_id] = target_user

        author_name = author.first_name if author else "Система"
        for telegram_id, watcher in recipients.items():
            if author and watcher.id == author.id:
                continue
            await self._safe_send(
                telegram_id,
                (
                    f"🔔 <b>Обновление профиля сотрудника</b>\n"
                    f"Сотрудник: {target_user.first_name} {target_user.last_name or ''}\n"
                    f"Автор заметки: {author_name}\n\n"
                    f"{note_body[:500]}"
                ),
            )

    async def _safe_send(self, chat_id: int, text: str, **kwargs) -> None:
        try:
            await self.bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML", **kwargs)
        except Exception as exc:
            logger.warning("Failed to send notification to %s: %s", chat_id, exc)
