"""Фоновая задача мониторинга SLA — запускается через APScheduler."""
import logging
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.database import AsyncSessionLocal
from bot.database.repositories.request_repo import RequestRepository
from bot.database.repositories.department_repo import DepartmentRepository
from bot.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


async def check_sla_breaches(bot: Bot) -> None:
    """Находит просроченные заявки и уведомляет агентов."""
    notification_service = NotificationService(bot)

    async with AsyncSessionLocal() as session:
        request_repo = RequestRepository(session)
        dept_repo = DepartmentRepository(session)

        breached = await request_repo.get_sla_breached()
        logger.info("SLA checker: найдено %d просроченных заявок", len(breached))

        for req in breached:
            await request_repo.mark_sla_breached(req.id)
            dept = await dept_repo.get_by_id(req.department_id)
            if dept:
                await notification_service.notify_sla_breach(req, dept)


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    # Проверка SLA каждые 15 минут
    scheduler.add_job(
        check_sla_breaches,
        trigger="interval",
        minutes=15,
        kwargs={"bot": bot},
        id="sla_check",
        replace_existing=True,
    )
    return scheduler
