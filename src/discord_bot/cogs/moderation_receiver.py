"""
ModerationReceiver Cog — принимает команды модерации от Telegram
через asyncio.Queue и выполняет их на Discord.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

import discord
from discord.ext import commands, tasks

from src.services.bridge import bridge

log = logging.getLogger(__name__)

# Глобальная очередь команд (заполняется из Telegram-бота)
moderation_queue: asyncio.Queue = asyncio.Queue()


@dataclass
class ModerationCommand:
    action: str           # ban / unban / mute / unmute / warn
    discord_user_id: int
    reason: Optional[str]
    duration_seconds: Optional[int]
    moderator_telegram_id: int
    moderator_username: Optional[str]
    ticket_id: Optional[int]
    future: asyncio.Future  # результат отправляется сюда


class ModerationReceiverCog(commands.Cog, name="ModerationReceiver"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.process_queue.start()

    def cog_unload(self):
        self.process_queue.cancel()

    @tasks.loop(seconds=0.1)
    async def process_queue(self):
        """Обрабатывает команды из очереди."""
        try:
            cmd: ModerationCommand = moderation_queue.get_nowait()
        except asyncio.QueueEmpty:
            return

        from src.services.moderation import moderation_service

        try:
            if cmd.action == "ban":
                result = await moderation_service.ban(
                    self.bot, cmd.discord_user_id, cmd.reason,
                    cmd.duration_seconds, cmd.moderator_telegram_id,
                    cmd.moderator_username, cmd.ticket_id,
                )
            elif cmd.action == "unban":
                result = await moderation_service.unban(
                    self.bot, cmd.discord_user_id,
                    cmd.moderator_telegram_id, cmd.moderator_username,
                )
            elif cmd.action == "mute":
                result = await moderation_service.mute(
                    self.bot, cmd.discord_user_id, cmd.reason,
                    cmd.duration_seconds, cmd.moderator_telegram_id,
                    cmd.moderator_username, cmd.ticket_id,
                )
            elif cmd.action == "unmute":
                result = await moderation_service.unmute(
                    self.bot, cmd.discord_user_id,
                    cmd.moderator_telegram_id, cmd.moderator_username,
                )
            elif cmd.action == "warn":
                result = await moderation_service.warn(
                    self.bot, cmd.discord_user_id, cmd.reason,
                    cmd.moderator_telegram_id, cmd.moderator_username,
                    cmd.ticket_id,
                )
            else:
                from src.services.moderation import ModerationResult
                result = ModerationResult(False, f"❌ Неизвестное действие: {cmd.action}")

            if not cmd.future.done():
                cmd.future.set_result(result)
        except Exception as e:
            log.exception(f"Error processing moderation command {cmd.action}")
            if not cmd.future.done():
                from src.services.moderation import ModerationResult
                cmd.future.set_result(ModerationResult(False, f"❌ Ошибка: {e}"))

    @process_queue.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(ModerationReceiverCog(bot))