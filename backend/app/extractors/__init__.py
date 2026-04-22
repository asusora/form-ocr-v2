"""字段抽取器导出。"""

from app.extractors.registry import get_extractor, list_extractors, register

from . import checkbox, date, multiline_text, option_select, signature, table, text  # noqa: F401

__all__ = ["get_extractor", "list_extractors", "register"]
