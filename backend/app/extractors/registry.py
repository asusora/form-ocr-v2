"""字段抽取器注册表。"""

from __future__ import annotations

from app.extractors.base import FieldExtractor

_REGISTRY: dict[str, FieldExtractor] = {}


def register(extractor: FieldExtractor) -> None:
    """注册字段抽取器实例。"""
    _REGISTRY[extractor.field_type] = extractor


def get_extractor(field_type: str) -> FieldExtractor:
    """按字段类型获取抽取器。"""
    try:
        return _REGISTRY[field_type]
    except KeyError as exc:
        raise KeyError(f"未注册的字段类型: {field_type}") from exc


def list_extractors() -> dict[str, FieldExtractor]:
    """返回当前注册的抽取器映射副本。"""
    return dict(_REGISTRY)
