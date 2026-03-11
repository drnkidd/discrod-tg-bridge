"""
Telegram Bot — сборка диспетчера и регистрация роутеров
"""
from __future__ import annotations

import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import BotCommand

from src.config import get_settings
from src.services.bridge import bridge
from src.telegram_bot.handlers import common, moderation

log = logging.getLogger(__name__)
settings = get_settings()


def create_telegram_bot() -> tuple[Bot, Dispatcher]:
    # Redis storage для FSM (persist через рестарты)
    storage = RedisStorage.from_url(settings.redis_url)

    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher(storage=storage)

    # Регистрируем роутеры
    dp.include_router(common.router)
    dp.include_router(moderation.router)

    # Регистрируем бот в бридже после создания
    bridge.set_telegram_bot(bot)

    return bot, dp


async def setup_bot_commands(bot: Bot) -> None:
    """Устанавливает меню команд бота в Telegram."""
    commands = [
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="help", description="Справка по командам"),
        BotCommand(command="ban", description="Забанить пользователя"),
        BotCommand(command="unban", description="Разбанить пользователя"),
        BotCommand(command="mute", description="Замьютить пользователя"),
        BotCommand(command="unmute", description="Размьютить пользователя"),
        BotCommand(command="warn", description="Выдать предупреждение"),
        BotCommand(command="history", description="История нарушений"),
        BotCommand(command="admins", description="Список администраторов"),
        BotCommand(command="addadmin", description="Добавить администратора"),
        BotCommand(command="removeadmin", description="Удалить администратора"),
    ]
    await bot.set_my_commands(commands)
    log.info("Bot commands set")