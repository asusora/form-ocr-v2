"""识别业务 API。"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, File, Form, UploadFile
from fastapi.responses import FileResponse

from app.api.deps import DbDep
from app.api.errors import bad_request, not_found
from app.config import settings
from app.models.orm import Recognition, RecognitionField
from app.pipeline import create_recognition, re_extract_single_field, run_recognition
from app.pipeline.export import build_json_output, write_excel
from app.pipeline.orchestrator import _snapshot_from_template
from app.schemas.common import BBox
from app.schemas.recognition import (
    ReExtractIn,
    RecognitionCreated,
    RecognitionFieldOut,
    RecognitionFieldsBatchUpdate,
    RecognitionOut,
)
from app.storage.paths import recognition_page_image_path, recognition_pdf_path
from app.template import get_template

router = APIRouter(prefix="/api/recognitions", tags=["recognitions"])


@router.post("", response_model=RecognitionCreated, status_code=202)
async def create(
    background: BackgroundTasks,
    db: DbDep,
    file: UploadFile = File(...),
    template_id: str = Form(...),
) -> RecognitionCreated:
    """创建识别任务。"""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise bad_request("只允许上传 PDF 文件。", code="FILE_TYPE_INVALID")

    template = get_template(db, template_id)
    if template is None:
        raise not_found(f"模板 {template_id} 不存在。")

    pdf_bytes = await file.read()
    if len(pdf_bytes) > settings.max_pdf_mb * 1024 * 1024:
        raise bad_request(f"PDF 大小不能超过 {settings.max_pdf_mb}MB。", code="FILE_TOO_LARGE")

    snapshot = _snapshot_from_template(template)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        temp_file.write(pdf_bytes)
        temp_path = Path(temp_file.name)

    recognition_id = create_recognition(
        db=db,
        template_id=template_id,
        template_snapshot=snapshot,
        input_pdf_path=str(temp_path),
    )
    final_pdf_path = recognition_pdf_path(recognition_id)
    temp_path.replace(final_pdf_path)

    recognition = db.get(Recognition, recognition_id)
    if recognition is None:
        raise not_found(f"识别任务 {recognition_id} 创建后未找到。", code="RECOGNITION_MISSING")
    recognition.input_pdf_path = str(final_pdf_path)
    db.commit()

    background.add_task(run_recognition, recognition_id)
    return RecognitionCreated(id=recognition_id, status="pending")


@router.get("/{recognition_id}", response_model=RecognitionOut)
def get_one(recognition_id: str, db: DbDep) -> RecognitionOut:
    """获取识别任务详情。"""
    recognition = db.get(Recognition, recognition_id)
    if recognition is None:
        raise not_found(f"识别任务 {recognition_id} 不存在。")
    return _to_recognition_out(recognition)


@router.get("/{recognition_id}/pages/{page}")
def get_page(recognition_id: str, page: int, db: DbDep) -> FileResponse:
    """返回识别页图片。"""
    recognition = db.get(Recognition, recognition_id)
    if recognition is None:
        raise not_found(f"识别任务 {recognition_id} 不存在。")
    if page < 1 or page > max(recognition.page_count, 1):
        raise bad_request(f"页码超出范围: {page}", code="PAGE_OUT_OF_RANGE")

    image_path = recognition_page_image_path(recognition_id, page)
    if not image_path.exists():
        raise not_found("识别页图片不存在。", code="PAGE_IMAGE_MISSING")
    return FileResponse(image_path, media_type="image/png")


@router.get("/{recognition_id}/crops/{field_id}")
def get_crop(recognition_id: str, field_id: str, db: DbDep) -> FileResponse:
    """返回识别字段切图。"""
    field = db.get(RecognitionField, field_id)
    if field is None or field.recognition_id != recognition_id or not field.crop_path:
        raise not_found("识别字段切图不存在。", code="CROP_NOT_FOUND")
    return FileResponse(field.crop_path, media_type="image/png")


@router.post("/{recognition_id}/re-extract/{field_id}", response_model=RecognitionFieldOut)
def re_extract(
    recognition_id: str,
    field_id: str,
    body: ReExtractIn,
    db: DbDep,
) -> RecognitionFieldOut:
    """基于新坐标重新识别单个字段。"""
    field = re_extract_single_field(db, recognition_id, field_id, body.aligned_bbox)
    if field is None:
        raise not_found("识别任务或字段不存在。", code="FIELD_NOT_FOUND")

    recognition = db.get(Recognition, recognition_id)
    if recognition is None:
        raise not_found(f"识别任务 {recognition_id} 不存在。")
    return _to_recognition_field_out(recognition, field)


@router.put("/{recognition_id}/fields", response_model=RecognitionOut)
def update_fields(
    recognition_id: str,
    body: RecognitionFieldsBatchUpdate,
    db: DbDep,
) -> RecognitionOut:
    """批量保存识别字段编辑结果。"""
    recognition = db.get(Recognition, recognition_id)
    if recognition is None:
        raise not_found(f"识别任务 {recognition_id} 不存在。")

    for field_update in body.fields:
        field = db.get(RecognitionField, str(field_update.id))
        if field is None or field.recognition_id != recognition_id:
            continue
        if "aligned_bbox" in field_update.model_fields_set:
            field.aligned_bbox = field_update.aligned_bbox.model_dump() if field_update.aligned_bbox else field.aligned_bbox
        if "edited_value" in field_update.model_fields_set:
            field.edited_value = field_update.edited_value
        if "alignment_status" in field_update.model_fields_set and field_update.alignment_status is not None:
            field.alignment_status = field_update.alignment_status

    db.commit()
    recognition = db.get(Recognition, recognition_id)
    if recognition is None:
        raise not_found(f"识别任务 {recognition_id} 不存在。")
    return _to_recognition_out(recognition)


@router.get("/{recognition_id}/export")
def export(recognition_id: str, db: DbDep, format: str = "json") -> FileResponse:
    """导出识别结果。"""
    recognition = db.get(Recognition, recognition_id)
    if recognition is None:
        raise not_found(f"识别任务 {recognition_id} 不存在。")
    if recognition.status != "success":
        raise bad_request("仅成功状态的识别任务允许导出。", code="RECOGNITION_NOT_READY")

    export_payload = _to_export_payload(recognition)
    if format == "json":
        destination = Path(tempfile.mkstemp(suffix=".json")[1])
        destination.write_text(
            json.dumps(build_json_output(export_payload), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return FileResponse(
            destination,
            media_type="application/json",
            filename=f"{export_payload.get('template_name') or 'recognition'}-{recognition_id}.json",
        )

    if format == "xlsx":
        destination = Path(tempfile.mkstemp(suffix=".xlsx")[1])
        write_excel(export_payload, destination)
        return FileResponse(
            destination,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=f"{export_payload.get('template_name') or 'recognition'}-{recognition_id}.xlsx",
        )

    raise bad_request(f"不支持的导出格式: {format}", code="FORMAT_NOT_SUPPORTED")


def _snapshot_field_map(recognition: Recognition) -> dict[str, dict[str, Any]]:
    """按模板字段 ID 构建快照映射。"""
    return {
        str(field["id"]): field
        for field in recognition.template_snapshot.get("fields", [])
    }


def _field_sort_key(field: RecognitionField, snapshot_map: dict[str, dict[str, Any]]) -> tuple[int, int, str]:
    """生成识别字段排序键。"""
    meta = snapshot_map.get(field.template_field_id, {})
    return (
        int(meta.get("page", 1)),
        int(meta.get("sort_order", 0)),
        field.field_name,
    )


def _to_recognition_field_out(
    recognition: Recognition,
    field: RecognitionField,
) -> RecognitionFieldOut:
    """把 ORM 识别字段转换为响应模型。"""
    snapshot_field = _snapshot_field_map(recognition).get(field.template_field_id, {})
    return RecognitionFieldOut(
        id=field.id,
        template_field_id=field.template_field_id,
        field_name=field.field_name,
        field_label=snapshot_field.get("label"),
        page=int(snapshot_field.get("page", 1)),
        sort_order=int(snapshot_field.get("sort_order", 0)),
        field_type=snapshot_field.get("field_type"),
        options=snapshot_field.get("options"),
        columns=snapshot_field.get("columns"),
        row_detection=snapshot_field.get("row_detection"),
        aligned_bbox=BBox.model_validate(field.aligned_bbox),
        raw_value=field.raw_value,
        edited_value=field.edited_value,
        confidence=field.confidence,
        crop_path=f"/api/recognitions/{recognition.id}/crops/{field.id}" if field.crop_path else None,
        alignment_status=field.alignment_status,
    )


def _to_recognition_out(recognition: Recognition) -> RecognitionOut:
    """把 ORM 识别任务转换为响应模型。"""
    snapshot_map = _snapshot_field_map(recognition)
    ordered_fields = sorted(recognition.fields, key=lambda field: _field_sort_key(field, snapshot_map))
    return RecognitionOut(
        id=recognition.id,
        template_id=recognition.template_id,
        template_name=recognition.template_snapshot.get("name"),
        status=recognition.status,
        error_message=recognition.error_message,
        page_count=recognition.page_count,
        created_at=recognition.created_at,
        updated_at=recognition.updated_at,
        fields=[_to_recognition_field_out(recognition, field) for field in ordered_fields],
    )


def _to_export_payload(recognition: Recognition) -> dict[str, Any]:
    """将识别任务转换为导出模块使用的标准结构。"""
    snapshot_map = _snapshot_field_map(recognition)
    ordered_fields = sorted(recognition.fields, key=lambda field: _field_sort_key(field, snapshot_map))
    return {
        "id": recognition.id,
        "template_id": recognition.template_id,
        "template_name": recognition.template_snapshot.get("name"),
        "status": recognition.status,
        "fields": [
            {
                "name": field.field_name,
                "label": snapshot_map.get(field.template_field_id, {}).get("label", field.field_name),
                "field_type": snapshot_map.get(field.template_field_id, {}).get("field_type", "text"),
                "raw_value": field.raw_value,
                "edited_value": field.edited_value,
            }
            for field in ordered_fields
        ],
    }
