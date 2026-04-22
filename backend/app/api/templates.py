"""模板业务 API。"""

from __future__ import annotations

from fastapi import APIRouter, File, Form, Response, UploadFile
from fastapi.responses import FileResponse

from app.api.deps import DbDep
from app.api.errors import bad_request, not_found, service_unavailable
from app.config import settings
from app.schemas.template import (
    TableSegmentationIn,
    TableSegmentationOut,
    TemplateFieldIn,
    TemplateFieldOut,
    TemplateFieldsBulkReplace,
    TemplateListItem,
    TemplateOut,
    TemplateUpdate,
)
from app.storage.paths import template_page_image_path
from app.template import (
    delete_field,
    get_template,
    list_templates,
    save_fields_with_anchors,
    save_template_from_pdf,
    soft_delete,
    suggest_table_structure,
    update_field_with_anchor,
    update_meta,
)

router = APIRouter(prefix="/api/templates", tags=["templates"])


def _is_ocr_runtime_unavailable_error(exc: RuntimeError) -> bool:
    """判断异常是否表示 OCR 运行时依赖不可用。"""
    message = str(exc).lower()
    dependency_markers = (
        "paddlepaddle",
        "paddleocr",
        "ocr 引擎",
    )
    state_markers = (
        "not installed",
        "unavailable",
        "未安装",
        "不可用",
    )
    return any(marker in message for marker in dependency_markers) and any(
        marker in message for marker in state_markers
    )


@router.post("", response_model=TemplateOut, status_code=201)
async def create(
    db: DbDep,
    file: UploadFile = File(...),
    name: str = Form(...),
    description: str | None = Form(None),
    render_dpi: int = Form(settings.render_dpi_default),
) -> TemplateOut:
    """上传模板 PDF 并创建模板。"""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise bad_request("只允许上传 PDF 文件。", code="FILE_TYPE_INVALID")

    pdf_bytes = await file.read()
    if len(pdf_bytes) > settings.max_pdf_mb * 1024 * 1024:
        raise bad_request(
            f"PDF 大小不能超过 {settings.max_pdf_mb}MB。",
            code="FILE_TOO_LARGE",
        )

    try:
        template_id = save_template_from_pdf(
            db=db,
            name=name.strip(),
            description=description.strip()
            if isinstance(description, str) and description.strip()
            else None,
            render_dpi=render_dpi,
            pdf_bytes=pdf_bytes,
        )
    except RuntimeError as exc:
        if _is_ocr_runtime_unavailable_error(exc):
            raise service_unavailable(
                "OCR 引擎不可用，请先安装 PaddlePaddle 运行时依赖。",
                code="OCR_ENGINE_UNAVAILABLE",
            ) from exc
        raise
    template = get_template(db, template_id)
    if template is None:
        raise not_found(f"模板 {template_id} 创建后未找到。", code="TEMPLATE_MISSING")
    return _to_template_out(template)


@router.get("", response_model=list[TemplateListItem])
def list_all(db: DbDep) -> list[TemplateListItem]:
    """获取模板列表。"""
    return [
        TemplateListItem(
            id=template.id,
            name=template.name,
            description=template.description,
            page_count=template.page_count,
            field_count=field_count,
            updated_at=template.updated_at,
        )
        for template, field_count in list_templates(db)
    ]


@router.get("/{template_id}", response_model=TemplateOut)
def get_one(template_id: str, db: DbDep) -> TemplateOut:
    """获取模板详情。"""
    template = get_template(db, template_id)
    if template is None:
        raise not_found(f"模板 {template_id} 不存在。")
    return _to_template_out(template)


@router.put("/{template_id}", response_model=TemplateOut)
def update(template_id: str, body: TemplateUpdate, db: DbDep) -> TemplateOut:
    """更新模板元信息。"""
    template = update_meta(
        db,
        template_id,
        name=body.name,
        description=body.description,
        fields_to_update=body.model_fields_set,
    )
    if template is None:
        raise not_found(f"模板 {template_id} 不存在。")
    return _to_template_out(template)


