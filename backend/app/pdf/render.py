"""PDF 渲染工具。"""

from __future__ import annotations

from pathlib import Path

import fitz
import numpy as np
from PIL import Image


def _normalize_pdf_path(pdf_path: str | Path) -> Path:
    """规范化 PDF 路径并校验文件存在。"""
    normalized_path = Path(pdf_path)
    if not normalized_path.exists():
        raise FileNotFoundError(f"PDF 文件不存在: {normalized_path}")
    if not normalized_path.is_file():
        raise ValueError(f"PDF 路径不是文件: {normalized_path}")
    return normalized_path


def _validate_dpi(dpi: int) -> int:
    """校验 DPI 必须为正整数。"""
    if dpi <= 0:
        raise ValueError("dpi 必须大于 0。")
    return dpi


def _open_document(pdf_path: Path) -> fitz.Document:
    """打开 PDF 文档并在失败时抛出明确异常。"""
    try:
        return fitz.open(str(pdf_path))
    except Exception as exc:  # pragma: no cover - 依赖底层库异常类型
        raise ValueError(f"无法打开 PDF 文件: {pdf_path}") from exc


def count_pages(pdf_path: str | Path) -> int:
    """返回 PDF 页数。

    Args:
        pdf_path: PDF 文件路径。

    Returns:
        PDF 的总页数。

    Raises:
        FileNotFoundError: PDF 文件不存在。
        ValueError: PDF 无法打开或路径非法。
    """

    normalized_path = _normalize_pdf_path(pdf_path)
    document = _open_document(normalized_path)
    try:
        return int(document.page_count)
    finally:
        document.close()


def render_pdf_to_images(pdf_path: str | Path, out_dir: str | Path, dpi: int = 200) -> list[Path]:
    """把 PDF 每一页渲染为 PNG 文件。

    Args:
        pdf_path: PDF 文件路径。
        out_dir: 输出目录。
        dpi: 渲染分辨率。

    Returns:
        按页码顺序返回生成的 PNG 路径列表，文件名从 `1.png` 开始。

    Raises:
        FileNotFoundError: PDF 文件不存在。
        ValueError: 路径非法、PDF 无法打开或 DPI 非法。
    """

    normalized_path = _normalize_pdf_path(pdf_path)
    validated_dpi = _validate_dpi(dpi)
    output_dir = Path(out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    zoom_ratio = validated_dpi / 72.0
    render_matrix = fitz.Matrix(zoom_ratio, zoom_ratio)

    document = _open_document(normalized_path)
    try:
        rendered_paths: list[Path] = []
        for page_index in range(document.page_count):
            pixmap = document.load_page(page_index).get_pixmap(matrix=render_matrix, alpha=False)
            target_path = output_dir / f"{page_index + 1}.png"
            pixmap.save(str(target_path))
            rendered_paths.append(target_path)
        return rendered_paths
    finally:
        document.close()


def render_page_to_array(pdf_path: str | Path, page: int, dpi: int = 200) -> np.ndarray:
    """把单页 PDF 渲染为 RGB numpy 数组。

    Args:
        pdf_path: PDF 文件路径。
        page: 页码，从 1 开始。
        dpi: 渲染分辨率。

    Returns:
        `shape=(H, W, 3)` 的 RGB 数组。

    Raises:
        FileNotFoundError: PDF 文件不存在。
        ValueError: 页码非法、PDF 无法打开或 DPI 非法。
    """

    if page < 1:
        raise ValueError("page 必须大于或等于 1。")

    normalized_path = _normalize_pdf_path(pdf_path)
    validated_dpi = _validate_dpi(dpi)
    zoom_ratio = validated_dpi / 72.0
    render_matrix = fitz.Matrix(zoom_ratio, zoom_ratio)

    document = _open_document(normalized_path)
    try:
        if page > document.page_count:
            raise ValueError(f"page 超出范围: {page} > {document.page_count}")
        pixmap = document.load_page(page - 1).get_pixmap(matrix=render_matrix, alpha=False)
        image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
        return np.asarray(image, dtype=np.uint8)
    finally:
        document.close()
