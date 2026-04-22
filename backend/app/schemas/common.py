"""通用 Schema 定义。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BBox(BaseModel):
    """矩形边界框。"""

    model_config = ConfigDict(extra="forbid")

    x1: float
    y1: float
    x2: float
    y2: float

    @model_validator(mode="after")
    def validate_coordinates(self) -> "BBox":
        """验证边界框坐标顺序有效。"""
        if self.x2 <= self.x1:
            raise ValueError("x2 必须大于 x1。")
        if self.y2 <= self.y1:
            raise ValueError("y2 必须大于 y1。")
        return self

    def width(self) -> float:
        """返回边界框宽度。"""
        return self.x2 - self.x1

    def height(self) -> float:
        """返回边界框高度。"""
        return self.y2 - self.y1

    def center(self) -> tuple[float, float]:
        """返回边界框中心点。"""
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)


class TextBlock(BaseModel):
    """OCR 文本块。"""

    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1)
    bbox: BBox
    confidence: float = Field(ge=0.0, le=1.0)


class Anchor(BaseModel):
    """字段锚点定义。"""

    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1)
    template_bbox: BBox
    offset_from_field: tuple[float, float] = Field(
        ...,
        description="字段中心点到锚点中心点的偏移量。",
    )


class ExtractResult(BaseModel):
    """字段抽取结果。"""

    model_config = ConfigDict(extra="forbid")

    raw_value: Any = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    crop_path: str | None = None
