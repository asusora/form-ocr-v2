"""OCR 引擎工厂。"""

from __future__ import annotations

from functools import lru_cache

from app.config import settings
from app.ocr.base import OcrEngine


@lru_cache(maxsize=1)
def get_engine() -> OcrEngine:
    """返回当前配置的 OCR 引擎单例。"""
    if settings.ocr_engine == "paddle":
        try:
            from app.ocr.paddle import PaddleOcrEngine
        except ModuleNotFoundError as exc:
            raise RuntimeError("PaddleOCR 引擎尚未实现或相关依赖未安装。") from exc
        return PaddleOcrEngine(lang=settings.ocr_lang, use_gpu=settings.paddle_use_gpu)

    raise ValueError(f"不支持的 OCR 引擎: {settings.ocr_engine}")
