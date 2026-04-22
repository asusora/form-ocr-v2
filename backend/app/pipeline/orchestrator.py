"""识别任务主流程。"""

from __future__ import annotations

import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image
from sqlalchemy.orm import Session

from app.alignment import align_page
from app.alignment.anchors import extract_anchors_for_field
from app.config import settings
from app.db import SessionLocal, get_engine as get_db_engine
from app.extractors import get_extractor
from app.extractors.base import ExtractContext, crop_image
from app.models.orm import Recognition, RecognitionField
from app.ocr import get_engine as get_ocr_engine
from app.pdf.render import render_page_to_array, render_pdf_to_images
from app.schemas.common import Anchor, BBox, TextBlock
from app.storage.paths import (
    recognition_crop_path,
    recognition_ocr_path,
    recognition_page_image_path,
    template_ocr_path,
)

logger = logging.getLogger(__name__)


def _read_template_blocks(path: Path) -> list[TextBlock]:
    """读取模板页 OCR 缓存。"""
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [TextBlock.model_validate(item) for item in payload]


def _build_template_field_bboxes(template: Any) -> dict[int, list[BBox]]:
    """按页收集模板字段框，供缺失锚点时回填使用。"""
    bboxes_by_page: dict[int, list[BBox]] = {}
    for field in template.fields:
        page = int(field.page)
        bboxes_by_page.setdefault(page, []).append(BBox.model_validate(field.bbox))
    return bboxes_by_page


def _normalize_snapshot_anchors(
    template: Any,
    field: Any,
    bboxes_by_page: dict[int, list[BBox]],
    page_block_cache: dict[int, list[TextBlock]],
) -> list[dict[str, Any]]:
    """规范化字段锚点；历史空锚点模板在此处按模板 OCR 自动补算。"""
    existing_anchors = field.anchors or []
    if existing_anchors:
        return [Anchor.model_validate(anchor).model_dump() for anchor in existing_anchors]

    page = int(field.page)
    if page not in page_block_cache:
        ocr_cache_path = template_ocr_path(str(template.id), page)
        if not ocr_cache_path.exists():
            logger.warning(
                "模板快照缺少 OCR 缓存，无法为字段补算锚点：template_id=%s page=%s field=%s",
                template.id,
                page,
                field.name,
            )
            page_block_cache[page] = []
        else:
            try:
                page_block_cache[page] = _read_template_blocks(ocr_cache_path)
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                logger.warning(
                    "模板 OCR 缓存损坏，无法为字段补算锚点：template_id=%s page=%s field=%s error=%s",
                    template.id,
                    page,
                    field.name,
                    exc,
                )
                page_block_cache[page] = []

    page_blocks = page_block_cache.get(page, [])
    if not page_blocks:
        return []

    field_bbox = BBox.model_validate(field.bbox)
    anchors = extract_anchors_for_field(
        field_bbox=field_bbox,
        page_blocks=page_blocks,
        all_field_bboxes=bboxes_by_page.get(page, [field_bbox]),
        n=3,
    )
    if anchors:
        logger.info(
            "模板快照已补算缺失锚点：template_id=%s page=%s field=%s count=%s",
            template.id,
            page,
            field.name,
            len(anchors),
        )
    return [anchor.model_dump() for anchor in anchors]


def _snapshot_from_template(template: Any) -> dict[str, Any]:
    """根据模板 ORM 生成识别快照。"""
    bboxes_by_page = _build_template_field_bboxes(template)
    page_block_cache: dict[int, list[TextBlock]] = {}
    return {
        "name": template.name,
        "render_dpi": template.render_dpi,
        "page_count": template.page_count,
        "fields": [
            {
                "id": field.id,
                "page": field.page,
                "name": field.name,
                "label": field.label,
                "field_type": field.field_type,
                "bbox": field.bbox,
                "anchors": _normalize_snapshot_anchors(
                    template=template,
                    field=field,
                    bboxes_by_page=bboxes_by_page,
                    page_block_cache=page_block_cache,
                ),
                "options": field.options,
                "columns": field.columns,
                "row_detection": field.row_detection,
                "sort_order": field.sort_order,
            }
            for field in sorted(template.fields, key=lambda item: (item.page, item.sort_order))
        ],
    }


