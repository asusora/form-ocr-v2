"""日期字段抽取器。"""

from __future__ import annotations

import re
from datetime import date

import numpy as np

from app.extractors.base import ExtractContext
from app.extractors.registry import register
from app.extractors.text import extract_text_value
from app.schemas.common import BBox, ExtractResult

_MONTH_MAP = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}


def _normalize_year(value: int) -> int:
    """把两位年份归一化为四位年份。"""
    if value >= 100:
        return value
    return 2000 + value if value < 50 else 1900 + value


def _format_date(day: int, month: int, year: int) -> str | None:
    """将年月日格式化为 DD/MM/YYYY。"""
    try:
        normalized = date(_normalize_year(year), month, day)
    except ValueError:
        return None
    return normalized.strftime("%d/%m/%Y")


def _parse_date(text: str) -> str | None:
    """从字符串中解析日期。"""
    normalized = text.strip()
    if not normalized:
        return None

    day_first = re.search(r"(?P<day>\d{1,2})[\/\-.](?P<month>\d{1,2})[\/\-.](?P<year>\d{2,4})", normalized)
    if day_first:
        return _format_date(
            int(day_first.group("day")),
            int(day_first.group("month")),
            int(day_first.group("year")),
        )

    year_first = re.search(r"(?P<year>\d{4})[\/\-.](?P<month>\d{1,2})[\/\-.](?P<day>\d{1,2})", normalized)
    if year_first:
        return _format_date(
            int(year_first.group("day")),
            int(year_first.group("month")),
            int(year_first.group("year")),
        )

    english = re.search(
        r"(?P<day>\d{1,2})\s+(?P<month>[A-Za-z]{3,9})\s+(?P<year>\d{2,4})",
        normalized,
    )
    if english:
        month_key = english.group("month").strip().lower()
        month = _MONTH_MAP.get(month_key)
        if month is not None:
            return _format_date(int(english.group("day")), month, int(english.group("year")))

    return None


class DateExtractor:
    """日期字段抽取器。"""

    field_type = "date"

    def extract(self, image: np.ndarray, bbox: BBox, context: ExtractContext) -> ExtractResult:
        """抽取并标准化日期文本。"""
        raw_text, confidence = extract_text_value(bbox, context, preserve_lines=False)
        normalized = _parse_date(raw_text)
        if normalized is not None:
            return ExtractResult(raw_value=normalized, confidence=confidence)
        return ExtractResult(
            raw_value=raw_text or None,
            confidence=(confidence * 0.8) if confidence is not None else None,
        )


register(DateExtractor())
