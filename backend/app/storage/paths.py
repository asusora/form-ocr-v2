"""本地文件存储路径助手。"""

from __future__ import annotations

from pathlib import Path

from app.config import settings


def _ensure_parent(path: Path) -> Path:
    """确保目标路径的父目录存在。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _validate_segment(segment_name: str, value: str) -> str:
    """校验路径段，防止路径穿越与空值。"""
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{segment_name} 不能为空。")
    if normalized in {".", ".."}:
        raise ValueError(f"{segment_name} 不能为当前目录或父目录。")
    if any(token in normalized for token in ("/", "\\")):
        raise ValueError(f"{segment_name} 不能包含路径分隔符。")
    return normalized


def _validate_page(page: int) -> int:
    """校验页码必须为正整数。"""
    if page < 1:
        raise ValueError("page 必须大于或等于 1。")
    return page


def template_pdf_path(template_id: str) -> Path:
    """返回模板源 PDF 的存储路径。"""
    safe_template_id = _validate_segment("template_id", template_id)
    return _ensure_parent(settings.data_dir / "templates" / safe_template_id / "source.pdf")


def template_page_image_path(template_id: str, page: int) -> Path:
    """返回模板页图片缓存路径。"""
    safe_template_id = _validate_segment("template_id", template_id)
    safe_page = _validate_page(page)
    return _ensure_parent(
        settings.data_dir / "templates" / safe_template_id / "pages" / f"{safe_page}.png"
    )


def template_ocr_path(template_id: str, page: int) -> Path:
    """返回模板页 OCR 缓存路径。"""
    safe_template_id = _validate_segment("template_id", template_id)
    safe_page = _validate_page(page)
    return _ensure_parent(
        settings.data_dir / "templates" / safe_template_id / "ocr" / f"{safe_page}.json"
    )


def recognition_pdf_path(recognition_id: str) -> Path:
    """返回识别任务输入 PDF 的存储路径。"""
    safe_recognition_id = _validate_segment("recognition_id", recognition_id)
    return _ensure_parent(
        settings.data_dir / "recognitions" / safe_recognition_id / "input.pdf"
    )


def recognition_page_image_path(recognition_id: str, page: int) -> Path:
    """返回识别任务页图片缓存路径。"""
    safe_recognition_id = _validate_segment("recognition_id", recognition_id)
    safe_page = _validate_page(page)
    return _ensure_parent(
        settings.data_dir / "recognitions" / safe_recognition_id / "pages" / f"{safe_page}.png"
    )


def recognition_ocr_path(recognition_id: str, page: int) -> Path:
    """返回识别任务页 OCR 缓存路径。"""
    safe_recognition_id = _validate_segment("recognition_id", recognition_id)
    safe_page = _validate_page(page)
    return _ensure_parent(
        settings.data_dir / "recognitions" / safe_recognition_id / "ocr" / f"{safe_page}.json"
    )


def recognition_crop_path(recognition_id: str, field_id: str) -> Path:
    """返回识别字段切图路径。"""
    safe_recognition_id = _validate_segment("recognition_id", recognition_id)
    safe_field_id = _validate_segment("field_id", field_id)
    return _ensure_parent(
        settings.data_dir / "recognitions" / safe_recognition_id / "crops" / f"{safe_field_id}.png"
    )
