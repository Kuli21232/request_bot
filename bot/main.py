"""Entry point for the Telegram bot."""

import asyncio
import logging
import socket
from collections.abc import Awaitable, Callable
from contextlib import suppress

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand
from aiohttp.resolver import ThreadedResolver

from bot.config import settings
from bot.handlers import callbacks, commands, forum_messages
from bot.middlewares import (
    AdminOnlyInteractionMiddleware,
    AuthMiddleware,
    RateLimitMiddleware,
    TopicResolverMiddleware,
)
from bot.services.llm_service import LLMService
from bot.services.sla_monitor import setup_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)
_ORIGINAL_GETADDRINFO = socket.getaddrinfo
_TELEGRAM_IPV4_ONLY_HOSTS = {"api.telegram.org", "core.telegram.org"}
_NETWORK_WORKAROUND_APPLIED = False


class IPv4Resolver(ThreadedResolver):
    async def resolve(self, host: str, port: int = 0, family: socket.AddressFamily = socket.AF_INET):
        return await super().resolve(host, port, family=socket.AF_INET)


async def _run_noncritical_step(
    label: str,
    action: Callable[[], Awaitable[object | None]],
    *,
    attempts: int = 3,
    base_delay: float = 2.0,
) -> bool:
    for attempt in range(1, attempts + 1):
        try:
            await action()
            if attempt > 1:
                logger.info("%s succeeded on attempt %s", label, attempt)
            return True
        except Exception:
            logger.exception("%s failed on attempt %s/%s", label, attempt, attempts)
            if attempt < attempts:
                await asyncio.sleep(base_delay * attempt)

    logger.error("%s failed after %s attempts; continuing startup", label, attempts)
    return False


def apply_network_workarounds() -> None:
    global _NETWORK_WORKAROUND_APPLIED

    if _NETWORK_WORKAROUND_APPLIED:
        return

    def _ipv4_only_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
        results = _ORIGINAL_GETADDRINFO(host, port, family, type, proto, flags)
        if host in _TELEGRAM_IPV4_ONLY_HOSTS:
            ipv4_results = [result for result in results if result[0] == socket.AF_INET]
            if ipv4_results:
                return ipv4_results
        return results

    socket.getaddrinfo = _ipv4_only_getaddrinfo
    _NETWORK_WORKAROUND_APPLIED = True


async def set_commands(bot: Bot) -> None:
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Запуск бота"),
            BotCommand(command="help", description="Список команд"),
            BotCommand(command="assistant", description="AI-помощник по потоку"),
            BotCommand(command="digest", description="AI-сводка по теме или группе"),
            BotCommand(command="next", description="Что сейчас в приоритете"),
        ]
    )


def create_bot() -> Bot:
    apply_network_workarounds()
    session = AiohttpSession()
    session._connector_init["family"] = socket.AF_INET
    return Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        session=session,
    )


def configure_bot_network(bot: Bot) -> None:
    connector_init = getattr(bot.session, "_connector_init", None)
    if isinstance(connector_init, dict):
        connector_init["family"] = socket.AF_INET
        connector_init["resolver"] = IPv4Resolver()


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())

    dp.message.outer_middleware(AuthMiddleware())
    dp.message.outer_middleware(RateLimitMiddleware(rate=settings.RATE_LIMIT_PER_MINUTE))
    dp.message.outer_middleware(TopicResolverMiddleware())
    dp.callback_query.outer_middleware(AuthMiddleware())

    commands.router.message.middleware(AdminOnlyInteractionMiddleware())
    callbacks.router.callback_query.middleware(AdminOnlyInteractionMiddleware())

    dp.include_router(commands.router)
    dp.include_router(forum_messages.router)
    dp.include_router(callbacks.router)
    return dp


async def main_polling() -> None:
    """Polling mode for local development."""
    bot = create_bot()
    configure_bot_network(bot)
    dp = create_dispatcher()

    scheduler = setup_scheduler(bot)
    scheduler.start()

    await set_commands(bot)
    logger.info("Starting bot in polling mode")
    try:
        await dp.start_polling(bot, allowed_updates=["message", "callback_query"])
    finally:
        scheduler.shutdown()
        await bot.session.close()


def main_webhook() -> None:
    """Webhook mode for production."""
    from aiohttp import web
    from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

    bot = create_bot()
    dp = create_dispatcher()
    scheduler = setup_scheduler(bot)

    webhook_path = f"/webhook/{settings.BOT_TOKEN}"
    webhook_url = f"{settings.WEBHOOK_BASE_URL.rstrip('/')}{webhook_path}"

    async def bootstrap_runtime() -> None:
        # Give aiohttp a moment to bind the port before Telegram checks the webhook URL.
        await asyncio.sleep(2)
        await _run_noncritical_step("LLM warmup", LLMService().warmup)
        webhook_ready = await _run_noncritical_step(
            "Webhook registration",
            lambda: bot.set_webhook(
                url=webhook_url,
                allowed_updates=["message", "callback_query"],
            ),
        )
        await _run_noncritical_step("Bot command sync", lambda: set_commands(bot))
        if webhook_ready:
            logger.info("Webhook registered: %s", webhook_url)
        else:
            logger.warning("Webhook was not confirmed during startup: %s", webhook_url)

    async def on_startup(app: web.Application) -> None:
        configure_bot_network(bot)
        scheduler.start()
        app["bootstrap_task"] = asyncio.create_task(bootstrap_runtime())

    async def on_shutdown(app: web.Application) -> None:
        bootstrap_task = app.get("bootstrap_task")
        if bootstrap_task is not None and not bootstrap_task.done():
            bootstrap_task.cancel()
            with suppress(asyncio.CancelledError):
                await bootstrap_task
        scheduler.shutdown()
        await _run_noncritical_step("Webhook cleanup", lambda: bot.delete_webhook(), attempts=1)
        await bot.session.close()
        logger.info("Webhook removed")

    app = web.Application()
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    handler.register(app, path=webhook_path)
    setup_application(app, dp, bot=bot)

    web.run_app(app, host="0.0.0.0", port=settings.BOT_PORT)


if __name__ == "__main__":
    if settings.WEBHOOK_BASE_URL:
        main_webhook()
    else:
        asyncio.run(main_polling())
