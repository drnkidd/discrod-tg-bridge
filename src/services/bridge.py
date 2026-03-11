"""
Bridge — центральный объект, связывающий Discord-бот и Telegram-бот.
Оба бота хранят ссылку на один экземпляр Bridge.
"""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    import discord
    from aiogram import Bot as TelegramBot

log = logging.getLogger(__name__)


class Bridge:
    """Singleton-подобный объект, хранящий ссылки на оба бота."""

    def __init__(self) -> None:
        self._discord_client: Optional["discord.Client"] = None
        self._telegram_bot: Optional["TelegramBot"] = None
        self._ready = asyncio.Event()

    # ── Регистрация ботов ─────────────────────────────────────
    def set_discord_client(self, client: "discord.Client") -> None:
        self._discord_client = client
        self._check_ready()

    def set_telegram_bot(self, bot: "TelegramBot") -> None:
        self._telegram_bot = bot
        self._check_ready()

    def _check_ready(self) -> None:
        if self._discord_client and self._telegram_bot:
            self._ready.set()
            log.info("Bridge: оба бота зарегистрированы, мост готов")

    async def wait_ready(self) -> None:
        await self._ready.wait()

    # ── Геттеры ───────────────────────────────────────────────
    @property
    def discord(self) -> "discord.Client":
        if not self._discord_client:
            raise RuntimeError("Discord client not registered in Bridge")
        return self._discord_client

    @property
    def telegram(self) -> "TelegramBot":
        if not self._telegram_bot:
            raise RuntimeError("Telegram bot not registered in Bridge")
        return self._telegram_bot


# Глобальный экземпляр
bridge = Bridge()