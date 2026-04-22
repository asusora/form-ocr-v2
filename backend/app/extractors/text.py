"""文本字段抽取器。"""

from __future__ import annotations

from typing import Iterable

import numpy as np

from app.extractors.base import ExtractContext, blocks_in_bbox, crop_image
from app.extractors.registry import register
from app.ocr import get_engine as get_ocr_engine
from app.schemas.common import BBox, ExtractResult, TextBlock


def _sort_blocks(blocks: Iterable[TextBlock]) -> list[TextBlock]:
    """按阅读顺序排序文本块。"""
    return sorted(blocks, key=lambda block: (((block.bbox.y1 + block.bbox.y2) / 2), block.bbox.x1))


def _group_lines(blocks: list[TextBlock]) -> list[list[TextBlock]]:
    """按 y 坐标把文本块聚成多行。"""
    if not blocks:
        return []

    sorted_blocks = _sort_blocks(blocks)
    average_height = sum(block.bbox.height() for block in sorted_blocks) / len(sorted_blocks)
    threshold = max(6.0, average_height * 0.6)

    groups: list[list[TextBlock]] = [[sorted_blocks[0]]]
    for block in sorted_blocks[1:]:
        current_center_y = (block.bbox.y1 + block.bbox.y2) / 2
        last_center_y = (
            groups[-1][-1].bbox.y1 + groups[-1][-1].bbox.y2
        ) / 2
        if abs(current_center_y - last_center_y) <= threshold:
            groups[-1].append(block)
            continue
        groups.append([block])

    for group in groups:
        group.sort(key=lambda item: item.bbox.x1)
    return groups


def _join_lines(line_groups: list[list[TextBlock]], preserve_lines: bool) -> str:
    """把文本块行组合成字符串。"""
    lines = [" ".join(block.text.strip() for block in group if block.text.strip()) for group in line_groups]
    lines = [line.strip() for line in lines if line.strip()]
    if not lines:
        return ""
    return "\n".join(lines) if preserve_lines else " ".join(lines)


def _average_confidence(blocks: list[TextBlock]) -> float | None:
    """计算文本块平均置信度。"""
    if not blocks:
        return None
    return float(sum(block.confidence for block in blocks) / len(blocks))


def extract_text_value(
    bbox: BBox,
    context: ExtractContext,
    preserve_lines: bool = False,
) -> tuple[str, float | None]:
    """从 OCR 文本块中提取文本，必要时回退到局部 OCR。"""
    in_scope_blocks = blocks_in_bbox(context.page_blocks, bbox)
    if in_scope_blocks:
        line_groups = _group_lines(in_scope_blocks)
        return _join_lines(line_groups, preserve_lines), _average_confidence(in_scope_blocks)

    local_image = crop_image(context.page_image, bbox)
    if local_image.size == 0:
        return "", None

    try:
        local_blocks = get_ocr_engine().recognize(local_image)
    except Exception:
        return "", None

    line_groups = _group_lines(local_blocks)
    return _join_lines(line_groups, preserve_lines), _average_confidence(local_blocks)


class TextExtractor:
    """普通文本字段抽取器。"""

    field_type = "text"

    def extract(self, image: np.ndarray, bbox: BBox, context: ExtractContext) -> ExtractResult:
        """抽取单行文本字段。"""
        value, confidence = extract_text_value(bbox, context, preserve_lines=False)
        return ExtractResult(raw_value=value or None, confidence=confidence)


register(TextExtractor())
