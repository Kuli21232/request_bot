"""Точка входа Telegram-бота."""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from bot.config import settings
from bot.handlers import forum_messages, commands, callbacks
from bot.middlewares import AuthMiddleware, TopicResolverMiddleware, RateLimitMiddleware
from bot.services.sla_monitor import setup_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def set_commands(bot: Bot) -> None:
    await bot.set_my_commands([
        BotCommand(command="start", description="Запуск бота"),
        BotCommand(command="help", description="Справка"),
        BotCommand(command="status", description="Статус заявки"),
        BotCommand(command="my", description="Мои заявки"),
        BotCommand(command="register_topic", description="Регистрация топика (admin)"),
        BotCommand(command="list_topics", description="Список топиков (admin)"),
    ])


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())

    # Middlewares (порядок важен)
    dp.message.outer_middleware(AuthMiddleware())
    dp.message.outer_middleware(RateLimitMiddleware(rate=settings.RATE_LIMIT_PER_MINUTE))
    dp.message.outer_middleware(TopicResolverMiddleware())

    # Роутеры
    dp.include_router(commands.router)
    dp.include_router(forum_messages.router)
    dp.include_router(callbacks.router)

    return dp


async def main_polling() -> None:
    """Режим polling — для разработки."""
    bot = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = create_dispatcher()

    scheduler = setup_scheduler(bot)
    scheduler.start()

    await set_commands(bot)
    logger.info("Запуск в режиме polling...")
    try:
        await dp.start_polling(bot, allowed_updates=["message", "callback_query"])
    finally:
        scheduler.shutdown()
        await bot.session.close()


async def main_webhook() -> None:
    """Режим webhook — для продакшена на VDS."""
    from aiohttp import web
    from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

    bot = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = create_dispatcher()

    scheduler = setup_scheduler(bot)

    webhook_path = f"/webhook/{settings.BOT_TOKEN}"
    webhook_url = f"{settings.WEBHOOK_BASE_URL.rstrip('/')}{webhook_path}"

    async def on_startup(app: web.Application) -> None:
        scheduler.start()
        await bot.set_webhook(
            url=webhook_url,
            allowed_updates=["message", "callback_query"],
        )
        await set_commands(bot)
        logger.info("Webhook установлен: %s", webhook_url)

    async def on_shutdown(app: web.Application) -> None:
        scheduler.shutdown()
        await bot.delete_webhook()
        await bot.session.close()
        logger.info("Webhook удалён.")

    app = web.Application()
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    handler.register(app, path=webhook_path)
    setup_application(app, dp, bot=bot)

    web.run_app(app, host="0.0.0.0", port=settings.BOT_PORT)


if __name__ == "__main__":
    if settings.WEBHOOK_BASE_URL:
        asyncio.run(main_webhook())
    else:
        asyncio.run(main_polling())
