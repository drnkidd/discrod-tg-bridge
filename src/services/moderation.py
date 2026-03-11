"""
ModerationService — выполняет модерационные действия на Discord
и сохраняет их в базу данных.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple

import discord
from sqlalchemy import select, update

from src.config import get_settings
from src.database.models import Ban, Mute, Warning, ModerationLog
from src.database.session import get_session
from src.services.utils import seconds_to_human, utcnow

log = logging.getLogger(__name__)
settings = get_settings()


class ModerationResult:
    def __init__(
        self,
        success: bool,
        message: str,
        discord_username: Optional[str] = None,
    ):
        self.success = success
        self.message = message
        self.discord_username = discord_username


class ModerationService:
    """Stateless сервис модерации — принимает discord.Client через аргумент."""

    # ── Вспомогательные ──────────────────────────────────────

    async def _get_guild(self, client: discord.Client) -> Optional[discord.Guild]:
        return client.get_guild(settings.discord_guild_id)

    async def _get_member(
        self, guild: discord.Guild, user_id: int
    ) -> Optional[discord.Member]:
        member = guild.get_member(user_id)
        if member is None:
            try:
                member = await guild.fetch_member(user_id)
            except discord.NotFound:
                return None
        return member

    async def _log_action(
        self,
        action: str,
        discord_user_id: str,
        discord_username: Optional[str],
        moderator_telegram_id: int,
        moderator_username: Optional[str],
        reason: Optional[str],
        duration_seconds: Optional[int],
        success: bool,
        error_message: Optional[str] = None,
        ticket_id: Optional[int] = None,
    ) -> None:
        async with get_session() as session:
            entry = ModerationLog(
                action=action,
                discord_user_id=discord_user_id,
                discord_username=discord_username,
                reason=reason,
                duration_seconds=duration_seconds,
                moderator_telegram_id=moderator_telegram_id,
                moderator_username=moderator_username,
                guild_id=str(settings.discord_guild_id),
                ticket_id=ticket_id,
                success=success,
                error_message=error_message,
            )
            session.add(entry)

    # ── BAN ──────────────────────────────────────────────────

    async def ban(
        self,
        client: discord.Client,
        discord_user_id: int,
        reason: str,
        duration_seconds: Optional[int],
        moderator_telegram_id: int,
        moderator_username: Optional[str],
        ticket_id: Optional[int] = None,
    ) -> ModerationResult:
        guild = await self._get_guild(client)
        if not guild:
            return ModerationResult(False, "❌ Сервер Discord не найден")

        member = await self._get_member(guild, discord_user_id)
        discord_username = str(member) if member else f"ID:{discord_user_id}"

        try:
            expires_at = None
            if duration_seconds:
                expires_at = utcnow() + timedelta(seconds=duration_seconds)

            await guild.ban(
                discord.Object(id=discord_user_id),
                reason=f"[TG Mod] {reason}",
                delete_message_days=0,
            )

            async with get_session() as session:
                ban = Ban(
                    discord_user_id=str(discord_user_id),
                    discord_username=discord_username,
                    reason=reason,
                    duration_seconds=duration_seconds,
                    expires_at=expires_at,
                    moderator_telegram_id=moderator_telegram_id,
                    moderator_username=moderator_username,
                    guild_id=str(settings.discord_guild_id),
                    is_active=True,
                )
                session.add(ban)

            await self._log_action(
                "ban", str(discord_user_id), discord_username,
                moderator_telegram_id, moderator_username, reason,
                duration_seconds, True, ticket_id=ticket_id,
            )

            duration_str = seconds_to_human(duration_seconds)
            return ModerationResult(
                True,
                f"✅ <b>{discord_username}</b> забанен на <b>{duration_str}</b>\n"
                f"📋 Причина: {reason}",
                discord_username,
            )
        except discord.Forbidden:
            msg = "❌ У бота нет прав для бана этого пользователя"
        except discord.HTTPException as e:
            msg = f"❌ Ошибка Discord: {e}"
        except Exception as e:
            log.exception("Ban error")
            msg = f"❌ Внутренняя ошибка: {e}"

        await self._log_action(
            "ban", str(discord_user_id), discord_username,
            moderator_telegram_id, moderator_username, reason,
            duration_seconds, False, error_message=msg, ticket_id=ticket_id,
        )
        return ModerationResult(False, msg, discord_username)

    # ── UNBAN ─────────────────────────────────────────────────

    async def unban(
        self,
        client: discord.Client,
        discord_user_id: int,
        moderator_telegram_id: int,
        moderator_username: Optional[str],
    ) -> ModerationResult:
        guild = await self._get_guild(client)
        if not guild:
            return ModerationResult(False, "❌ Сервер Discord не найден")

        try:
            user = discord.Object(id=discord_user_id)
            await guild.unban(user, reason="[TG Mod] Разбан")

            now = utcnow()
            async with get_session() as session:
                await session.execute(
                    update(Ban)
                    .where(
                        Ban.discord_user_id == str(discord_user_id),
                        Ban.is_active == True,
                    )
                    .values(is_active=False, unbanned_at=now, unbanned_by=moderator_telegram_id)
                )

            await self._log_action(
                "unban", str(discord_user_id), None,
                moderator_telegram_id, moderator_username, None, None, True,
            )
            return ModerationResult(True, f"✅ Пользователь <b>{discord_user_id}</b> разбанен")
        except discord.NotFound:
            return ModerationResult(False, "❌ Пользователь не найден в списке банов")
        except discord.Forbidden:
            return ModerationResult(False, "❌ У бота нет прав для разбана")
        except Exception as e:
            log.exception("Unban error")
            return ModerationResult(False, f"❌ Ошибка: {e}")

    # ── MUTE (Discord Timeout) ────────────────────────────────

    async def mute(
        self,
        client: discord.Client,
        discord_user_id: int,
        reason: str,
        duration_seconds: int,
        moderator_telegram_id: int,
        moderator_username: Optional[str],
        ticket_id: Optional[int] = None,
    ) -> ModerationResult:
        guild = await self._get_guild(client)
        if not guild:
            return ModerationResult(False, "❌ Сервер Discord не найден")

        member = await self._get_member(guild, discord_user_id)
        if not member:
            return ModerationResult(False, "❌ Пользователь не найден на сервере")

        discord_username = str(member)

        # Discord timeout: максимум 28 дней
        MAX_TIMEOUT = 28 * 24 * 3600
        effective_duration = min(duration_seconds, MAX_TIMEOUT)
        expires_at = utcnow() + timedelta(seconds=effective_duration)

        try:
            await member.timeout(expires_at, reason=f"[TG Mod] {reason}")

            async with get_session() as session:
                mute = Mute(
                    discord_user_id=str(discord_user_id),
                    discord_username=discord_username,
                    reason=reason,
                    duration_seconds=effective_duration,
                    expires_at=expires_at,
                    moderator_telegram_id=moderator_telegram_id,
                    moderator_username=moderator_username,
                    guild_id=str(settings.discord_guild_id),
                    is_active=True,
                )
                session.add(mute)

            await self._log_action(
                "mute", str(discord_user_id), discord_username,
                moderator_telegram_id, moderator_username, reason,
                effective_duration, True, ticket_id=ticket_id,
            )

            duration_str = seconds_to_human(effective_duration)
            return ModerationResult(
                True,
                f"🔇 <b>{discord_username}</b> замьючен на <b>{duration_str}</b>\n"
                f"📋 Причина: {reason}",
                discord_username,
            )
        except discord.Forbidden:
            msg = "❌ У бота нет прав для мута этого пользователя"
        except discord.HTTPException as e:
            msg = f"❌ Ошибка Discord: {e}"
        except Exception as e:
            log.exception("Mute error")
            msg = f"❌ Внутренняя ошибка: {e}"

        await self._log_action(
            "mute", str(discord_user_id), discord_username,
            moderator_telegram_id, moderator_username, reason,
            duration_seconds, False, error_message=msg, ticket_id=ticket_id,
        )
        return ModerationResult(False, msg, discord_username)

    # ── UNMUTE ────────────────────────────────────────────────

    async def unmute(
        self,
        client: discord.Client,
        discord_user_id: int,
        moderator_telegram_id: int,
        moderator_username: Optional[str],
    ) -> ModerationResult:
        guild = await self._get_guild(client)
        if not guild:
            return ModerationResult(False, "❌ Сервер Discord не найден")

        member = await self._get_member(guild, discord_user_id)
        if not member:
            return ModerationResult(False, "❌ Пользователь не найден на сервере")

        discord_username = str(member)

        try:
            await member.timeout(None, reason="[TG Mod] Размут")

            now = utcnow()
            async with get_session() as session:
                await session.execute(
                    update(Mute)
                    .where(
                        Mute.discord_user_id == str(discord_user_id),
                        Mute.is_active == True,
                    )
                    .values(is_active=False, unmuted_at=now, unmuted_by=moderator_telegram_id)
                )

            await self._log_action(
                "unmute", str(discord_user_id), discord_username,
                moderator_telegram_id, moderator_username, None, None, True,
            )
            return ModerationResult(True, f"🔊 <b>{discord_username}</b> размьючен")
        except discord.Forbidden:
            return ModerationResult(False, "❌ У бота нет прав для размута")
        except Exception as e:
            log.exception("Unmute error")
            return ModerationResult(False, f"❌ Ошибка: {e}")

    # ── WARN ──────────────────────────────────────────────────

    async def warn(
        self,
        client: discord.Client,
        discord_user_id: int,
        reason: str,
        moderator_telegram_id: int,
        moderator_username: Optional[str],
        ticket_id: Optional[int] = None,
    ) -> ModerationResult:
        guild = await self._get_guild(client)
        if not guild:
            return ModerationResult(False, "❌ Сервер Discord не найден")

        member = await self._get_member(guild, discord_user_id)
        discord_username = str(member) if member else f"ID:{discord_user_id}"

        try:
            async with get_session() as session:
                warning = Warning(
                    discord_user_id=str(discord_user_id),
                    discord_username=discord_username,
                    reason=reason,
                    moderator_telegram_id=moderator_telegram_id,
                    moderator_username=moderator_username,
                    guild_id=str(settings.discord_guild_id),
                )
                session.add(warning)

            await self._log_action(
                "warn", str(discord_user_id), discord_username,
                moderator_telegram_id, moderator_username, reason, None, True,
                ticket_id=ticket_id,
            )

            # Попытка отправить DM пользователю на Discord
            if member:
                try:
                    await member.send(
                        f"⚠️ Вы получили предупреждение на сервере.\n"
                        f"**Причина:** {reason}"
                    )
                except Exception:
                    pass  # DM отключены — не критично

            return ModerationResult(
                True,
                f"⚠️ <b>{discord_username}</b> получил предупреждение\n"
                f"📋 Причина: {reason}",
                discord_username,
            )
        except Exception as e:
            log.exception("Warn error")
            return ModerationResult(False, f"❌ Ошибка: {e}")

    # ── HISTORY ───────────────────────────────────────────────

    async def get_history(self, discord_user_id: int) -> str:
        uid = str(discord_user_id)
        async with get_session() as session:
            warns = (
                await session.execute(
                    select(Warning)
                    .where(Warning.discord_user_id == uid)
                    .order_by(Warning.created_at.desc())
                    .limit(10)
                )
            ).scalars().all()

            bans = (
                await session.execute(
                    select(Ban)
                    .where(Ban.discord_user_id == uid)
                    .order_by(Ban.created_at.desc())
                    .limit(10)
                )
            ).scalars().all()

            mutes = (
                await session.execute(
                    select(Mute)
                    .where(Mute.discord_user_id == uid)
                    .order_by(Mute.created_at.desc())
                    .limit(10)
                )
            ).scalars().all()

        lines = [f"📂 <b>История модерации для ID {discord_user_id}</b>\n"]

        if not warns and not bans and not mutes:
            lines.append("✅ Нарушений не найдено")
            return "\n".join(lines)

        if warns:
            lines.append(f"⚠️ <b>Предупреждения ({len(warns)}):</b>")
            for w in warns:
                ts = w.created_at.strftime("%d.%m.%Y %H:%M") if w.created_at else "?"
                lines.append(f"  • {ts} — {w.reason} (mod: @{w.moderator_username})")

        if bans:
            lines.append(f"\n🔨 <b>Баны ({len(bans)}):</b>")
            for b in bans:
                ts = b.created_at.strftime("%d.%m.%Y %H:%M") if b.created_at else "?"
                dur = seconds_to_human(b.duration_seconds)
                status = "активен" if b.is_active else "снят"
                lines.append(f"  • {ts} [{status}] {dur} — {b.reason}")

        if mutes:
            lines.append(f"\n🔇 <b>Муты ({len(mutes)}):</b>")
            for m in mutes:
                ts = m.created_at.strftime("%d.%m.%Y %H:%M") if m.created_at else "?"
                dur = seconds_to_human(m.duration_seconds)
                status = "активен" if m.is_active else "снят"
                lines.append(f"  • {ts} [{status}] {dur} — {m.reason}")

        return "\n".join(lines)


# Глобальный экземпляр
moderation_service = ModerationService()