"""
Inline keyboards для Telegram-бота
"""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def confirm_keyboard(action: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm:{action}"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"),
        ]
    ])


def moderation_menu_keyboard(discord_user_id: int) -> InlineKeyboardMarkup:
    """Клавиатура меню модерации для конкретного пользователя."""
    uid = discord_user_id
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⚠️ Варн", callback_data=f"direct:warn:{uid}"),
            InlineKeyboardButton(text="🔇 Мут", callback_data=f"direct:mute:{uid}"),
            InlineKeyboardButton(text="🔨 Бан", callback_data=f"direct:ban:{uid}"),
        ],
        [
            InlineKeyboardButton(text="🔊 Размут", callback_data=f"direct:unmute:{uid}"),
            InlineKeyboardButton(text="🔓 Разбан", callback_data=f"direct:unban:{uid}"),
            InlineKeyboardButton(text="📜 История", callback_data=f"direct:history:{uid}"),
        ],
    ])


def cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
    ])