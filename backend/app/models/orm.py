"""核心业务 ORM 模型。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import CHAR, JSON, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy import UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

FIELD_TYPES = (
    "text",
    "multiline_text",
    "date",
    "checkbox",
    "option_select",
    "signature",
    "table",
)
RECOGNITION_STATUS = ("pending", "processing", "success", "failed")
ALIGNMENT_STATUS = ("auto", "manual_adjusted", "alignment_failed")


class Template(Base):
    """模板主表。"""

    __tablename__ = "templates"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_pdf_path: Mapped[str] = mapped_column(String(512), nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, nullable=False)
    render_dpi: Mapped[int] = mapped_column(Integer, nullable=False, default=200)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    fields: Mapped[list["TemplateField"]] = relationship(
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="TemplateField.sort_order",
    )


class TemplateField(Base):
    """模板字段定义表。"""

    __tablename__ = "template_fields"
    __table_args__ = (UniqueConstraint("template_id", "name", name="uq_template_field_name"),)

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True)
    template_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey("templates.id", ondelete="CASCADE"),
        nullable=False,
    )
    page: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(128), nullable=False)
    field_type: Mapped[str] = mapped_column(Enum(*FIELD_TYPES, name="field_type_enum"), nullable=False)
    bbox: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    anchors: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    options: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    columns: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    row_detection: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    template: Mapped[Template] = relationship(back_populates="fields")


class Recognition(Base):
    """识别任务主表。"""

    __tablename__ = "recognitions"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True)
    template_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("templates.id"), nullable=False)
    template_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    input_pdf_path: Mapped[str] = mapped_column(String(512), nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(
        Enum(*RECOGNITION_STATUS, name="recognition_status_enum"),
        nullable=False,
        default="pending",
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    fields: Mapped[list["RecognitionField"]] = relationship(
        back_populates="recognition",
        cascade="all, delete-orphan",
    )


class RecognitionField(Base):
    """识别结果字段表。"""

    __tablename__ = "recognition_fields"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True)
    recognition_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey("recognitions.id", ondelete="CASCADE"),
        nullable=False,
    )
    template_field_id: Mapped[str] = mapped_column(CHAR(36), nullable=False)
    field_name: Mapped[str] = mapped_column(String(64), nullable=False)
    aligned_bbox: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    raw_value: Mapped[dict[str, Any] | list[Any] | str | bool | None] = mapped_column(
        JSON,
        nullable=True,
    )
    edited_value: Mapped[dict[str, Any] | list[Any] | str | bool | None] = mapped_column(
        JSON,
        nullable=True,
    )
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    crop_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    alignment_status: Mapped[str] = mapped_column(
        Enum(*ALIGNMENT_STATUS, name="alignment_status_enum"),
        nullable=False,
        default="auto",
    )

    recognition: Mapped[Recognition] = relationship(back_populates="fields")
