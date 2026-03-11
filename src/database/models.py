"""
SQLAlchemy ORM Models
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


# ──────────────────────────────────────────────────────────────
class AdminUser(Base):
    __tablename__ = "admin_users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(100))
    added_by: Mapped[Optional[int]] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    def __repr__(self) -> str:
        return f"<AdminUser tg={self.telegram_id} @{self.username}>"


# ──────────────────────────────────────────────────────────────
class Warning(Base):
    __tablename__ = "warnings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    discord_user_id: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    discord_username: Mapped[Optional[str]] = mapped_column(String(100))
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    moderator_telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    moderator_username: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    guild_id: Mapped[str] = mapped_column(String(30), nullable=False)


# ──────────────────────────────────────────────────────────────
class Ban(Base):
    __tablename__ = "bans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    discord_user_id: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    discord_username: Mapped[Optional[str]] = mapped_column(String(100))
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    duration_seconds: Mapped[Optional[int]] = mapped_column(BigInteger)  # NULL = perm
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    moderator_telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    moderator_username: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    unbanned_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    unbanned_by: Mapped[Optional[int]] = mapped_column(BigInteger)
    guild_id: Mapped[str] = mapped_column(String(30), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


# ──────────────────────────────────────────────────────────────
class Mute(Base):
    __tablename__ = "mutes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    discord_user_id: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    discord_username: Mapped[Optional[str]] = mapped_column(String(100))
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    duration_seconds: Mapped[int] = mapped_column(BigInteger, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    moderator_telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    moderator_username: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    unmuted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    unmuted_by: Mapped[Optional[int]] = mapped_column(BigInteger)
    guild_id: Mapped[str] = mapped_column(String(30), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


# ──────────────────────────────────────────────────────────────
class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    discord_message_id: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    discord_channel_id: Mapped[str] = mapped_column(String(30), nullable=False)
    discord_user_id: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    discord_username: Mapped[Optional[str]] = mapped_column(String(100))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    telegram_message_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    telegram_chat_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(20), default="open")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    closed_by: Mapped[Optional[int]] = mapped_column(BigInteger)
    guild_id: Mapped[str] = mapped_column(String(30), nullable=False)


# ──────────────────────────────────────────────────────────────
class ModerationLog(Base):
    __tablename__ = "moderation_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    action: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    discord_user_id: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    discord_username: Mapped[Optional[str]] = mapped_column(String(100))
    reason: Mapped[Optional[str]] = mapped_column(Text)
    duration_seconds: Mapped[Optional[int]] = mapped_column(BigInteger)
    moderator_telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    moderator_username: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    guild_id: Mapped[str] = mapped_column(String(30), nullable=False)
    ticket_id: Mapped[Optional[int]] = mapped_column(Integer)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text)


# ──────────────────────────────────────────────────────────────
class MonitoredChannel(Base):
    __tablename__ = "monitored_channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_id: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    channel_name: Mapped[Optional[str]] = mapped_column(String(100))
    category_id: Mapped[Optional[str]] = mapped_column(String(30))
    category_name: Mapped[Optional[str]] = mapped_column(String(100))
    guild_id: Mapped[str] = mapped_column(String(30), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )