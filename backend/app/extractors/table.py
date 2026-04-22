"""表格字段抽取器。"""

from __future__ import annotations

from typing import Any

import cv2
import numpy as np

from app.extractors.base import ExtractContext, blocks_in_bbox
from app.extractors.registry import get_extractor, register
from app.schemas.common import BBox, ExtractResult, TextBlock


def _cluster_rows_by_text(blocks: list[TextBlock], bbox: BBox) -> list[tuple[float, float]]:
    """按 OCR 文本行聚类推断表格行范围。"""
    in_scope = blocks_in_bbox(blocks, bbox)
    if not in_scope:
        return []

    ordered = sorted(in_scope, key=lambda block: ((block.bbox.y1 + block.bbox.y2) / 2, block.bbox.x1))
    average_height = sum(block.bbox.height() for block in ordered) / len(ordered)
    threshold = max(6.0, average_height * 0.8)

    rows: list[list[TextBlock]] = [[ordered[0]]]
    for block in ordered[1:]:
        current_center = (block.bbox.y1 + block.bbox.y2) / 2
        previous_center = (rows[-1][-1].bbox.y1 + rows[-1][-1].bbox.y2) / 2
        if abs(current_center - previous_center) <= threshold:
            rows[-1].append(block)
            continue
        rows.append([block])

    return [
        (float(min(block.bbox.y1 for block in row)), float(max(block.bbox.y2 for block in row)))
        for row in rows
    ]


def _detect_rows_by_lines(image: np.ndarray, bbox: BBox) -> list[tuple[float, float]]:
    """按水平线检测推断表格行范围。"""
    x1 = max(int(round(bbox.x1)), 0)
    y1 = max(int(round(bbox.y1)), 0)
    x2 = max(int(round(bbox.x2)), x1 + 1)
    y2 = max(int(round(bbox.y2)), y1 + 1)
    crop = image[y1:y2, x1:x2]
    if crop.size == 0:
        return []

    gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    lines = cv2.HoughLinesP(
        edges,
        1,
        np.pi / 180,
        threshold=60,
        minLineLength=max(20, int(crop.shape[1] * 0.6)),
        maxLineGap=10,
    )
    if lines is None:
        return []

    positions = sorted(
        {
            int(round((line[0][1] + line[0][3]) / 2))
            for line in lines
            if abs(int(line[0][3]) - int(line[0][1])) <= 2
        }
    )
    if len(positions) < 2:
        return []

    rows: list[tuple[float, float]] = []
    for top, bottom in zip(positions, positions[1:]):
        if bottom - top <= 5:
            continue
        rows.append((float(top + y1), float(bottom + y1)))
    return rows


def _split_fixed_count(bbox: BBox, count: int) -> list[tuple[float, float]]:
    """按固定行数均分表格区域。"""
    row_height = bbox.height() / max(count, 1)
    return [
        (bbox.y1 + row_index * row_height, bbox.y1 + (row_index + 1) * row_height)
        for row_index in range(count)
    ]


def _normalize_columns(config: dict[str, Any]) -> list[dict[str, Any]]:
    """把列定义统一转成字典。"""
    normalized: list[dict[str, Any]] = []
    for column in config.get("columns") or []:
        if hasattr(column, "model_dump"):
            normalized.append(column.model_dump())
            continue
        if isinstance(column, dict):
            normalized.append(column)
    return normalized


def _row_has_content(row: dict[str, Any]) -> bool:
    """判断表格行是否包含至少一个有效值。"""
    for value in row.values():
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        if isinstance(value, list) and not value:
            continue
        return True
    return False


class TableExtractor:
    """表格字段抽取器。"""

    field_type = "table"

    def extract(self, image: np.ndarray, bbox: BBox, context: ExtractContext) -> ExtractResult:
        """按行列切分并递归复用子字段抽取器。"""
        config = context.field_config
        columns = _normalize_columns(config)
        if not columns:
            return ExtractResult(raw_value=[], confidence=None)

        row_config = config.get("row_detection") or {"mode": "by_text_rows"}
        if hasattr(row_config, "model_dump"):
            row_config = row_config.model_dump()

        mode = str(row_config.get("mode", "by_text_rows"))
        source_image = context.page_image if context.page_image is not None else image
        if mode == "by_horizontal_lines":
            row_bounds = _detect_rows_by_lines(source_image, bbox)
            if not row_bounds:
                row_bounds = _cluster_rows_by_text(context.page_blocks, bbox)
        elif mode == "fixed_count":
            row_bounds = _split_fixed_count(bbox, int(row_config.get("count") or 1))
        else:
            row_bounds = _cluster_rows_by_text(context.page_blocks, bbox)

        if not row_bounds:
            return ExtractResult(raw_value=[], confidence=None)

        table_rows: list[dict[str, Any]] = []
        for row_top, row_bottom in row_bounds:
            row_data: dict[str, Any] = {}
            for column in columns:
                start_ratio, end_ratio = column["x_ratio"]
                cell_bbox = BBox(
                    x1=bbox.x1 + bbox.width() * float(start_ratio),
                    y1=row_top,
                    x2=bbox.x1 + bbox.width() * float(end_ratio),
                    y2=row_bottom,
                )
                extractor = get_extractor(str(column["type"]))
                sub_result = extractor.extract(
                    source_image,
                    cell_bbox,
                    ExtractContext(
                        page_blocks=context.page_blocks,
                        page_image=source_image,
                        field_config={},
                    ),
                )
                row_data[str(column["name"])] = sub_result.raw_value
            if _row_has_content(row_data):
                table_rows.append(row_data)

        return ExtractResult(raw_value=table_rows, confidence=None)


register(TableExtractor())
