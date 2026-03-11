"""
main.py — точка входа.
Запускает Discord-бот и Telegram-бот в одном asyncio event loop.
"""
from __future__ import annotations

import asyncio
import logging
import signal
import sys

from src.config import get_settings
from src.logging_config import setup_logging

settings = get_settings()
setup_logging(settings.log_level)

log = logging.getLogger(__name__)


async def run_discord_bot(discord_bot) -> None:
    """Запускает Discord-бот."""
    log.info("Starting Discord bot...")
    async with discord_bot:
        await discord_bot.start(settings.discord_token)


async def run_telegram_bot(bot, dp) -> None:
    """Запускает Telegram-бот (polling)."""
    from src.telegram_bot.bot import setup_bot_commands

    log.info("Starting Telegram bot...")
    await setup_bot_commands(bot)
    await dp.start_polling(bot, allowed_updates=["message", "callback_query"])


async def wait_for_db() -> None:
    """Ожидает готовности PostgreSQL."""
    import asyncpg
    from src.config import get_settings

    s = get_settings()
    for attempt in range(30):
        try:
            conn = await asyncpg.connect(
                host=s.postgres_host,
                port=s.postgres_port,
                user=s.postgres_user,
                password=s.postgres_password,
                database=s.postgres_db,
            )
            await conn.close()
            log.info("PostgreSQL is ready")
            return
        except Exception as e:
            log.warning(f"DB not ready (attempt {attempt + 1}/30): {e}")
            await asyncio.sleep(2)

    log.error("PostgreSQL did not become ready in time")
    sys.exit(1)


async def main() -> None:
    log.info("=" * 60)
    log.info("Discord–Telegram Bridge starting up")
    log.info(f"Environment: {settings.environment}")
    log.info("=" * 60)

    # Ждём БД
    await wait_for_db()

    # Создаём Discord бота
    from src.discord_bot.bot import create_discord_bot
    discord_bot = create_discord_bot()

    # Создаём Telegram бота
    from src.telegram_bot.bot import create_telegram_bot
    tg_bot, tg_dp = create_telegram_bot()

    # Запускаем оба бота параллельно
    tasks = [
        asyncio.create_task(run_discord_bot(discord_bot), name="discord"),
        asyncio.create_task(run_telegram_bot(tg_bot, tg_dp), name="telegram"),
    ]

    # Обработка сигналов для graceful shutdown
    loop = asyncio.get_event_loop()

    def shutdown():
        log.info("Shutdown signal received")
        for task in tasks:
            task.cancel()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, shutdown)

    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        log.info("Tasks cancelled, shutting down gracefully...")
    except Exception as e:
        log.exception(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        # Закрываем Telegram бота
        try:
            await tg_bot.session.close()
        except Exception:
            pass

        # Закрываем Discord бота
        if not discord_bot.is_closed():
            await discord_bot.close()

        # Закрываем DB engine
        from src.database.session import engine
        await engine.dispose()

        log.info("Shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())