"""单选项字段抽取器。"""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any

import cv2
import numpy as np

from app.extractors.base import ExtractContext, blocks_in_bbox, crop_image
from app.extractors.registry import register
from app.ocr import get_engine as get_ocr_engine
from app.schemas.common import BBox, ExtractResult, TextBlock

try:  # pragma: no cover - 依赖是否安装由运行环境决定
    from rapidfuzz import fuzz, process
except ImportError:  # pragma: no cover - 静态环境下允许降级
    class _FallbackFuzz:
        """rapidfuzz 缺失时的简化兼容实现。"""

        @staticmethod
        def ratio(left: str, right: str) -> int:
            """返回 0-100 的字符串相似度。"""
            return int(round(SequenceMatcher(None, left, right).ratio() * 100))

    class _FallbackProcess:
        """rapidfuzz.process 的简化兼容实现。"""

        @staticmethod
        def extractOne(query: str, choices: list[str], scorer) -> tuple[str, int, int] | None:
            """返回最佳匹配项。"""
            if not choices:
                return None
            scored = [(choice, int(scorer(query, choice)), index) for index, choice in enumerate(choices)]
            scored.sort(key=lambda item: item[1], reverse=True)
            return scored[0]

    fuzz = _FallbackFuzz()
    process = _FallbackProcess()


def _normalize_options(config: dict[str, Any]) -> list[dict[str, Any]]:
    """把配置中的选项定义统一转为字典。"""
    normalized: list[dict[str, Any]] = []
    for option in config.get("options") or []:
        if hasattr(option, "model_dump"):
            normalized.append(option.model_dump())
            continue
        if isinstance(option, dict):
            normalized.append(option)
    return normalized


def _match_option_value(text: str, options: list[dict[str, Any]], threshold: int = 80) -> str | None:
    """根据文本内容模糊匹配单选项值。"""
    normalized = text.strip()
    if not normalized:
        return None

    best_value: str | None = None
    best_score = 0
    for option in options:
        labels = [str(label).strip() for label in option.get("labels") or [] if str(label).strip()]
        for label in labels:
            score = int(fuzz.ratio(normalized, label))
            if score >= threshold and score > best_score:
                best_score = score
                best_value = str(option.get("value"))
    return best_value


def _locate_option_blocks(
    blocks: list[TextBlock],
    bbox: BBox,
    options: list[dict[str, Any]],
) -> dict[str, TextBlock]:
    """在字段框内定位每个选项对应的 OCR 文本块。"""
    in_scope = blocks_in_bbox(blocks, bbox)
    located: dict[str, TextBlock] = {}
    for option in options:
        value = str(option.get("value"))
        labels = [str(label).strip() for label in option.get("labels") or [] if str(label).strip()]
        best_block: TextBlock | None = None
        best_score = 0
        for label in labels:
            for block in in_scope:
                score = int(fuzz.ratio(label, block.text.strip()))
                if score >= 75 and score > best_score:
                    best_score = score
                    best_block = block
        if best_block is not None:
            located[value] = best_block
    return located


def _detect_by_circle(image: np.ndarray, bbox: BBox, located: dict[str, TextBlock]) -> str | None:
    """通过圆圈检测识别被圈中的选项。"""
    crop = crop_image(image, bbox)
    if crop.size == 0 or not located:
        return None

    gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
    circles = cv2.HoughCircles(
        gray,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=18,
        param1=80,
        param2=18,
        minRadius=6,
        maxRadius=max(12, int(max(crop.shape[:2]) * 0.3)),
    )
    if circles is None:
        return None

    for center_x, center_y, radius in circles[0]:
        page_x = float(center_x + bbox.x1)
        page_y = float(center_y + bbox.y1)
        for value, block in located.items():
            block_center_x, block_center_y = block.bbox.center()
            if (block_center_x - page_x) ** 2 + (block_center_y - page_y) ** 2 <= (radius * 1.5) ** 2:
                return value
    return None


def _detect_struck_values(image: np.ndarray, bbox: BBox, located: dict[str, TextBlock]) -> set[str]:
    """检测被水平线划掉的选项值集合。"""
    crop = crop_image(image, bbox)
    if crop.size == 0 or not located:
        return set()

    gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    lines = cv2.HoughLinesP(
        edges,
        1,
        np.pi / 180,
        threshold=40,
        minLineLength=max(20, crop.shape[1] // 5),
        maxLineGap=5,
    )
    if lines is None:
        return set()

    struck_values: set[str] = set()
    for raw_line in lines[:, 0]:
        x1, y1, x2, y2 = map(float, raw_line)
        if abs(y2 - y1) > 4:
            continue
        line_y = (y1 + y2) / 2 + bbox.y1
        line_left = min(x1, x2) + bbox.x1
        line_right = max(x1, x2) + bbox.x1
        for value, block in located.items():
            block_center_y = (block.bbox.y1 + block.bbox.y2) / 2
            if abs(block_center_y - line_y) > max(6.0, block.bbox.height()):
                continue
            if line_left <= block.bbox.x2 and line_right >= block.bbox.x1:
                struck_values.add(value)
    return struck_values


def _read_local_ocr_texts(image: np.ndarray, bbox: BBox) -> list[str]:
    """对字段局部图像做 OCR 并返回文本列表。"""
    crop = crop_image(image, bbox)
    if crop.size == 0:
        return []
    try:
        blocks = get_ocr_engine().recognize(crop)
    except Exception:
        return []
    return [block.text.strip() for block in blocks if block.text.strip()]


class OptionSelectExtractor:
    """单选项字段三级抽取器。"""

    field_type = "option_select"

    def extract(self, image: np.ndarray, bbox: BBox, context: ExtractContext) -> ExtractResult:
        """按圈选、划除、手写匹配三层策略识别选项。"""
        options = _normalize_options(context.field_config)
        if not options:
            return ExtractResult(raw_value=None, confidence=0.0)

        source_image = context.page_image if context.page_image is not None else image
        located = _locate_option_blocks(context.page_blocks, bbox, options)

        circle_value = _detect_by_circle(source_image, bbox, located)
        if circle_value is not None:
            return ExtractResult(raw_value=circle_value, confidence=0.9)

        struck_values = _detect_struck_values(source_image, bbox, located)
        remaining_values = [value for value in located.keys() if value not in struck_values]
        if len(remaining_values) == 1:
            return ExtractResult(raw_value=remaining_values[0], confidence=0.75)

        local_texts = [block.text.strip() for block in blocks_in_bbox(context.page_blocks, bbox) if block.text.strip()]
        if not local_texts:
            local_texts = _read_local_ocr_texts(source_image, bbox)

        best_value: str | None = None
        best_score = 0
        for option in options:
            for label in option.get("labels") or []:
                label_text = str(label).strip()
                if not label_text:
                    continue
                match = process.extractOne(label_text, local_texts, scorer=fuzz.ratio)
                if match is None:
                    continue
                _matched_text, score, _index = match
                if score >= 80 and score > best_score:
                    best_score = int(score)
                    best_value = str(option.get("value"))
        if best_value is not None:
            return ExtractResult(raw_value=best_value, confidence=min(1.0, best_score / 100.0))

        return ExtractResult(raw_value=None, confidence=0.0)


register(OptionSelectExtractor())
