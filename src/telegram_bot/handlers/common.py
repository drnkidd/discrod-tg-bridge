"""
Общие команды Telegram-бота: /start, /help, /admins, /addadmin, /removeadmin
"""
from __future__ import annotations

import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import select, delete

from src.config import get_settings
from src.database.models import AdminUser
from src.database.session import get_session
from src.telegram_bot.filters import AdminFilter, OwnerFilter
from src.telegram_bot.states import AddAdminState

log = logging.getLogger(__name__)
settings = get_settings()

router = Router(name="common")


# ── /start ────────────────────────────────────────────────────
@router.message(Command("start"))
async def cmd_start(msg: Message):
    await msg.answer(
        "🤖 <b>Discord–Telegram Bridge Bot</b>\n\n"
        "Этот бот получает уведомления с Discord-сервера и позволяет "
        "администраторам выполнять модерационные действия.\n\n"
        "<b>Команды модерации:</b>\n"
        "/ban — забанить пользователя\n"
        "/unban — разбанить пользователя\n"
        "/mute — замьютить пользователя\n"
        "/unmute — размьютить пользователя\n"
        "/warn — выдать предупреждение\n"
        "/history — история нарушений\n\n"
        "<b>Управление:</b>\n"
        "/admins — список администраторов\n"
        "/addadmin — добавить администратора\n"
        "/removeadmin — удалить администратора\n",
        parse_mode="HTML",
    )


# ── /help ─────────────────────────────────────────────────────
@router.message(Command("help"), AdminFilter())
async def cmd_help(msg: Message):
    await msg.answer(
        "📖 <b>Справка по командам</b>\n\n"
        "<b>Формат времени:</b> 10m, 2h, 7d, 1w, perm\n"
        "  • s/sec = секунды\n"
        "  • m/min = минуты\n"
        "  • h/hr = часы\n"
        "  • d/day = дни\n"
        "  • w/week = недели\n"
        "  • perm/навсегда = постоянно\n\n"
        "<b>Модерация:</b>\n"
        "/ban &lt;discord_id&gt; — бан\n"
        "/unban &lt;discord_id&gt; — разбан\n"
        "/mute &lt;discord_id&gt; — мут\n"
        "/unmute &lt;discord_id&gt; — размут\n"
        "/warn &lt;discord_id&gt; — предупреждение\n"
        "/history &lt;discord_id&gt; — история\n\n"
        "Или нажимайте кнопки под тикетами 👇",
        parse_mode="HTML",
    )


# ── /admins ───────────────────────────────────────────────────
@router.message(Command("admins"), OwnerFilter())
async def cmd_admins(msg: Message):
    async with get_session() as session:
        result = await session.execute(
            select(AdminUser).where(AdminUser.is_active == True)
        )
        admins = result.scalars().all()

    if not admins:
        await msg.answer("👥 Список администраторов пуст.")
        return

    lines = ["👥 <b>Администраторы бота:</b>\n"]
    for a in admins:
        username = f"@{a.username}" if a.username else "без username"
        lines.append(f"  • <code>{a.telegram_id}</code> — {username}")

    await msg.answer("\n".join(lines), parse_mode="HTML")


# ── /addadmin ─────────────────────────────────────────────────
@router.message(Command("addadmin"), OwnerFilter())
async def cmd_addadmin_start(msg: Message, state: FSMContext):
    args = msg.text.split(maxsplit=1)
    if len(args) > 1:
        # Telegram ID передан сразу
        await _add_admin(msg, args[1].strip(), state)
    else:
        await msg.answer(
            "➕ Введите Telegram ID нового администратора:",
            parse_mode="HTML",
        )
        await state.set_state(AddAdminState.waiting_telegram_id)


@router.message(AddAdminState.waiting_telegram_id, OwnerFilter())
async def cmd_addadmin_receive(msg: Message, state: FSMContext):
    await state.clear()
    await _add_admin(msg, msg.text.strip(), state)


async def _add_admin(msg: Message, raw_id: str, state: FSMContext):
    try:
        tg_id = int(raw_id)
    except ValueError:
        await msg.answer("❌ Некорректный Telegram ID. Должно быть число.")
        return

    async with get_session() as session:
        existing = await session.execute(
            select(AdminUser).where(AdminUser.telegram_id == tg_id)
        )
        if existing.scalar_one_or_none():
            await msg.answer(f"⚠️ Пользователь <code>{tg_id}</code> уже является администратором.", parse_mode="HTML")
            return

        admin = AdminUser(
            telegram_id=tg_id,
            username=None,
            added_by=msg.from_user.id,
            is_active=True,
        )
        session.add(admin)

    await msg.answer(
        f"✅ Администратор <code>{tg_id}</code> успешно добавлен.",
        parse_mode="HTML",
    )
    log.info(f"Admin {tg_id} added by {msg.from_user.id}")


# ── /removeadmin ──────────────────────────────────────────────
@router.message(Command("removeadmin"), OwnerFilter())
async def cmd_removeadmin(msg: Message):
    args = msg.text.split(maxsplit=1)
    if len(args) < 2:
        await msg.answer("Использование: /removeadmin &lt;telegram_id&gt;", parse_mode="HTML")
        return

    try:
        tg_id = int(args[1].strip())
    except ValueError:
        await msg.answer("❌ Некорректный Telegram ID.")
        return

    async with get_session() as session:
        result = await session.execute(
            select(AdminUser).where(AdminUser.telegram_id == tg_id)
        )
        admin = result.scalar_one_or_none()
        if not admin:
            await msg.answer(f"❌ Администратор <code>{tg_id}</code> не найден.", parse_mode="HTML")
            return
        admin.is_active = False

    await msg.answer(
        f"✅ Администратор <code>{tg_id}</code> удалён.",
        parse_mode="HTML",
    )
    log.info(f"Admin {tg_id} removed by {msg.from_user.id}")