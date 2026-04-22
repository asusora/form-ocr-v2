"""OCR 抽象层导出。"""

from app.ocr.base import OcrEngine, textblock_from_quad
from app.ocr.factory import get_engine
from app.ocr.paddle import PaddleOcrEngine

__all__ = ["OcrEngine", "get_engine", "textblock_from_quad", "PaddleOcrEngine"]
