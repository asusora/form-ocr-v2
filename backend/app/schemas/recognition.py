"""识别任务相关 Schema。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.common import BBox
from app.schemas.template import ColumnDef, FieldType, OptionDef, RowDetectionConfig

RecognitionStatus = Literal["pending", "processing", "success", "failed"]
AlignmentStatus = Literal["auto", "manual_adjusted", "alignment_failed"]


class RecognitionFieldOut(BaseModel):
    """识别字段输出模型。"""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: UUID
    template_field_id: UUID
    field_name: str
    field_label: str | None = None
    page: int
    sort_order: int = 0
    field_type: FieldType | None = None
    options: list[OptionDef] | None = None
    columns: list[ColumnDef] | None = None
    row_detection: RowDetectionConfig | None = None
    aligned_bbox: BBox
    raw_value: Any = None
    edited_value: Any = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    crop_path: str | None = None
    alignment_status: AlignmentStatus


class RecognitionOut(BaseModel):
    """识别任务详情输出模型。"""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: UUID
    template_id: UUID
    template_name: str | None = None
    status: RecognitionStatus
    error_message: str | None = None
    page_count: int
    created_at: datetime
    updated_at: datetime
    fields: list[RecognitionFieldOut] = Field(default_factory=list)


class RecognitionCreated(BaseModel):
    """识别任务创建响应。"""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    status: RecognitionStatus


class ReExtractIn(BaseModel):
    """字段重新识别请求。"""

    model_config = ConfigDict(extra="forbid")

    aligned_bbox: BBox


class RecognitionFieldUpdate(BaseModel):
    """识别字段更新请求。"""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    aligned_bbox: BBox | None = None
    edited_value: Any = None
    alignment_status: AlignmentStatus | None = None

    @model_validator(mode="after")
    def validate_has_any_update(self) -> "RecognitionFieldUpdate":
        """验证至少提供一个待更新字段。"""
        updatable_fields = {"aligned_bbox", "edited_value", "alignment_status"}
        if not any(field_name in self.model_fields_set for field_name in updatable_fields):
            raise ValueError("至少需要提供一个可更新字段。")
        return self


class RecognitionFieldsBatchUpdate(BaseModel):
    """识别字段批量更新请求。"""

    model_config = ConfigDict(extra="forbid")

    fields: list[RecognitionFieldUpdate] = Field(min_length=1)