@router.delete("/{template_id}", status_code=204, response_class=Response)
def delete(template_id: str, db: DbDep) -> Response:
    """软删除模板。"""
    if not soft_delete(db, template_id):
        raise not_found(f"模板 {template_id} 不存在。")
    return Response(status_code=204)


@router.get("/{template_id}/pages/{page}")
def get_page(template_id: str, page: int, db: DbDep) -> FileResponse:
    """返回模板页图片。"""
    template = get_template(db, template_id)
    if template is None:
        raise not_found(f"模板 {template_id} 不存在。")
    if page < 1 or page > template.page_count:
        raise bad_request(f"页码超出范围: {page}", code="PAGE_OUT_OF_RANGE")

    image_path = template_page_image_path(template_id, page)
    if not image_path.exists():
        raise not_found(f"模板页图片不存在: {page}", code="PAGE_IMAGE_MISSING")
    return FileResponse(image_path, media_type="image/png")


@router.post("/{template_id}/fields", response_model=TemplateOut)
def replace_fields(
    template_id: str,
    body: TemplateFieldsBulkReplace,
    db: DbDep,
) -> TemplateOut:
    """批量保存模板字段。"""
    template = get_template(db, template_id)
    if template is None:
        raise not_found(f"模板 {template_id} 不存在。")
    save_fields_with_anchors(db, template_id, body.fields)
    template = get_template(db, template_id)
    if template is None:
        raise not_found(f"模板 {template_id} 不存在。")
    return _to_template_out(template)


@router.put("/{template_id}/fields/{field_id}", response_model=TemplateOut)
def update_single_field(
    template_id: str,
    field_id: str,
    body: TemplateFieldIn,
    db: DbDep,
) -> TemplateOut:
    """更新单个模板字段。"""
    template = get_template(db, template_id)
    if template is None:
        raise not_found(f"模板 {template_id} 不存在。")

    updated_field = update_field_with_anchor(db, template_id, field_id, body)
    if updated_field is None:
        raise not_found(f"模板字段 {field_id} 不存在。", code="FIELD_NOT_FOUND")

    template = get_template(db, template_id)
    if template is None:
        raise not_found(f"模板 {template_id} 不存在。")
    return _to_template_out(template)


@router.delete(
    "/{template_id}/fields/{field_id}",
    status_code=204,
    response_class=Response,
)
def delete_single_field(template_id: str, field_id: str, db: DbDep) -> Response:
    """删除模板字段。"""
    template = get_template(db, template_id)
    if template is None:
        raise not_found(f"模板 {template_id} 不存在。")
    if not delete_field(db, template_id, field_id):
        raise not_found(f"模板字段 {field_id} 不存在。", code="FIELD_NOT_FOUND")
    return Response(status_code=204)


@router.post("/{template_id}/table-segmentation", response_model=TableSegmentationOut)
def table_segmentation(
    template_id: str,
    body: TableSegmentationIn,
    db: DbDep,
) -> TableSegmentationOut:
    """返回表格视觉分割建议。"""
    template = get_template(db, template_id)
    if template is None:
        raise not_found(f"模板 {template_id} 不存在。")
    if body.page > template.page_count:
        raise bad_request(f"页码超出范围: {body.page}", code="PAGE_OUT_OF_RANGE")
    try:
        return suggest_table_structure(
            template_id=template_id,
            page=body.page,
            bbox=body.bbox,
            desired_columns=body.desired_columns,
        )
    except FileNotFoundError as exc:
        raise not_found(str(exc), code="PAGE_IMAGE_MISSING") from exc


def _to_template_field_out(field: object) -> TemplateFieldOut:
    """把 ORM 模板字段转换为响应模型。"""
    return TemplateFieldOut.model_validate(field)


def _to_template_out(template: object) -> TemplateOut:
    """把 ORM 模板转换为响应模型。"""
    return TemplateOut(
        id=template.id,
        name=template.name,
        description=template.description,
        page_count=template.page_count,
        render_dpi=template.render_dpi,
        created_at=template.created_at,
        updated_at=template.updated_at,
        fields=[_to_template_field_out(field) for field in template.fields],
    )
