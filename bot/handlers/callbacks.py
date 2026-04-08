"""Обработчики inline-кнопок: рейтинг, статус, приоритет."""
import logging
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery

from bot.database import AsyncSessionLocal
from bot.database.repositories.request_repo import RequestRepository
from bot.services.notification_service import NotificationService
from models.enums import RequestStatus, RequestPriority, UserRole

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "my_requests")
async def cb_my_requests(callback: CallbackQuery) -> None:
    await callback.answer("Открываю список заявок...", show_alert=False)


@router.callback_query(F.data.startswith("rate:"))
async def cb_rate_request(callback: CallbackQuery) -> None:
    """Оценка качества после решения заявки."""
    _, request_id_str, score_str = callback.data.split(":")
    request_id = int(request_id_str)
    score = int(score_str)

    async with AsyncSessionLocal() as session:
        repo = RequestRepository(session)
        req = await repo.get_by_id(request_id)
        if req is None:
            await callback.answer("Заявка не найдена.", show_alert=True)
            return
        req.satisfaction_score = score
        await session.commit()

    stars = "⭐" * score
    await callback.message.edit_text(
        f"Спасибо за оценку! {stars}\n"
        f"Заявка {req.ticket_number} закрыта."
    )
    await callback.answer()


@router.callback_query(F.data.startswith("status:"))
async def cb_change_status(callback: CallbackQuery, bot: Bot) -> None:
    """Смена статуса агентом (только агент/admin)."""
    from bot.database.repositories.user_repo import UserRepository

    _, request_id_str, new_status_str = callback.data.split(":")
    request_id = int(request_id_str)

    async with AsyncSessionLocal() as session:
        user_repo = UserRepository(session)
        db_user = await user_repo.get_by_telegram_id(callback.from_user.id)

        if db_user is None or db_user.role not in (UserRole.agent, UserRole.supervisor, UserRole.admin):
            await callback.answer("Недостаточно прав.", show_alert=True)
            return

        try:
            new_status = RequestStatus(new_status_str)
        except ValueError:
            await callback.answer("Неизвестный статус.", show_alert=True)
            return

        request_repo = RequestRepository(session)
        req = await request_repo.get_by_id(request_id)
        if req is None:
            await callback.answer("Заявка не найдена.", show_alert=True)
            return

        await request_repo.update_status(request_id, new_status, actor_id=db_user.id)

    notification_service = NotificationService(bot)
    if req.submitter:
        await notification_service.notify_status_changed(req, new_status_str, req.submitter)

    await callback.answer(f"Статус изменён: {new_status_str}", show_alert=False)


@router.callback_query(F.data.startswith("priority:"))
async def cb_change_priority(callback: CallbackQuery) -> None:
    """Смена приоритета агентом."""
    from bot.database.repositories.user_repo import UserRepository

    _, request_id_str, new_priority_str = callback.data.split(":")
    request_id = int(request_id_str)

    async with AsyncSessionLocal() as session:
        user_repo = UserRepository(session)
        db_user = await user_repo.get_by_telegram_id(callback.from_user.id)

        if db_user is None or db_user.role not in (UserRole.agent, UserRole.supervisor, UserRole.admin):
            await callback.answer("Недостаточно прав.", show_alert=True)
            return

        try:
            new_priority = RequestPriority(new_priority_str)
        except ValueError:
            await callback.answer("Неизвестный приоритет.", show_alert=True)
            return

        request_repo = RequestRepository(session)
        req = await request_repo.get_by_id(request_id)
        if req is None:
            await callback.answer("Заявка не найдена.", show_alert=True)
            return

        old_priority = req.priority
        req.priority = new_priority
        from models.request import RequestHistory
        session.add(RequestHistory(
            request_id=request_id,
            actor_id=db_user.id,
            action="priority_change",
            field_name="priority",
            old_value=old_priority.value,
            new_value=new_priority.value,
        ))
        await session.commit()

    await callback.answer(f"Приоритет изменён: {new_priority_str}", show_alert=False)
