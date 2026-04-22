"""字段抽取器基础定义。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

import numpy as np

from app.schemas.common import BBox, ExtractResult, TextBlock


@dataclass(slots=True)
class ExtractContext:
    """字段抽取上下文。"""

    page_blocks: list[TextBlock] = field(default_factory=list)
    page_image: np.ndarray | None = None
    field_config: dict[str, Any] = field(default_factory=dict)


class FieldExtractor(Protocol):
    """字段抽取器协议。"""

    field_type: str

    def extract(self, image: np.ndarray, bbox: BBox, context: ExtractContext) -> ExtractResult:
        """基于页面图像、字段坐标和上下文抽取字段值。"""


def crop_image(image: np.ndarray | None, bbox: BBox) -> np.ndarray:
    """从整页图像中裁剪字段区域。"""
    if image is None or image.size == 0:
        return np.zeros((0, 0, 3), dtype=np.uint8)

    height, width = image.shape[:2]
    x1 = max(int(round(bbox.x1)), 0)
    y1 = max(int(round(bbox.y1)), 0)
    x2 = min(int(round(bbox.x2)), width)
    y2 = min(int(round(bbox.y2)), height)
    if x2 <= x1 or y2 <= y1:
        return np.zeros((0, 0, 3), dtype=np.uint8)
    return image[y1:y2, x1:x2].copy()


def block_overlaps_bbox(block: TextBlock, bbox: BBox) -> bool:
    """判断 OCR 文本块是否与字段框有交集。"""
    inter_x1 = max(block.bbox.x1, bbox.x1)
    inter_y1 = max(block.bbox.y1, bbox.y1)
    inter_x2 = min(block.bbox.x2, bbox.x2)
    inter_y2 = min(block.bbox.y2, bbox.y2)
    if inter_x2 <= inter_x1 or inter_y2 <= inter_y1:
        return False

    return True


def blocks_in_bbox(blocks: list[TextBlock], bbox: BBox) -> list[TextBlock]:
    """返回与字段框重叠的 OCR 文本块。"""
    return [block for block in blocks if block_overlaps_bbox(block, bbox)]
