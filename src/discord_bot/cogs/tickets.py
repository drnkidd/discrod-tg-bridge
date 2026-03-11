"""
Tickets Cog — мониторинг канала тикетов Discord,
пересылка в Telegram с кнопками модерации.
"""
from __future__ import annotations

import logging

import discord
from discord.ext import commands

from src.config import get_settings
from src.database.models import Ticket
from src.database.session import get_session
from src.services.bridge import bridge

log = logging.getLogger(__name__)
settings = get_settings()


def _escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _build_ticket_text(message: discord.Message) -> str:
    author = message.author
    content = _escape_html(message.content or "")
    avatar_url = author.display_avatar.url if author.display_avatar else ""

    lines = [
        f"🎫 <b>ТИКЕТ #{message.id}</b>",
        f"",
        f"👤 <b>Пользователь:</b> {_escape_html(str(author))}",
        f"🆔 <b>Discord ID:</b> <code>{author.id}</code>",
        f"📅 <b>Время:</b> {message.created_at.strftime('%d.%m.%Y %H:%M')} UTC",
        f"",
        f"📝 <b>Сообщение:</b>",
        f"{content}",
    ]

    if message.attachments:
        lines.append("")
        lines.append(f"📎 <b>Вложения ({len(message.attachments)}):</b>")
        for att in message.attachments[:5]:
            lines.append(f"  • <a href='{att.url}'>{_escape_html(att.filename)}</a>")

    lines.append(
        f"\n🔗 <a href='https://discord.com/channels/"
        f"{message.guild.id}/{message.channel.id}/{message.id}'>Перейти к сообщению</a>"
    )
    return "\n".join(lines)


class TicketsCog(commands.Cog, name="Tickets"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        if not message.guild or message.guild.id != settings.discord_guild_id:
            return

        if message.channel.id != settings.discord_tickets_channel_id:
            return

        await self._process_ticket(message)

    async def _process_ticket(self, message: discord.Message) -> None:
        """Обрабатывает новый тикет: сохраняет в БД и отправляет в Telegram."""
        try:
            # Формируем текст тикета
            text = _build_ticket_text(message)

            # Создаём inline-клавиатуру с кнопками модерации
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

            user_id = message.author.id
            ticket_msg_id = message.id

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="⚠️ Варн",
                        callback_data=f"mod:warn:{user_id}:{ticket_msg_id}",
                    ),
                    InlineKeyboardButton(
                        text="🔇 Мут",
                        callback_data=f"mod:mute:{user_id}:{ticket_msg_id}",
                    ),
                    InlineKeyboardButton(
                        text="🔨 Бан",
                        callback_data=f"mod:ban:{user_id}:{ticket_msg_id}",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text="📜 История",
                        callback_data=f"mod:history:{user_id}:{ticket_msg_id}",
                    ),
                    InlineKeyboardButton(
                        text="✅ Закрыть тикет",
                        callback_data=f"mod:close:{user_id}:{ticket_msg_id}",
                    ),
                ],
            ])

            # Отправляем в Telegram
            tg_msg = await bridge.telegram.send_message(
                chat_id=settings.telegram_tickets_chat_id,
                text=text,
                parse_mode="HTML",
                reply_markup=keyboard,
                disable_web_page_preview=True,
            )

            # Сохраняем тикет в БД
            async with get_session() as session:
                ticket = Ticket(
                    discord_message_id=str(message.id),
                    discord_channel_id=str(message.channel.id),
                    discord_user_id=str(message.author.id),
                    discord_username=str(message.author),
                    content=message.content or "",
                    telegram_message_id=tg_msg.message_id,
                    telegram_chat_id=settings.telegram_tickets_chat_id,
                    status="open",
                    guild_id=str(settings.discord_guild_id),
                )
                session.add(ticket)

            log.info(f"Ticket created: Discord msg {message.id} → TG msg {tg_msg.message_id}")

        except Exception as e:
            log.exception(f"Failed to process ticket {message.id}: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(TicketsCog(bot)) 