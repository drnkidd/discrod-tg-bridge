"""
Фильтры для Telegram-бота:
- AdminFilter: проверяет, является ли пользователь администратором
"""
from __future__ import annotations

import logging

from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select

from src.config import get_settings
from src.database.models import AdminUser
from src.database.session import get_session

log = logging.getLogger(__name__)
settings = get_settings()


class AdminFilter(BaseFilter):
    """Пропускает только владельца и зарегистрированных администраторов."""

    async def __call__(self, event: Message | CallbackQuery) -> bool:
        user = event.from_user
        if not user:
            return False

        # Владелец всегда имеет доступ
        if user.id == settings.telegram_owner_id:
            return True

        # Проверяем в БД
        try:
            async with get_session() as session:
                result = await session.execute(
                    select(AdminUser).where(
                        AdminUser.telegram_id == user.id,
                        AdminUser.is_active == True,
                    )
                )
                admin = result.scalar_one_or_none()
                return admin is not None
        except Exception as e:
            log.error(f"AdminFilter DB error: {e}")
            return False


class OwnerFilter(BaseFilter):
    """Пропускает только владельца бота."""

    async def __call__(self, event: Message | CallbackQuery) -> bool:
        user = event.from_user
        return user is not None and user.id == settings.telegram_owner_id