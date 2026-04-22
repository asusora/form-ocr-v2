"""模板数据访问层。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.orm import Template, TemplateField


def create_template(
    db: Session,
    template_id: str,
    name: str,
    description: str | None,
    source_pdf_path: str,
    page_count: int,
    render_dpi: int,
) -> Template:
    """创建模板记录。ID 由调用方传入，保证与磁盘文件目录一致。"""
    template = Template(
        id=template_id,
        name=name,
        description=description,
        source_pdf_path=source_pdf_path,
        page_count=page_count,
        render_dpi=render_dpi,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


def get_template(db: Session, template_id: str) -> Template | None:
    """获取未被软删除的模板详情。"""
    statement = (
        select(Template)
        .options(selectinload(Template.fields))
        .where(Template.id == template_id, Template.deleted_at.is_(None))
    )
    return db.scalars(statement).first()


def list_templates(db: Session) -> list[tuple[Template, int]]:
    """返回模板列表及字段数量。"""
    statement = (
        select(Template, func.count(TemplateField.id))
        .outerjoin(TemplateField, TemplateField.template_id == Template.id)
        .where(Template.deleted_at.is_(None))
        .group_by(Template.id)
        .order_by(Template.updated_at.desc())
    )
    return [(template, int(field_count)) for template, field_count in db.execute(statement).all()]


def soft_delete(db: Session, template_id: str) -> bool:
    """软删除模板。"""
    template = db.get(Template, template_id)
    if template is None or template.deleted_at is not None:
        return False

    template.deleted_at = datetime.utcnow()
    template.updated_at = datetime.utcnow()
    db.commit()
    return True


def update_meta(
    db: Session,
    template_id: str,
    name: str | None,
    description: str | None,
    fields_to_update: set[str] | None = None,
) -> Template | None:
    """更新模板元信息。"""
    template = get_template(db, template_id)
    if template is None:
        return None

    updated_fields = fields_to_update or set()
    if "name" in updated_fields:
        template.name = name or template.name
    if "description" in updated_fields:
        template.description = description
    template.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(template)
    return template


def replace_fields(db: Session, template_id: str, fields: list[TemplateField]) -> None:
    """全量替换模板字段。"""
    template = db.get(Template, template_id)
    if template is None:
        raise ValueError(f"模板不存在: {template_id}")

    db.query(TemplateField).filter(TemplateField.template_id == template_id).delete()
    for field in fields:
        db.add(field)
    template.updated_at = datetime.utcnow()
    db.commit()


def get_template_field(db: Session, template_id: str, field_id: str) -> TemplateField | None:
    """获取模板下的单个字段。"""
    field = db.get(TemplateField, field_id)
    if field is None or field.template_id != template_id:
        return None
    return field


def delete_template_field(db: Session, template_id: str, field_id: str) -> bool:
    """删除模板字段。"""
    field = get_template_field(db, template_id, field_id)
    if field is None:
        return False

    template = db.get(Template, template_id)
    db.delete(field)
    if template is not None:
        template.updated_at = datetime.utcnow()
    db.commit()
    return True
