"""OCR 引擎抽象定义。"""

from __future__ import annotations

from typing import Protocol

import numpy as np

from app.schemas.common import BBox, TextBlock


class OcrEngine(Protocol):
    """OCR 引擎统一接口。"""

    def recognize(self, image: np.ndarray) -> list[TextBlock]:
        """识别整页图像并返回文本块列表。"""


def textblock_from_quad(text: str, quad: list[list[float]], score: float) -> TextBlock:
    """把四点框转换成轴对齐文本块。"""
    if len(quad) != 4:
        raise ValueError("quad 必须包含 4 个顶点。")

    xs = [point[0] for point in quad]
    ys = [point[1] for point in quad]
    return TextBlock(
        text=text,
        bbox=BBox(x1=min(xs), y1=min(ys), x2=max(xs), y2=max(ys)),
        confidence=float(score),
    )
