"""勾选框字段抽取器。"""

from __future__ import annotations

import cv2
import numpy as np

from app.extractors.base import ExtractContext, crop_image
from app.extractors.registry import register
from app.schemas.common import BBox, ExtractResult


class CheckboxExtractor:
    """基于前景像素密度的勾选框抽取器。"""

    field_type = "checkbox"

    def extract(self, image: np.ndarray, bbox: BBox, context: ExtractContext) -> ExtractResult:
        """判断勾选框是否被填写。"""
        crop = crop_image(context.page_image if context.page_image is not None else image, bbox)
        if crop.size == 0:
            return ExtractResult(raw_value=False, confidence=0.0)

        gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        _threshold, binary = cv2.threshold(
            blurred,
            0,
            255,
            cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU,
        )
        fill_ratio = float(np.count_nonzero(binary) / binary.size)
        checked = fill_ratio >= 0.02
        confidence = min(1.0, fill_ratio * 12.0) if checked else max(0.0, 1.0 - fill_ratio * 8.0)
        return ExtractResult(raw_value=checked, confidence=confidence)


register(CheckboxExtractor())
