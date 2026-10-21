"""Lịch Việt Nam cho đặc trưng Forecast: giờ địa phương và ngày nghỉ lễ.

Việt Nam không có giờ mùa hè nên dùng lệch cố định UTC+7, không cần tzdata.
Ngày lễ âm lịch (Tết, Giỗ Tổ) chỉ có cho các năm đã tra; năm ngoài bảng trả
``None`` = "không biết", để model coi là thiếu thay vì học nhầm "không phải lễ".
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

VN_UTC_OFFSET_HOURS = 7

# Mùng 1 Tết Nguyên đán và 10/3 âm lịch (Giỗ Tổ Hùng Vương) theo dương lịch.
_TET_DAY_ONE = {
    2024: date(2024, 2, 10),
    2025: date(2025, 1, 29),
    2026: date(2026, 2, 17),
}
_HUNG_KINGS = {
    2024: date(2024, 4, 18),
    2025: date(2025, 4, 7),
    2026: date(2026, 4, 26),
}
_FIXED_SOLAR = ((1, 1), (4, 30), (5, 1), (9, 2))
# Kỳ nghỉ Tết thực tế kéo từ trước giao thừa tới khoảng mùng 5.
_TET_DAYS_BEFORE = 1
_TET_DAYS_AFTER = 4


def to_local(timestamp: int, utc_offset_hours: float = VN_UTC_OFFSET_HOURS) -> datetime:
    return datetime.fromtimestamp(
        timestamp, tz=timezone(timedelta(hours=utc_offset_hours))
    )


def is_vn_public_holiday(day: date) -> bool | None:
    """``True``/``False`` khi năm có trong bảng âm lịch, ``None`` khi chưa tra."""
    tet = _TET_DAY_ONE.get(day.year)
    hung_kings = _HUNG_KINGS.get(day.year)
    if tet is None or hung_kings is None:
        return None
    if (day.month, day.day) in _FIXED_SOLAR or day == hung_kings:
        return True
    return tet - timedelta(days=_TET_DAYS_BEFORE) <= day <= tet + timedelta(
        days=_TET_DAYS_AFTER
    )
