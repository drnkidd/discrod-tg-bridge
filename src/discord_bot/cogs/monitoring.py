"""
Monitoring Cog — мониторинг каналов и пингов ролей,
отправка уведомлений в Telegram.
"""
from __future__ import annotations

import logging
from typing import Optional

import discord
from discord.ext import commands

from src.config import get_settings
from src.services.bridge import bridge

log = logging.getLogger(__name__)
settings = get_settings()

# Максимальная длина сообщения для Telegram
TG_MAX_LEN = 4096
MSG_PREVIEW_LEN = 800


def _truncate(text: str, limit: int = MSG_PREVIEW_LEN) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "…"


def _escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _build_notification(message: discord.Message) -> str:
    """Форматирует сообщение Discord для отправки в Telegram."""
    channel = message.channel
    category = getattr(channel, "category", None)

    category_str = f"📂 <b>{_escape_html(category.name)}</b> / " if category else ""
    channel_str = f"#{_escape_html(channel.name)}"
    author = _escape_html(str(message.author))
    content = _escape_html(_truncate(message.content or ""))

    lines = [
        f"💬 {category_str}{channel_str}",
        f"👤 <b>{author}</b>",
    ]
    if content:
        lines.append(f"📝 {content}")

    if message.attachments:
        files = ", ".join(a.filename for a in message.attachments[:3])
        lines.append(f"📎 Вложения: {files}")

    if message.embeds:
        embed = message.embeds[0]
        if embed.title:
            lines.append(f"🔗 Embed: {_escape_html(embed.title)}")

    lines.append(
        f"\n🔗 <a href='https://discord.com/channels/"
        f"{message.guild.id}/{channel.id}/{message.id}'>Перейти к сообщению</a>"
    )
    return "\n".join(lines)


def _build_ping_notification(message: discord.Message, pinged_roles: list) -> str:
    """Форматирует уведомление о пинге роли для Telegram."""
    channel = message.channel
    category = getattr(channel, "category", None)

    category_str = f"📂 {_escape_html(category.name)} / " if category else ""
    channel_str = f"#{_escape_html(channel.name)}"
    author = _escape_html(str(message.author))
    content = _escape_html(_truncate(message.content or ""))

    roles_str = ", ".join(f"@{_escape_html(r.name)}" for r in pinged_roles)

    lines = [
        f"🔔 <b>ПИНГ РОЛЕЙ: {roles_str}</b>",
        f"📍 {category_str}{channel_str}",
        f"👤 <b>{author}</b>",
    ]
    if content:
        lines.append(f"📝 {content}")

    if message.attachments:
        files = ", ".join(a.filename for a in message.attachments[:3])
        lines.append(f"📎 Вложения: {files}")

    lines.append(
        f"\n🔗 <a href='https://discord.com/channels/"
        f"{message.guild.id}/{channel.id}/{message.id}'>Перейти к сообщению</a>"
    )
    return "\n".join(lines)


class MonitoringCog(commands.Cog, name="Monitoring"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _should_monitor(self, channel: discord.TextChannel) -> bool:
        """Проверяет, нужно ли мониторить этот канал."""
        # Проверяем прямое совпадение канала
        if channel.id in settings.monitored_channel_ids:
            return True

        # Проверяем категорию
        if channel.category_id and channel.category_id in settings.monitored_category_ids:
            return True

        return False

    def _get_watched_role_pings(
        self, message: discord.Message
    ) -> list[discord.Role]:
        """Возвращает список отслеживаемых ролей, которые пингованы в сообщении."""
        if not message.role_mentions:
            return []

        return [
            role
            for role in message.role_mentions
            if role.id in settings.watched_role_ids
        ]

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Игнорируем ботов
        if message.author.bot:
            return

        # Только сообщения с нашего сервера
        if not message.guild or message.guild.id != settings.discord_guild_id:
            return

        # Пропускаем канал тикетов (обрабатывается отдельным когом)
        if message.channel.id == settings.discord_tickets_channel_id:
            return

        channel = message.channel
        if not isinstance(channel, discord.TextChannel):
            return

        # ── Пинги отслеживаемых ролей ─────────────────────────
        watched_roles = self._get_watched_role_pings(message)
        if watched_roles:
            await self._send_ping_notification(message, watched_roles)

        # ── Обычный мониторинг каналов ────────────────────────
        if self._should_monitor(channel):
            await self._send_channel_notification(message)

    async def _send_channel_notification(self, message: discord.Message) -> None:
        """Отправляет уведомление о сообщении в Telegram."""
        try:
            text = _build_notification(message)
            await bridge.telegram.send_message(
                chat_id=settings.telegram_notifications_chat_id,
                text=text,
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
        except Exception as e:
            log.error(f"Failed to send channel notification: {e}")

    async def _send_ping_notification(
        self, message: discord.Message, pinged_roles: list
    ) -> None:
        """Отправляет уведомление о пинге роли в Telegram."""
        try:
            text = _build_ping_notification(message, pinged_roles)
            await bridge.telegram.send_message(
                chat_id=settings.telegram_pings_chat_id,
                text=text,
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
        except Exception as e:
            log.error(f"Failed to send ping notification: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(MonitoringCog(bot))