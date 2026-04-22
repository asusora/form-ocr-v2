"""PaddleOCR 引擎实现。"""

from __future__ import annotations

import os
from typing import Any

import numpy as np

# PaddlePaddle 3.x 的 PIR 执行器在 oneDNN 指令上缺少
# pir::ArrayAttribute<pir::DoubleAttribute> 的属性转换，会导致
# PaddleOCR 文本检测模型在 CPU 推理时抛 NotImplementedError。
# 切回旧版执行器即可绕过，oneDNN 加速仍然保留。
os.environ.setdefault("FLAGS_enable_pir_in_executor", "0")

from app.ocr.base import textblock_from_quad
from app.schemas.common import TextBlock

try:  # pragma: no cover - 依赖是否安装由运行环境决定
    from paddleocr import PaddleOCR
except ImportError:  # pragma: no cover - 本地静态检查环境可能未安装依赖
    PaddleOCR = None  # type: ignore[assignment]


def _looks_like_result_item(item: object) -> bool:
    """判断对象是否符合 PaddleOCR 2.x 单条识别结果结构。"""
    return isinstance(item, (list, tuple)) and len(item) == 2


def _extract_v3_payload(result_item: object) -> dict[str, Any] | None:
    """提取 PaddleOCR 3.x 结果对象中的标准字典载荷。"""
    if isinstance(result_item, dict):
        nested_payload = result_item.get("res")
        if isinstance(nested_payload, dict):
            return nested_payload
        return result_item

    nested_payload = getattr(result_item, "res", None)
    if isinstance(nested_payload, dict):
        return nested_payload

    return None


def _extract_v3_result_items(result_item: object) -> list[tuple[Any, Any]]:
    """从 PaddleOCR 3.x 结果对象中提取框、文本和置信度。"""
    payload = _extract_v3_payload(result_item)
    if payload is None:
        return []

    polygons = payload.get("rec_polys")
    if polygons is None:
        polygons = payload.get("dt_polys")

    texts = payload.get("rec_texts")
    scores = payload.get("rec_scores")
    if polygons is None or texts is None:
        return []

    polygon_list = list(polygons)
    text_list = list(texts)
    score_list = [0.0] * len(text_list) if scores is None else list(scores)

    return [
        (polygon, (text, float(score)))
        for polygon, text, score in zip(polygon_list, text_list, score_list)
    ]


def _extract_result_items(raw_result: Any) -> list[tuple[Any, Any]]:
    """兼容 PaddleOCR 2.x 与 3.x 的常见返回结果结构。"""
    if not raw_result:
        return []

    result_items = raw_result if isinstance(raw_result, list) else [raw_result]
    extracted_items: list[tuple[Any, Any]] = []

    for result_item in result_items:
        if _looks_like_result_item(result_item):
            extracted_items.append(result_item)
            continue

        if isinstance(result_item, list):
            extracted_items.extend(
                item for item in result_item if _looks_like_result_item(item)
            )
            continue

        extracted_items.extend(_extract_v3_result_items(result_item))

    return extracted_items


def _normalize_init_runtime_error(exc: RuntimeError) -> RuntimeError:
    """把底层 SDK 的运行时依赖异常转换为更明确的错误。"""
    message = str(exc)
    lowered_message = message.lower()
    if "paddlepaddle" in lowered_message and "not installed" in lowered_message:
        return RuntimeError(
            "未安装 PaddlePaddle 运行时依赖，无法初始化 PaddleOCR。"
            "请先安装 `paddlepaddle>=3.0.0`，再重新启动后端服务。"
        )
    return exc


class PaddleOcrEngine:
    """基于 PaddleOCR 的 OCR 引擎实现。"""

    def __init__(self, lang: str = "ch", use_gpu: bool = False) -> None:
        """初始化 PaddleOCR 实例。

        Args:
            lang: PaddleOCR 语言包标识。
            use_gpu: 是否启用 GPU。

        Raises:
            RuntimeError: 当前环境未安装 `paddleocr`。
        """
        if PaddleOCR is None:
            raise RuntimeError("未安装 paddleocr 依赖，无法初始化 PaddleOcrEngine。")

        modern_kwargs = {
            "use_angle_cls": True,
            "lang": lang,
            "device": "gpu:0" if use_gpu else "cpu",
        }
        legacy_kwargs = {
            "use_angle_cls": True,
            "lang": lang,
            "use_gpu": use_gpu,
            "show_log": False,
        }

        try:
            self._ocr = PaddleOCR(**modern_kwargs)
        except TypeError:
            self._ocr = PaddleOCR(**legacy_kwargs)
        except RuntimeError as exc:
            raise _normalize_init_runtime_error(exc) from exc

    def recognize(self, image: np.ndarray) -> list[TextBlock]:
        """执行整页 OCR 并返回文本块列表。

        Args:
            image: `shape=(H, W, 3)` 的 RGB numpy 数组。

        Returns:
            识别出的文本块列表。

        Raises:
            ValueError: 输入图像不是 RGB 三通道数组。
        """
        if image.ndim != 3 or image.shape[2] != 3:
            raise ValueError("image 必须是 shape=(H, W, 3) 的 RGB 数组。")

        raw_result = self._ocr.ocr(image)
        items = _extract_result_items(raw_result)
        blocks: list[TextBlock] = []

        for item in items:
            quad, text_payload = item
            try:
                text, score = text_payload
            except (TypeError, ValueError):
                continue

            normalized_text = str(text).strip()
            if not normalized_text:
                continue

            try:
                blocks.append(textblock_from_quad(normalized_text, quad, float(score)))
            except (TypeError, ValueError):
                continue

        return blocks
