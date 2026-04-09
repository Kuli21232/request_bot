"""Фоновая задача мониторинга SLA — запускается через APScheduler."""
import logging
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.database import AsyncSessionLocal
from bot.database.repositories.request_repo import RequestRepository
from bot.database.repositories.department_repo import DepartmentRepository
from bot.services.notification_service import NotificationService
from bot.services.topic_automation_service import TopicAutomationService
from bot.services.topic_learning_service import TopicLearningService

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


async def retrain_topic_profiles() -> None:
    async with AsyncSessionLocal() as session:
        trainer = TopicLearningService()
        results = await trainer.retrain_active_topics(session, limit=20)
        await session.commit()
        logger.info("Topic trainer: retrained %d topics", len(results))


async def refresh_topic_automation() -> None:
    async with AsyncSessionLocal() as session:
        automation = TopicAutomationService()
        results = await automation.refresh_active_topics(session, limit=30)
        await session.commit()
        logger.info("Topic automation: refreshed %d topics", len(results))


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
    scheduler.add_job(
        retrain_topic_profiles,
        trigger="interval",
        minutes=60,
        id="topic_profile_retrain",
        replace_existing=True,
    )
    scheduler.add_job(
        refresh_topic_automation,
        trigger="interval",
        minutes=20,
        id="topic_automation_refresh",
        replace_existing=True,
    )
    return scheduler
