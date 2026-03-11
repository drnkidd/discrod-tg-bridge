"""
Discord Bot — основной файл
"""
from __future__ import annotations

import logging

import discord
from discord.ext import commands

from src.config import get_settings
from src.services.bridge import bridge

log = logging.getLogger(__name__)
settings = get_settings()


def create_discord_bot() -> commands.Bot:
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    intents.guilds = True
    intents.moderation = True

    bot = commands.Bot(
        command_prefix="!",
        intents=intents,
        help_command=None,
    )

    @bot.event
    async def on_ready():
        log.info(f"Discord бот запущен как {bot.user} (ID: {bot.user.id})")
        bridge.set_discord_client(bot)

        # Загружаем коги
        for cog in ["monitoring", "tickets", "moderation_receiver"]:
            try:
                await bot.load_extension(f"src.discord_bot.cogs.{cog}")
                log.info(f"Loaded cog: {cog}")
            except Exception as e:
                log.error(f"Failed to load cog {cog}: {e}")

        await bot.tree.sync(guild=discord.Object(id=settings.discord_guild_id))
        log.info("Slash commands synced")

    @bot.event
    async def on_error(event, *args, **kwargs):
        log.exception(f"Discord error in event {event}")

    return bot