"""签名字段抽取器。"""

from __future__ import annotations

import numpy as np

from app.extractors.base import ExtractContext
from app.extractors.registry import register
from app.schemas.common import BBox, ExtractResult


class SignatureExtractor:
    """签名字段仅保留切图，不做值识别。"""

    field_type = "signature"

    def extract(self, image: np.ndarray, bbox: BBox, context: ExtractContext) -> ExtractResult:
        """返回空值，具体预览由切图接口承担。"""
        return ExtractResult(raw_value=None, confidence=None)


register(SignatureExtractor())
