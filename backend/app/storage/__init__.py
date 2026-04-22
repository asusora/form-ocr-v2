"""存储路径工具导出。"""

from app.storage.paths import (
    recognition_crop_path,
    recognition_ocr_path,
    recognition_page_image_path,
    recognition_pdf_path,
    template_ocr_path,
    template_page_image_path,
    template_pdf_path,
)

__all__ = [
    "template_pdf_path",
    "template_page_image_path",
    "template_ocr_path",
    "recognition_pdf_path",
    "recognition_page_image_path",
    "recognition_ocr_path",
    "recognition_crop_path",
]
