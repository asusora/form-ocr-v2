"""模板业务服务。"""

from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from sqlalchemy.orm import Session

from app.alignment.anchors import extract_anchors_for_field
from app.models.orm import TemplateField
from app.ocr import get_engine as get_ocr_engine
from app.pdf.render import render_page_to_array, render_pdf_to_images
from app.schemas.common import Anchor, BBox, TextBlock
from app.schemas.template import ColumnDef, RowDetectionConfig, TableSegmentationOut, TemplateFieldIn
from app.storage.paths import template_ocr_path, template_page_image_path, template_pdf_path
from app.template.repository import (
    create_template,
    delete_template_field,
    get_template,
    get_template_field,
    replace_fields,
)


def _write_ocr_json(path: Path, blocks: list[TextBlock]) -> None:
    """写入 OCR 缓存文件。"""
    path.write_text(
        json.dumps([block.model_dump() for block in blocks], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _read_ocr_json(path: Path) -> list[TextBlock]:
    """读取 OCR 缓存文件。"""
    data = json.loads(path.read_text(encoding="utf-8"))
    return [TextBlock.model_validate(item) for item in data]


def _ensure_valid_page(page: int, page_count: int) -> None:
    """验证页码位于模板范围内。"""
    if page < 1 or page > page_count:
        raise ValueError(f"字段页码超出模板范围: {page}")


def _resolve_anchors(
    field: TemplateFieldIn,
    page_blocks: list[TextBlock],
    all_field_bboxes: list[BBox],
) -> list[Anchor]:
    """优先使用手工锚点，否则自动提取锚点。"""
    if field.anchors:
        return field.anchors
    return extract_anchors_for_field(
        field_bbox=field.bbox,
        page_blocks=page_blocks,
        all_field_bboxes=all_field_bboxes,
        n=3,
    )


def save_template_from_pdf(
    db: Session,
    name: str,
    description: str | None,
    render_dpi: int,
    pdf_bytes: bytes,
) -> str:
    """保存上传 PDF，渲染页面并缓存 OCR。

    任何一步失败都会清掉 `<data_dir>/templates/<id>/` 下的中间文件，
    避免留下 DB 无记录但磁盘有残留的孤儿目录。
    """
    template_id = str(uuid.uuid4())
    pdf_path = template_pdf_path(template_id)
    try:
        pdf_path.write_bytes(pdf_bytes)

        pages_dir = template_page_image_path(template_id, 1).parent
        page_paths = render_pdf_to_images(pdf_path, pages_dir, dpi=render_dpi)
        ocr_engine = get_ocr_engine()

        for page_index in range(1, len(page_paths) + 1):
            page_array = render_page_to_array(pdf_path, page=page_index, dpi=render_dpi)
            blocks = ocr_engine.recognize(page_array)
            _write_ocr_json(template_ocr_path(template_id, page_index), blocks)

        template = create_template(
            db=db,
            template_id=template_id,
            name=name,
            description=description,
            source_pdf_path=str(pdf_path),
            page_count=len(page_paths),
            render_dpi=render_dpi,
        )
        return template.id
    except Exception:
        shutil.rmtree(pdf_path.parent, ignore_errors=True)
        raise


def save_fields_with_anchors(db: Session, template_id: str, fields_in: list[TemplateFieldIn]) -> None:
    """保存模板字段，并补齐锚点。"""
    template = get_template(db, template_id)
    if template is None:
        raise ValueError(f"模板不存在: {template_id}")

    bboxes_by_page: dict[int, list[BBox]] = {}
    for field in fields_in:
        _ensure_valid_page(field.page, template.page_count)
        bboxes_by_page.setdefault(field.page, []).append(field.bbox)

    ocr_cache: dict[int, list[TextBlock]] = {
        page: _read_ocr_json(template_ocr_path(template_id, page))
        for page in bboxes_by_page
    }

    orm_fields: list[TemplateField] = []
    for field in fields_in:
        anchors = _resolve_anchors(field, ocr_cache[field.page], bboxes_by_page[field.page])
        orm_fields.append(
            TemplateField(
                id=str(field.id) if field.id is not None else str(uuid.uuid4()),
                template_id=template_id,
                page=field.page,
                name=field.name,
                label=field.label,
                field_type=field.field_type,
                bbox=field.bbox.model_dump(),
                anchors=[anchor.model_dump() for anchor in anchors],
                options=[option.model_dump() for option in field.options] if field.options else None,
                columns=[column.model_dump() for column in field.columns] if field.columns else None,
                row_detection=field.row_detection.model_dump() if field.row_detection else None,
                sort_order=field.sort_order,
            )
        )

    replace_fields(db, template_id, orm_fields)


def update_field_with_anchor(
    db: Session,
    template_id: str,
    field_id: str,
    field_in: TemplateFieldIn,
) -> TemplateField | None:
    """更新单个模板字段并重算或覆盖锚点。"""
    template = get_template(db, template_id)
    if template is None:
        return None

    field = get_template_field(db, template_id, field_id)
    if field is None:
        return None

    _ensure_valid_page(field_in.page, template.page_count)

    page_blocks = _read_ocr_json(template_ocr_path(template_id, field_in.page))
    same_page_bboxes = [
        BBox.model_validate(item.bbox)
        for item in template.fields
        if item.id != field_id and item.page == field_in.page
    ]
    same_page_bboxes.append(field_in.bbox)
    anchors = _resolve_anchors(field_in, page_blocks, same_page_bboxes)

    field.page = field_in.page
    field.name = field_in.name
    field.label = field_in.label
    field.field_type = field_in.field_type
    field.bbox = field_in.bbox.model_dump()
    field.anchors = [anchor.model_dump() for anchor in anchors]
    field.options = [option.model_dump() for option in field_in.options] if field_in.options else None
    field.columns = [column.model_dump() for column in field_in.columns] if field_in.columns else None
    field.row_detection = field_in.row_detection.model_dump() if field_in.row_detection else None
    field.sort_order = field_in.sort_order
    db.commit()
    db.refresh(field)
    return field


def delete_field(db: Session, template_id: str, field_id: str) -> bool:
    """删除单个模板字段。"""
    return delete_template_field(db, template_id, field_id)


def _dedupe_positions(values: list[int], minimum_gap: int = 8) -> list[int]:
    """对线段位置做去重和近邻合并。"""
    if not values:
        return []

    merged: list[int] = [values[0]]
    for value in values[1:]:
        if abs(value - merged[-1]) <= minimum_gap:
            merged[-1] = int(round((merged[-1] + value) / 2))
            continue
        merged.append(value)
    return merged


def _detect_line_positions(
    crop: np.ndarray,
    axis: str,
    min_ratio: float,
) -> list[int]:
    """检测表格横线或竖线位置。"""
    gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
    inverted = cv2.bitwise_not(gray)
    binary = cv2.adaptiveThreshold(
        inverted,
        255,
        cv2.ADAPTIVE_THRESH_MEAN_C,
        cv2.THRESH_BINARY,
        15,
        -2,
    )

    if axis == "vertical":
        size = max(10, crop.shape[0] // 4)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, size))
        min_length = int(crop.shape[0] * min_ratio)
    else:
        size = max(10, crop.shape[1] // 4)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (size, 1))
        min_length = int(crop.shape[1] * min_ratio)

    lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    contours, _hierarchy = cv2.findContours(lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    positions: list[int] = []
    for contour in contours:
        x, y, width, height = cv2.boundingRect(contour)
        if axis == "vertical" and height >= min_length:
            positions.append(x + width // 2)
        if axis == "horizontal" and width >= min_length:
            positions.append(y + height // 2)

    return _dedupe_positions(sorted(positions))


def _cluster_column_bounds_by_text(
    blocks: list[TextBlock],
    bbox: BBox,
    desired_columns: int | None,
) -> list[tuple[float, float]]:
    """在没有明显竖线时，根据文本分布推断列边界。"""
    in_scope = [block for block in blocks if block.bbox.x1 < bbox.x2 and block.bbox.x2 > bbox.x1]
    in_scope = [block for block in in_scope if block.bbox.y1 < bbox.y2 and block.bbox.y2 > bbox.y1]
    if not in_scope:
        return [(bbox.x1, bbox.x2)]

    ordered = sorted(in_scope, key=lambda block: block.bbox.x1)
    groups: list[list[TextBlock]] = [[ordered[0]]]
    average_width = sum(block.bbox.width() for block in ordered) / len(ordered)
    threshold = max(12.0, average_width * 0.8)
    for block in ordered[1:]:
        current_left = block.bbox.x1
        previous_right = groups[-1][-1].bbox.x2
        if current_left - previous_right <= threshold:
            groups[-1].append(block)
            continue
        groups.append([block])

    bounds = [
        (float(min(block.bbox.x1 for block in group)), float(max(block.bbox.x2 for block in group)))
        for group in groups
    ]
    if desired_columns and desired_columns > 0 and len(bounds) > desired_columns:
        return bounds[:desired_columns]
    return bounds


def suggest_table_structure(
    template_id: str,
    page: int,
    bbox: BBox,
    desired_columns: int | None = None,
) -> TableSegmentationOut:
    """基于页面图像给出表格列和行检测建议。"""
    image_path = template_page_image_path(template_id, page)
    if not image_path.exists():
        raise FileNotFoundError(f"模板页图不存在: {image_path}")

    page_image = np.asarray(Image.open(image_path).convert("RGB"))
    x1 = max(int(round(bbox.x1)), 0)
    y1 = max(int(round(bbox.y1)), 0)
    x2 = min(int(round(bbox.x2)), page_image.shape[1])
    y2 = min(int(round(bbox.y2)), page_image.shape[0])
    crop = page_image[y1:y2, x1:x2]

    vertical_positions = _detect_line_positions(crop, axis="vertical", min_ratio=0.5) if crop.size else []
    horizontal_positions = _detect_line_positions(crop, axis="horizontal", min_ratio=0.6) if crop.size else []

    ocr_blocks = _read_ocr_json(template_ocr_path(template_id, page))
    if len(vertical_positions) >= 2:
        column_bounds = [
            (float(left + bbox.x1), float(right + bbox.x1))
            for left, right in zip(vertical_positions, vertical_positions[1:])
            if right - left > 8
        ]
        if not column_bounds:
            column_bounds = [(bbox.x1, bbox.x2)]
    else:
        column_bounds = _cluster_column_bounds_by_text(ocr_blocks, bbox, desired_columns)

    columns: list[ColumnDef] = []
    for index, (left, right) in enumerate(column_bounds, start=1):
        start_ratio = max(0.0, min(1.0, (left - bbox.x1) / bbox.width()))
        end_ratio = max(0.0, min(1.0, (right - bbox.x1) / bbox.width()))
        if end_ratio <= start_ratio:
            continue
        columns.append(
            ColumnDef(
                name=f"col_{index}",
                label=f"列 {index}",
                type="text",
                x_ratio=(start_ratio, end_ratio),
            )
        )

    if not columns:
        columns = [ColumnDef(name="col_1", label="列 1", type="text", x_ratio=(0.0, 1.0))]

    if len(horizontal_positions) >= 2:
        row_bounds = [
            (float(top + bbox.y1), float(bottom + bbox.y1))
            for top, bottom in zip(horizontal_positions, horizontal_positions[1:])
            if bottom - top > 6
        ]
        row_detection = RowDetectionConfig(mode="by_horizontal_lines")
    else:
        row_bounds = []
        row_detection = RowDetectionConfig(mode="by_text_rows")

    return TableSegmentationOut(
        columns=columns,
        row_detection=row_detection,
        row_bounds=row_bounds,
    )
