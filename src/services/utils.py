"""
Утилиты для парсинга времени и форматирования длительностей
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Optional


_UNITS = {
    "s": 1,
    "sec": 1,
    "м": 60,
    "m": 60,
    "min": 60,
    "ч": 3600,
    "h": 3600,
    "hr": 3600,
    "д": 86400,
    "d": 86400,
    "day": 86400,
    "нед": 604800,
    "w": 604800,
    "week": 604800,
}


def parse_duration(text: str) -> Optional[int]:
    """
    Парсит строку вида '10m', '2h', '7d', '1w', 'perm', 'навсегда'
    Возвращает количество секунд или None для постоянного бана.
    """
    text = text.strip().lower()
    if text in ("perm", "permanent", "навсегда", "0", "inf", "∞"):
        return None  # permanent

    pattern = re.compile(r"(\d+)\s*([a-zа-я]+)")
    match = pattern.fullmatch(text)
    if not match:
        return None  # cannot parse → treat as permanent

    amount, unit = int(match.group(1)), match.group(2)
    multiplier = _UNITS.get(unit)
    if multiplier is None:
        return None

    return amount * multiplier


def seconds_to_human(seconds: Optional[int]) -> str:
    """Преобразует секунды в читаемую строку."""
    if seconds is None:
        return "навсегда"

    parts = []
    intervals = [
        (604800, "нед"),
        (86400, "д"),
        (3600, "ч"),
        (60, "мин"),
        (1, "сек"),
    ]
    remaining = seconds
    for unit_seconds, unit_name in intervals:
        value = remaining // unit_seconds
        if value:
            parts.append(f"{value}{unit_name}")
        remaining %= unit_seconds

    return " ".join(parts) or "0сек"


def utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)