def _write_blocks(path: Path, blocks: list[TextBlock]) -> None:
    """写入 OCR 缓存。"""
    path.write_text(
        json.dumps([block.model_dump() for block in blocks], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _read_blocks(path: Path) -> list[TextBlock]:
    """读取 OCR 缓存。"""
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [TextBlock.model_validate(item) for item in payload]


def _save_crop(page_image: np.ndarray, bbox: BBox, destination: Path) -> bool:
    """保存识别字段切图。"""
    crop = crop_image(page_image, bbox)
    if crop.size == 0:
        return False
    bgr_crop = cv2.cvtColor(crop, cv2.COLOR_RGB2BGR)
    return bool(cv2.imwrite(str(destination), bgr_crop))


def _ensure_not_timed_out(started_at: float) -> None:
    """检查识别流程是否超时。"""
    elapsed = time.monotonic() - started_at
    if elapsed > settings.recognition_timeout_seconds:
        raise TimeoutError(f"识别流程超过 {settings.recognition_timeout_seconds} 秒超时限制。")


def _load_cached_page_image(
    recognition_id: str,
    page: int,
    input_pdf: Path,
    dpi: int,
) -> np.ndarray:
    """加载已缓存的识别页图像，必要时即时渲染。"""
    cached_path = recognition_page_image_path(recognition_id, page)
    if cached_path.exists():
        return np.asarray(Image.open(cached_path).convert("RGB"))

    rendered = render_page_to_array(input_pdf, page=page, dpi=dpi)
    Image.fromarray(rendered).save(cached_path)
    return rendered


def create_recognition(
    db: Session,
    template_id: str,
    template_snapshot: dict[str, Any],
    input_pdf_path: str,
) -> str:
    """创建识别任务记录。"""
    recognition_id = str(uuid.uuid4())
    recognition = Recognition(
        id=recognition_id,
        template_id=template_id,
        template_snapshot=template_snapshot,
        input_pdf_path=input_pdf_path,
        status="pending",
        page_count=0,
    )
    db.add(recognition)
    db.commit()
    return recognition_id


def run_recognition(recognition_id: str) -> None:
    """执行识别任务主流程。"""
    get_db_engine()
    db = SessionLocal()
    recognition: Recognition | None = None
    try:
        recognition = db.get(Recognition, recognition_id)
        if recognition is None:
            return

        started_at = time.monotonic()
        recognition.status = "processing"
        recognition.error_message = None
        for existing_field in list(recognition.fields):
            db.delete(existing_field)
        db.commit()

        snapshot = recognition.template_snapshot
        render_dpi = int(snapshot["render_dpi"])
        input_pdf = Path(recognition.input_pdf_path)
        pages_dir = recognition_page_image_path(recognition_id, 1).parent
        page_paths = render_pdf_to_images(input_pdf, pages_dir, dpi=render_dpi)
        recognition.page_count = len(page_paths)
        db.commit()
        _ensure_not_timed_out(started_at)

        ocr_engine = get_ocr_engine()
        page_cache: dict[int, tuple[np.ndarray, list[TextBlock]]] = {}
        for page_number, page_path in enumerate(page_paths, start=1):
            page_image = np.asarray(Image.open(page_path).convert("RGB"))
            page_blocks = ocr_engine.recognize(page_image)
            _write_blocks(recognition_ocr_path(recognition_id, page_number), page_blocks)
            page_cache[page_number] = (page_image, page_blocks)
            _ensure_not_timed_out(started_at)

        fields_by_page: dict[int, list[dict[str, Any]]] = {}
        for field in snapshot.get("fields", []):
            fields_by_page.setdefault(int(field["page"]), []).append(field)

        for page_number, field_defs in fields_by_page.items():
            cached_page = page_cache.get(page_number)
            if cached_page is None:
                continue

            page_image, page_blocks = cached_page
            page_height, page_width = page_image.shape[:2]
            page_fields = [
                (
                    BBox.model_validate(field_def["bbox"]),
                    [Anchor.model_validate(anchor) for anchor in field_def.get("anchors") or []],
                )
                for field_def in field_defs
            ]
            alignment_result = align_page(
                page_fields=page_fields,
                target_blocks=page_blocks,
                page_width=float(page_width),
                page_height=float(page_height),
            )

            for field_def, (aligned_bbox, alignment_status) in zip(
                field_defs,
                alignment_result.fields,
                strict=True,
            ):
                field_id = str(uuid.uuid4())

                if alignment_status == "alignment_failed":
                    # 对齐失败时 aligned_bbox 保留的是模板原位置，没有意义也不
                    # 应该按模板位置乱裁一张图/乱跑抽取器，让人工在前端补齐。
                    db.add(
                        RecognitionField(
                            id=field_id,
                            recognition_id=recognition_id,
                            template_field_id=str(field_def["id"]),
                            field_name=str(field_def["name"]),
                            aligned_bbox=aligned_bbox.model_dump(),
                            raw_value=None,
                            edited_value=None,
                            confidence=None,
                            crop_path=None,
                            alignment_status=alignment_status,
                        )
                    )
                    continue

                crop_path = recognition_crop_path(recognition_id, field_id)
                saved_crop = _save_crop(page_image, aligned_bbox, crop_path)
                extractor = get_extractor(str(field_def["field_type"]))
                context = ExtractContext(
                    page_blocks=page_blocks,
                    page_image=page_image,
                    field_config={
                        "options": field_def.get("options"),
                        "columns": field_def.get("columns"),
                        "row_detection": field_def.get("row_detection"),
                    },
                )
                result = extractor.extract(page_image, aligned_bbox, context)
                db.add(
                    RecognitionField(
                        id=field_id,
                        recognition_id=recognition_id,
                        template_field_id=str(field_def["id"]),
                        field_name=str(field_def["name"]),
                        aligned_bbox=aligned_bbox.model_dump(),
                        raw_value=result.raw_value,
                        edited_value=None,
                        confidence=result.confidence,
                        crop_path=str(crop_path) if saved_crop else None,
                        alignment_status=alignment_status,
                    )
                )
            db.commit()
            _ensure_not_timed_out(started_at)

        recognition.status = "success"
        recognition.error_message = None
        db.commit()
    except Exception as exc:
        if recognition is None:
            recognition = db.get(Recognition, recognition_id)
        if recognition is not None:
            recognition.status = "failed"
            recognition.error_message = f"{type(exc).__name__}: {exc}"
            db.commit()
        raise
    finally:
        db.close()


def re_extract_single_field(
    db: Session,
    recognition_id: str,
    field_id: str,
    new_bbox: BBox,
) -> RecognitionField | None:
    """基于新框坐标重新抽取单个识别字段。"""
    recognition = db.get(Recognition, recognition_id)
    if recognition is None:
        return None

    recognition_field = db.get(RecognitionField, field_id)
    if recognition_field is None or recognition_field.recognition_id != recognition_id:
        return None

    field_definition = next(
        (
            field
            for field in recognition.template_snapshot.get("fields", [])
            if str(field["id"]) == recognition_field.template_field_id
        ),
        None,
    )
    if field_definition is None:
        return None

    page = int(field_definition["page"])
    render_dpi = int(recognition.template_snapshot["render_dpi"])
    input_pdf = Path(recognition.input_pdf_path)
    page_image = _load_cached_page_image(recognition_id, page, input_pdf, render_dpi)

    ocr_cache_path = recognition_ocr_path(recognition_id, page)
    if ocr_cache_path.exists():
        page_blocks = _read_blocks(ocr_cache_path)
    else:
        page_blocks = get_ocr_engine().recognize(page_image)
        _write_blocks(ocr_cache_path, page_blocks)

    crop_path = recognition_crop_path(recognition_id, field_id)
    saved_crop = _save_crop(page_image, new_bbox, crop_path)
    extractor = get_extractor(str(field_definition["field_type"]))
    result = extractor.extract(
        page_image,
        new_bbox,
        ExtractContext(
            page_blocks=page_blocks,
            page_image=page_image,
            field_config={
                "options": field_definition.get("options"),
                "columns": field_definition.get("columns"),
                "row_detection": field_definition.get("row_detection"),
            },
        ),
    )

    recognition_field.aligned_bbox = new_bbox.model_dump()
    recognition_field.raw_value = result.raw_value
    recognition_field.edited_value = None
    recognition_field.confidence = result.confidence
    recognition_field.crop_path = str(crop_path) if saved_crop else None
    recognition_field.alignment_status = "manual_adjusted"
    db.commit()
    db.refresh(recognition_field)
    return recognition_field
