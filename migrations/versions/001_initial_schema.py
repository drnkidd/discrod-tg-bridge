"""initial schema

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── admin_users ──────────────────────────────────────────────
    op.create_table(
        "admin_users",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False, unique=True),
        sa.Column("username", sa.String(100), nullable=True),
        sa.Column("added_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
    )

    # ── warnings ─────────────────────────────────────────────────
    op.create_table(
        "warnings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("discord_user_id", sa.String(30), nullable=False),
        sa.Column("discord_username", sa.String(100), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("moderator_telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("moderator_username", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("guild_id", sa.String(30), nullable=False),
    )
    op.create_index("ix_warnings_discord_user_id", "warnings", ["discord_user_id"])

    # ── bans ─────────────────────────────────────────────────────
    op.create_table(
        "bans",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("discord_user_id", sa.String(30), nullable=False),
        sa.Column("discord_username", sa.String(100), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("duration_seconds", sa.BigInteger(), nullable=True),  # NULL = permanent
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("moderator_telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("moderator_username", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("unbanned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("unbanned_by", sa.BigInteger(), nullable=True),
        sa.Column("guild_id", sa.String(30), nullable=False),
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
    )
    op.create_index("ix_bans_discord_user_id", "bans", ["discord_user_id"])

    # ── mutes ─────────────────────────────────────────────────────
    op.create_table(
        "mutes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("discord_user_id", sa.String(30), nullable=False),
        sa.Column("discord_username", sa.String(100), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("duration_seconds", sa.BigInteger(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("moderator_telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("moderator_username", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("unmuted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("unmuted_by", sa.BigInteger(), nullable=True),
        sa.Column("guild_id", sa.String(30), nullable=False),
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
    )
    op.create_index("ix_mutes_discord_user_id", "mutes", ["discord_user_id"])

    # ── tickets ───────────────────────────────────────────────────
    op.create_table(
        "tickets",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("discord_message_id", sa.String(30), nullable=False, unique=True),
        sa.Column("discord_channel_id", sa.String(30), nullable=False),
        sa.Column("discord_user_id", sa.String(30), nullable=False),
        sa.Column("discord_username", sa.String(100), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("telegram_message_id", sa.BigInteger(), nullable=True),
        sa.Column("telegram_chat_id", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(20), default="open", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_by", sa.BigInteger(), nullable=True),
        sa.Column("guild_id", sa.String(30), nullable=False),
    )
    op.create_index("ix_tickets_discord_user_id", "tickets", ["discord_user_id"])

    # ── moderation_log ────────────────────────────────────────────
    op.create_table(
        "moderation_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("action", sa.String(20), nullable=False),  # ban/unban/mute/unmute/warn
        sa.Column("discord_user_id", sa.String(30), nullable=False),
        sa.Column("discord_username", sa.String(100), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("duration_seconds", sa.BigInteger(), nullable=True),
        sa.Column("moderator_telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("moderator_username", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("guild_id", sa.String(30), nullable=False),
        sa.Column("ticket_id", sa.Integer(), nullable=True),
        sa.Column("success", sa.Boolean(), default=True, nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.create_index("ix_modlog_discord_user_id", "moderation_log", ["discord_user_id"])
    op.create_index("ix_modlog_action", "moderation_log", ["action"])

    # ── monitored_channels ────────────────────────────────────────
    op.create_table(
        "monitored_channels",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("channel_id", sa.String(30), nullable=False, unique=True),
        sa.Column("channel_name", sa.String(100), nullable=True),
        sa.Column("category_id", sa.String(30), nullable=True),
        sa.Column("category_name", sa.String(100), nullable=True),
        sa.Column("guild_id", sa.String(30), nullable=False),
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("monitored_channels")
    op.drop_table("moderation_log")
    op.drop_table("tickets")
    op.drop_table("mutes")
    op.drop_table("bans")
    op.drop_table("warnings")
    op.drop_table("admin_users")