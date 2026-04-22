"""模板相关 Schema。"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.common import Anchor, BBox

FieldType = Literal[
    "text",
    "multiline_text",
    "date",
    "checkbox",
    "option_select",
    "signature",
    "table",
]
CellType = Literal["text", "multiline_text", "date", "checkbox"]
RowDetectionMode = Literal["by_horizontal_lines", "by_text_rows", "fixed_count"]


class OptionDef(BaseModel):
    """单选项配置。"""

    model_config = ConfigDict(extra="forbid")

    value: str = Field(min_length=1)
    labels: list[str] = Field(min_length=1)


class ColumnDef(BaseModel):
    """表格列定义。"""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, pattern=r"^[A-Za-z][A-Za-z0-9_]*$")
    label: str = Field(min_length=1)
    type: CellType
    x_ratio: tuple[float, float]

    @model_validator(mode="after")
    def validate_x_ratio(self) -> "ColumnDef":
        """验证列横向比例范围合法。"""
        start_ratio, end_ratio = self.x_ratio
        if not 0.0 <= start_ratio < end_ratio <= 1.0:
            raise ValueError("x_ratio 必须位于 0 到 1 之间，且起点小于终点。")
        return self


class RowDetectionConfig(BaseModel):
    """表格行检测配置。"""

    model_config = ConfigDict(extra="forbid")

    mode: RowDetectionMode
    count: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_count(self) -> "RowDetectionConfig":
        """验证固定行数模式下的数量配置。"""
        if self.mode == "fixed_count" and self.count is None:
            raise ValueError("fixed_count 模式必须提供 count。")
        return self


class TemplateFieldIn(BaseModel):
    """模板字段写入模型。"""

    model_config = ConfigDict(extra="forbid")

    id: UUID | None = None
    template_id: UUID | None = None
    page: int = Field(ge=1)
    name: str = Field(min_length=1, pattern=r"^[A-Za-z][A-Za-z0-9_]*$")
    label: str = Field(min_length=1)
    field_type: FieldType
    bbox: BBox
    anchors: list[Anchor] | None = None
    options: list[OptionDef] | None = None
    columns: list[ColumnDef] | None = None
    row_detection: RowDetectionConfig | None = None
    sort_order: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_field_specific_config(self) -> "TemplateFieldIn":
        """验证字段类型与扩展配置的一致性。"""
        if self.field_type == "option_select":
            if not self.options:
                raise ValueError("option_select 字段必须提供 options。")
            if self.columns is not None or self.row_detection is not None:
                raise ValueError("option_select 字段不允许提供表格配置。")
            return self

        if self.field_type == "table":
            if not self.columns:
                raise ValueError("table 字段必须提供 columns。")
            if self.row_detection is None:
                raise ValueError("table 字段必须提供 row_detection。")
            if self.options is not None:
                raise ValueError("table 字段不允许提供 options。")
            return self

        if self.options is not None or self.columns is not None or self.row_detection is not None:
            raise ValueError("当前字段类型不允许提供 options、columns 或 row_detection。")
        return self


class TemplateFieldOut(TemplateFieldIn):
    """模板字段输出模型。"""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: UUID
    template_id: UUID
    anchors: list[Anchor] = Field(default_factory=list)


class TemplateCreate(BaseModel):
    """模板创建请求。"""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=128)
    description: str | None = None
    render_dpi: int = Field(default=200, ge=72, le=600)


class TemplateUpdate(BaseModel):
    """模板元信息更新请求。"""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = None

    @model_validator(mode="after")
    def validate_has_any_update(self) -> "TemplateUpdate":
        """验证至少传入一个可更新字段。"""
        if not ({"name", "description"} & self.model_fields_set):
            raise ValueError("至少需要提供一个可更新字段。")
        return self


class TemplateOut(BaseModel):
    """模板详情输出模型。"""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: UUID
    name: str
    description: str | None
    page_count: int
    render_dpi: int
    created_at: datetime
    updated_at: datetime
    fields: list[TemplateFieldOut] = Field(default_factory=list)


class TemplateListItem(BaseModel):
    """模板列表项。"""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: UUID
    name: str
    description: str | None
    page_count: int
    field_count: int
    updated_at: datetime


class TemplateFieldsBulkReplace(BaseModel):
    """模板字段全量替换请求。"""

    model_config = ConfigDict(extra="forbid")

    fields: list[TemplateFieldIn]


class TableSegmentationIn(BaseModel):
    """表格视觉分割建议请求。"""

    model_config = ConfigDict(extra="forbid")

    page: int = Field(ge=1)
    bbox: BBox
    desired_columns: int | None = Field(default=None, ge=1, le=20)


class TableSegmentationOut(BaseModel):
    """表格视觉分割建议响应。"""

    model_config = ConfigDict(extra="forbid")

    columns: list[ColumnDef] = Field(default_factory=list)
    row_detection: RowDetectionConfig
    row_bounds: list[tuple[float, float]] = Field(default_factory=list)
