"""多行文本字段抽取器。"""

from __future__ import annotations

import numpy as np

from app.extractors.base import ExtractContext
from app.extractors.registry import register
from app.extractors.text import extract_text_value
from app.schemas.common import BBox, ExtractResult


class MultilineTextExtractor:
    """多行文本字段抽取器。"""

    field_type = "multiline_text"

    def extract(self, image: np.ndarray, bbox: BBox, context: ExtractContext) -> ExtractResult:
        """按行保留换行符抽取文本。"""
        value, confidence = extract_text_value(bbox, context, preserve_lines=True)
        return ExtractResult(raw_value=value or None, confidence=confidence)


register(MultilineTextExtractor())
