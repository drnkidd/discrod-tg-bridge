"""
Moderation handlers — команды /ban, /unban, /mute, /unmute, /warn, /history
и обработчики inline-кнопок из тикетов.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.services.utils import parse_duration, seconds_to_human
from src.telegram_bot.filters import AdminFilter
from src.telegram_bot.keyboards import cancel_keyboard, confirm_keyboard
from src.telegram_bot.states import (
    BanState,
    HistoryState,
    ModActionData,
    MuteState,
    UnbanState,
    UnmuteState,
    WarnState,
)

log = logging.getLogger(__name__)
router = Router(name="moderation")


# ════════════════════════════════════════════════════════════════
#  Вспомогательные функции
# ════════════════════════════════════════════════════════════════

async def _execute_moderation(
    action: str,
    discord_user_id: int,
    reason: Optional[str],
    duration_seconds: Optional[int],
    moderator_id: int,
    moderator_username: Optional[str],
    ticket_id: Optional[int] = None,
):
    """Отправляет команду в очередь Discord-бота и ждёт результата."""
    from src.discord_bot.cogs.moderation_receiver import (
        ModerationCommand,
        moderation_queue,
    )

    loop = asyncio.get_event_loop()
    future = loop.create_future()
    cmd = ModerationCommand(
        action=action,
        discord_user_id=discord_user_id,
        reason=reason,
        duration_seconds=duration_seconds,
        moderator_telegram_id=moderator_id,
        moderator_username=moderator_username,
        ticket_id=ticket_id,
        future=future,
    )
    await moderation_queue.put(cmd)

    try:
        result = await asyncio.wait_for(future, timeout=15.0)
    except asyncio.TimeoutError:
        from src.services.moderation import ModerationResult
        result = ModerationResult(False, "⏱️ Превышено время ожидания ответа от Discord")

    return result


def _get_moderator_info(user) -> tuple:
    return user.id, user.username


# ════════════════════════════════════════════════════════════════
#  /ban
# ════════════════════════════════════════════════════════════════

@router.message(Command("ban"), AdminFilter())
async def cmd_ban_start(msg: Message, state: FSMContext):
    args = msg.text.split(maxsplit=2)
    if len(args) >= 2:
        try:
            uid = int(args[1])
            await state.update_data(**{ModActionData.DISCORD_USER_ID: uid, ModActionData.TICKET_ID: None})
            await msg.answer(
                f"🔨 Бан для <code>{uid}</code>\n"
                "Укажите длительность (например: <code>7d</code>, <code>2h</code>, <code>perm</code>):",
                parse_mode="HTML",
                reply_markup=cancel_keyboard(),
            )
            await state.set_state(BanState.waiting_duration)
            return
        except ValueError:
            pass

    await msg.answer(
        "🔨 <b>Бан пользователя</b>\nВведите Discord ID пользователя:",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(),
    )
    await state.set_state(BanState.waiting_user_id)


@router.message(BanState.waiting_user_id, AdminFilter())
async def ban_receive_user_id(msg: Message, state: FSMContext):
    try:
        uid = int(msg.text.strip())
    except ValueError:
        await msg.answer("❌ Некорректный Discord ID. Введите число:", reply_markup=cancel_keyboard())
        return

    await state.update_data(**{ModActionData.DISCORD_USER_ID: uid, ModActionData.TICKET_ID: None})
    await msg.answer(
        f"✅ ID: <code>{uid}</code>\n"
        "Укажите длительность (например: <code>7d</code>, <code>2h</code>, <code>perm</code>):",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(),
    )
    await state.set_state(BanState.waiting_duration)


@router.message(BanState.waiting_duration, AdminFilter())
async def ban_receive_duration(msg: Message, state: FSMContext):
    text = msg.text.strip()
    duration = parse_duration(text)
    # None = permanent — это допустимо
    await state.update_data(**{ModActionData.DURATION: duration})
    dur_str = seconds_to_human(duration)
    await msg.answer(
        f"⏱️ Длительность: <b>{dur_str}</b>\nВведите причину бана:",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(),
    )
    await state.set_state(BanState.waiting_reason)


@router.message(BanState.waiting_reason, AdminFilter())
async def ban_receive_reason(msg: Message, state: FSMContext):
    reason = msg.text.strip()
    data = await state.get_data()
    uid = data[ModActionData.DISCORD_USER_ID]
    duration = data.get(ModActionData.DURATION)
    dur_str = seconds_to_human(duration)

    await state.update_data(**{ModActionData.REASON: reason})
    await msg.answer(
        f"🔨 <b>Подтверждение бана</b>\n\n"
        f"👤 Discord ID: <code>{uid}</code>\n"
        f"⏱️ Длительность: <b>{dur_str}</b>\n"
        f"📋 Причина: {reason}\n\n"
        f"Подтвердить?",
        parse_mode="HTML",
        reply_markup=confirm_keyboard("ban"),
    )
    await state.set_state(BanState.confirm)


@router.callback_query(F.data == "confirm:ban", BanState.confirm, AdminFilter())
async def ban_confirm(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    await call.answer()

    uid = data[ModActionData.DISCORD_USER_ID]
    duration = data.get(ModActionData.DURATION)
    reason = data[ModActionData.REASON]
    ticket_id = data.get(ModActionData.TICKET_ID)
    mod_id, mod_username = _get_moderator_info(call.from_user)

    await call.message.edit_text("⏳ Выполняю бан...", parse_mode="HTML")
    result = await _execute_moderation("ban", uid, reason, duration, mod_id, mod_username, ticket_id)
    await call.message.edit_text(result.message, parse_mode="HTML")


# ════════════════════════════════════════════════════════════════
#  /unban
# ════════════════════════════════════════════════════════════════

@router.message(Command("unban"), AdminFilter())
async def cmd_unban_start(msg: Message, state: FSMContext):
    args = msg.text.split(maxsplit=1)
    if len(args) >= 2:
        try:
            uid = int(args[1])
            await _do_unban(msg, uid, state)
            return
        except ValueError:
            pass

    await msg.answer(
        "🔓 <b>Разбан пользователя</b>\nВведите Discord ID пользователя:",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(),
    )
    await state.set_state(UnbanState.waiting_user_id)


@router.message(UnbanState.waiting_user_id, AdminFilter())
async def unban_receive_user_id(msg: Message, state: FSMContext):
    try:
        uid = int(msg.text.strip())
    except ValueError:
        await msg.answer("❌ Некорректный Discord ID:", reply_markup=cancel_keyboard())
        return
    await _do_unban(msg, uid, state)


async def _do_unban(msg: Message, uid: int, state: FSMContext):
    await state.clear()
    mod_id, mod_username = _get_moderator_info(msg.from_user)
    await msg.answer("⏳ Выполняю разбан...")
    result = await _execute_moderation("unban", uid, None, None, mod_id, mod_username)
    await msg.answer(result.message, parse_mode="HTML")


# ════════════════════════════════════════════════════════════════
#  /mute
# ════════════════════════════════════════════════════════════════

@router.message(Command("mute"), AdminFilter())
async def cmd_mute_start(msg: Message, state: FSMContext):
    args = msg.text.split(maxsplit=2)
    if len(args) >= 2:
        try:
            uid = int(args[1])
            await state.update_data(**{ModActionData.DISCORD_USER_ID: uid, ModActionData.TICKET_ID: None})
            await msg.answer(
                f"🔇 Мут для <code>{uid}</code>\n"
                "Укажите длительность (например: <code>30m</code>, <code>2h</code>, <code>7d</code>):",
                parse_mode="HTML",
                reply_markup=cancel_keyboard(),
            )
            await state.set_state(MuteState.waiting_duration)
            return
        except ValueError:
            pass

    await msg.answer(
        "🔇 <b>Мут пользователя</b>\nВведите Discord ID пользователя:",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(),
    )
    await state.set_state(MuteState.waiting_user_id)


@router.message(MuteState.waiting_user_id, AdminFilter())
async def mute_receive_user_id(msg: Message, state: FSMContext):
    try:
        uid = int(msg.text.strip())
    except ValueError:
        await msg.answer("❌ Некорректный Discord ID:", reply_markup=cancel_keyboard())
        return
    await state.update_data(**{ModActionData.DISCORD_USER_ID: uid, ModActionData.TICKET_ID: None})
    await msg.answer(
        "Укажите длительность (например: <code>30m</code>, <code>2h</code>):",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(),
    )
    await state.set_state(MuteState.waiting_duration)


@router.message(MuteState.waiting_duration, AdminFilter())
async def mute_receive_duration(msg: Message, state: FSMContext):
    duration = parse_duration(msg.text.strip())
    if duration is None:
        await msg.answer(
            "❌ Для мута нужна конечная длительность (perm недопустим).\n"
            "Введите снова (например: <code>1h</code>):",
            parse_mode="HTML",
            reply_markup=cancel_keyboard(),
        )
        return
    await state.update_data(**{ModActionData.DURATION: duration})
    await msg.answer(
        f"⏱️ Длительность: <b>{seconds_to_human(duration)}</b>\nВведите причину мута:",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(),
    )
    await state.set_state(MuteState.waiting_reason)


@router.message(MuteState.waiting_reason, AdminFilter())
async def mute_receive_reason(msg: Message, state: FSMContext):
    reason = msg.text.strip()
    data = await state.get_data()
    uid = data[ModActionData.DISCORD_USER_ID]
    duration = data[ModActionData.DURATION]

    await state.update_data(**{ModActionData.REASON: reason})
    await msg.answer(
        f"🔇 <b>Подтверждение мута</b>\n\n"
        f"👤 Discord ID: <code>{uid}</code>\n"
        f"⏱️ Длительность: <b>{seconds_to_human(duration)}</b>\n"
        f"📋 Причина: {reason}",
        parse_mode="HTML",
        reply_markup=confirm_keyboard("mute"),
    )
    await state.set_state(MuteState.confirm)


@router.callback_query(F.data == "confirm:mute", MuteState.confirm, AdminFilter())
async def mute_confirm(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    await call.answer()

    uid = data[ModActionData.DISCORD_USER_ID]
    duration = data[ModActionData.DURATION]
    reason = data[ModActionData.REASON]
    ticket_id = data.get(ModActionData.TICKET_ID)
    mod_id, mod_username = _get_moderator_info(call.from_user)

    await call.message.edit_text("⏳ Выполняю мут...", parse_mode="HTML")
    result = await _execute_moderation("mute", uid, reason, duration, mod_id, mod_username, ticket_id)
    await call.message.edit_text(result.message, parse_mode="HTML")


# ════════════════════════════════════════════════════════════════
#  /unmute
# ════════════════════════════════════════════════════════════════

@router.message(Command("unmute"), AdminFilter())
async def cmd_unmute_start(msg: Message, state: FSMContext):
    args = msg.text.split(maxsplit=1)
    if len(args) >= 2:
        try:
            uid = int(args[1])
            await _do_unmute(msg, uid, state)
            return
        except ValueError:
            pass

    await msg.answer(
        "🔊 <b>Размут пользователя</b>\nВведите Discord ID пользователя:",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(),
    )
    await state.set_state(UnmuteState.waiting_user_id)


@router.message(UnmuteState.waiting_user_id, AdminFilter())
async def unmute_receive_user_id(msg: Message, state: FSMContext):
    try:
        uid = int(msg.text.strip())
    except ValueError:
        await msg.answer("❌ Некорректный Discord ID:", reply_markup=cancel_keyboard())
        return
    await _do_unmute(msg, uid, state)


async def _do_unmute(msg: Message, uid: int, state: FSMContext):
    await state.clear()
    mod_id, mod_username = _get_moderator_info(msg.from_user)
    await msg.answer("⏳ Выполняю размут...")
    result = await _execute_moderation("unmute", uid, None, None, mod_id, mod_username)
    await msg.answer(result.message, parse_mode="HTML")


# ════════════════════════════════════════════════════════════════
#  /warn
# ════════════════════════════════════════════════════════════════

@router.message(Command("warn"), AdminFilter())
async def cmd_warn_start(msg: Message, state: FSMContext):
    args = msg.text.split(maxsplit=1)
    if len(args) >= 2:
        try:
            uid = int(args[1])
            await state.update_data(**{ModActionData.DISCORD_USER_ID: uid, ModActionData.TICKET_ID: None})
            await msg.answer(
                f"⚠️ Предупреждение для <code>{uid}</code>\nВведите причину:",
                parse_mode="HTML",
                reply_markup=cancel_keyboard(),
            )
            await state.set_state(WarnState.waiting_reason)
            return
        except ValueError:
            pass

    await msg.answer(
        "⚠️ <b>Предупреждение</b>\nВведите Discord ID пользователя:",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(),
    )
    await state.set_state(WarnState.waiting_user_id)


@router.message(WarnState.waiting_user_id, AdminFilter())
async def warn_receive_user_id(msg: Message, state: FSMContext):
    try:
        uid = int(msg.text.strip())
    except ValueError:
        await msg.answer("❌ Некорректный Discord ID:", reply_markup=cancel_keyboard())
        return
    await state.update_data(**{ModActionData.DISCORD_USER_ID: uid, ModActionData.TICKET_ID: None})
    await msg.answer(
        "Введите причину предупреждения:",
        reply_markup=cancel_keyboard(),
    )
    await state.set_state(WarnState.waiting_reason)


@router.message(WarnState.waiting_reason, AdminFilter())
async def warn_receive_reason(msg: Message, state: FSMContext):
    reason = msg.text.strip()
    data = await state.get_data()
    uid = data[ModActionData.DISCORD_USER_ID]

    await state.update_data(**{ModActionData.REASON: reason})
    await msg.answer(
        f"⚠️ <b>Подтверждение предупреждения</b>\n\n"
        f"👤 Discord ID: <code>{uid}</code>\n"
        f"📋 Причина: {reason}",
        parse_mode="HTML",
        reply_markup=confirm_keyboard("warn"),
    )
    await state.set_state(WarnState.confirm)


@router.callback_query(F.data == "confirm:warn", WarnState.confirm, AdminFilter())
async def warn_confirm(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    await call.answer()

    uid = data[ModActionData.DISCORD_USER_ID]
    reason = data[ModActionData.REASON]
    ticket_id = data.get(ModActionData.TICKET_ID)
    mod_id, mod_username = _get_moderator_info(call.from_user)

    await call.message.edit_text("⏳ Выдаю предупреждение...", parse_mode="HTML")
    result = await _execute_moderation("warn", uid, reason, None, mod_id, mod_username, ticket_id)
    await call.message.edit_text(result.message, parse_mode="HTML")


# ════════════════════════════════════════════════════════════════
#  /history
# ════════════════════════════════════════════════════════════════

@router.message(Command("history"), AdminFilter())
async def cmd_history(msg: Message, state: FSMContext):
    args = msg.text.split(maxsplit=1)
    if len(args) >= 2:
        try:
            uid = int(args[1])
            await _send_history(msg, uid)
            return
        except ValueError:
            pass

    await msg.answer(
        "📜 <b>История модерации</b>\nВведите Discord ID пользователя:",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(),
    )
    await state.set_state(HistoryState.waiting_user_id)


@router.message(HistoryState.waiting_user_id, AdminFilter())
async def history_receive_user_id(msg: Message, state: FSMContext):
    await state.clear()
    try:
        uid = int(msg.text.strip())
    except ValueError:
        await msg.answer("❌ Некорректный Discord ID.")
        return
    await _send_history(msg, uid)


async def _send_history(msg: Message, uid: int):
    from src.services.moderation import moderation_service
    text = await moderation_service.get_history(uid)
    await msg.answer(text, parse_mode="HTML")


# ════════════════════════════════════════════════════════════════
#  Inline callback — кнопки из тикетов (mod:action:user_id:ticket_msg_id)
# ════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("mod:"), AdminFilter())
async def ticket_mod_callback(call: CallbackQuery, state: FSMContext):
    """Обрабатывает нажатия кнопок в тикетах."""
    parts = call.data.split(":")
    if len(parts) < 3:
        await call.answer("❌ Ошибка данных кнопки")
        return

    action = parts[1]
    try:
        discord_user_id = int(parts[2])
    except (ValueError, IndexError):
        await call.answer("❌ Ошибка: некорректный ID")
        return

    ticket_msg_id = parts[3] if len(parts) > 3 else None

    await call.answer()

    if action == "history":
        from src.services.moderation import moderation_service
        text = await moderation_service.get_history(discord_user_id)
        await call.message.answer(text, parse_mode="HTML")
        return

    if action == "close":
        await _close_ticket(call, ticket_msg_id)
        return

    # Запускаем FSM для модерационных действий
    await state.update_data(**{
        ModActionData.DISCORD_USER_ID: discord_user_id,
        ModActionData.TICKET_ID: ticket_msg_id,
    })

    if action == "ban":
        await call.message.answer(
            f"🔨 Бан для <code>{discord_user_id}</code>\n"
            "Укажите длительность (<code>1h</code>, <code>7d</code>, <code>perm</code>):",
            parse_mode="HTML",
            reply_markup=cancel_keyboard(),
        )
        await state.set_state(BanState.waiting_duration)

    elif action == "mute":
        await call.message.answer(
            f"🔇 Мут для <code>{discord_user_id}</code>\n"
            "Укажите длительность (<code>30m</code>, <code>2h</code>):",
            parse_mode="HTML",
            reply_markup=cancel_keyboard(),
        )
        await state.set_state(MuteState.waiting_duration)

    elif action == "warn":
        await call.message.answer(
            f"⚠️ Предупреждение для <code>{discord_user_id}</code>\nВведите причину:",
            parse_mode="HTML",
            reply_markup=cancel_keyboard(),
        )
        await state.set_state(WarnState.waiting_reason)


async def _close_ticket(call: CallbackQuery, ticket_msg_id: Optional[str]):
    """Закрывает тикет в БД и обновляет сообщение в Telegram."""
    from sqlalchemy import update
    from src.database.models import Ticket
    from src.database.session import get_session
    from src.services.utils import utcnow

    if ticket_msg_id:
        async with get_session() as session:
            await session.execute(
                update(Ticket)
                .where(Ticket.discord_message_id == str(ticket_msg_id))
                .values(
                    status="closed",
                    closed_at=utcnow(),
                    closed_by=call.from_user.id,
                )
            )

    # Обновляем текст сообщения
    original_text = call.message.text or call.message.caption or ""
    closed_text = original_text + f"\n\n✅ <b>Тикет закрыт</b> администратором @{call.from_user.username}"

    try:
        await call.message.edit_text(
            closed_text[:4096],
            parse_mode="HTML",
            reply_markup=None,
        )
    except Exception:
        await call.message.answer(f"✅ Тикет закрыт.")


# ════════════════════════════════════════════════════════════════
#  Direct callbacks (direct:action:uid)
# ════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("direct:"), AdminFilter())
async def direct_mod_callback(call: CallbackQuery, state: FSMContext):
    """Обрабатывает кнопки прямого меню модерации."""
    parts = call.data.split(":")
    action = parts[1]
    try:
        uid = int(parts[2])
    except (ValueError, IndexError):
        await call.answer("❌ Ошибка данных")
        return

    await call.answer()
    await state.update_data(**{ModActionData.DISCORD_USER_ID: uid, ModActionData.TICKET_ID: None})

    if action == "history":
        from src.services.moderation import moderation_service
        text = await moderation_service.get_history(uid)
        await call.message.answer(text, parse_mode="HTML")

    elif action == "ban":
        await call.message.answer(
            f"🔨 Бан для <code>{uid}</code>\nДлительность:",
            parse_mode="HTML", reply_markup=cancel_keyboard(),
        )
        await state.set_state(BanState.waiting_duration)

    elif action == "mute":
        await call.message.answer(
            f"🔇 Мут для <code>{uid}</code>\nДлительность:",
            parse_mode="HTML", reply_markup=cancel_keyboard(),
        )
        await state.set_state(MuteState.waiting_duration)

    elif action == "warn":
        await call.message.answer(
            f"⚠️ Варн для <code>{uid}</code>\nПричина:",
            parse_mode="HTML", reply_markup=cancel_keyboard(),
        )
        await state.set_state(WarnState.waiting_reason)

    elif action == "unban":
        await call.message.edit_text("⏳ Выполняю разбан...")
        mod_id, mod_username = _get_moderator_info(call.from_user)
        result = await _execute_moderation("unban", uid, None, None, mod_id, mod_username)
        await call.message.edit_text(result.message, parse_mode="HTML")

    elif action == "unmute":
        await call.message.edit_text("⏳ Выполняю размут...")
        mod_id, mod_username = _get_moderator_info(call.from_user)
        result = await _execute_moderation("unmute", uid, None, None, mod_id, mod_username)
        await call.message.edit_text(result.message, parse_mode="HTML")


# ════════════════════════════════════════════════════════════════
#  Универсальная отмена
# ════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "cancel")
async def cancel_action(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.answer("Отменено")
    try:
        await call.message.edit_text("❌ Действие отменено.")
    except Exception:
        pass