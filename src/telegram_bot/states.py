"""
FSM States для Telegram-бота
"""
from aiogram.fsm.state import State, StatesGroup


class BanState(StatesGroup):
    waiting_user_id = State()
    waiting_duration = State()
    waiting_reason = State()
    confirm = State()


class MuteState(StatesGroup):
    waiting_user_id = State()
    waiting_duration = State()
    waiting_reason = State()
    confirm = State()


class WarnState(StatesGroup):
    waiting_user_id = State()
    waiting_reason = State()
    confirm = State()


class UnbanState(StatesGroup):
    waiting_user_id = State()
    confirm = State()


class UnmuteState(StatesGroup):
    waiting_user_id = State()
    confirm = State()


class HistoryState(StatesGroup):
    waiting_user_id = State()


class AddAdminState(StatesGroup):
    waiting_telegram_id = State()


# Данные, хранящиеся в FSM storage во время диалога
class ModActionData:
    """Ключи для FSM data."""
    DISCORD_USER_ID = "discord_user_id"
    DURATION = "duration_seconds"
    REASON = "reason"
    TICKET_ID = "ticket_id"
    DISCORD_USERNAME = "discord_username"