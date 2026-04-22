"""页级对齐主入口。"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

from app.alignment.geometry import apply_affine_to_bbox, clamp_bbox_to_page
from app.alignment.matching import build_candidate_pairs, finalize_anchor_matches
from app.alignment.transform import AnchorMatch, compute_transform
from app.schemas.common import Anchor, BBox, TextBlock

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PageAlignmentResult:
    """单页字段对齐结果。"""

    fields: list[tuple[BBox, str]]
    global_matrix: np.ndarray | None
    anchor_matches: list[AnchorMatch]


def _select_nearest(matches: list[AnchorMatch], field_bbox: BBox, k: int = 3) -> list[AnchorMatch]:
    """选出模板坐标上距离字段中心最近的若干锚点匹配。"""
    if k <= 0:
        return []

    field_center_x, field_center_y = field_bbox.center()
    return sorted(
        matches,
        key=lambda match: (match.template_point[0] - field_center_x) ** 2
        + (match.template_point[1] - field_center_y) ** 2,
    )[:k]


def _apply_matrix_or_fail(
    field_bbox: BBox,
    matrix: np.ndarray,
    page_width: float,
    page_height: float,
) -> BBox | None:
    """应用仿射矩阵，结果完全落在页面外时返回 None 表示对齐失败。

    旧实现会在越界时调用 `_fit_bbox_into_page` 把框平移回页内，结果是
    把明显错误的变换伪装成成功对齐（字段被钉到页面角上却标成 auto）。
    这里让调用方拿到 None 后显式改写为 `alignment_failed`，方便暴露问题。
    """
    transformed_bbox = apply_affine_to_bbox(field_bbox, matrix)
    try:
        return clamp_bbox_to_page(transformed_bbox, page_width, page_height)
    except ValueError:
        return None


def align_page(
    page_fields: list[tuple[BBox, list[Anchor]]],
    target_blocks: list[TextBlock],
    page_width: float,
    page_height: float,
) -> PageAlignmentResult:
    """对单页所有字段执行页级粗对齐与字段级局部对齐。

    Args:
        page_fields: 每个字段的模板 bbox 与其锚点列表。
        target_blocks: 目标页 OCR 文本块。
        page_width: 目标页宽度。
        page_height: 目标页高度。

    Returns:
        对齐后的字段 bbox、全局矩阵以及最终锚点匹配结果。
    """

    all_anchors: list[Anchor] = []
    for _field_bbox, anchors in page_fields:
        all_anchors.extend(anchors)

    if not all_anchors:
        logger.warning(
            "页对齐跳过：模板页没有可用锚点（fields=%d target_blocks=%d）",
            len(page_fields),
            len(target_blocks),
        )
        return PageAlignmentResult(
            fields=[(field_bbox, "alignment_failed") for field_bbox, _anchors in page_fields],
            global_matrix=None,
            anchor_matches=[],
        )

    candidate_pairs = build_candidate_pairs(all_anchors, target_blocks)
    if not candidate_pairs:
        logger.warning(
            "对齐失败：%d 个锚点都没有拿到任何候选匹配（target_blocks=%d）",
            len(all_anchors),
            len(target_blocks),
        )
        return PageAlignmentResult(
            fields=[(field_bbox, "alignment_failed") for field_bbox, _anchors in page_fields],
            global_matrix=None,
            anchor_matches=[],
        )

    coarse_matches = [
        AnchorMatch(
            template_point=pair.template_point,
            target_point=pair.target_point,
            score=pair.score,
        )
        for pair in candidate_pairs
    ]
    coarse_global_matrix = compute_transform(coarse_matches)

    finalized_matches = finalize_anchor_matches(candidate_pairs, coarse_global_matrix)
    global_matrix = compute_transform(finalized_matches)
    if global_matrix is None:
        global_matrix = coarse_global_matrix

    logger.info(
        "页对齐矩阵：anchors=%d candidate_pairs=%d finalized_matches=%d "
        "global_matrix=%s",
        len(all_anchors),
        len(candidate_pairs),
        len(finalized_matches),
        None if global_matrix is None else global_matrix.round(3).tolist(),
    )

    aligned_fields: list[tuple[BBox, str]] = []
    failed_count = 0
    for field_bbox, _anchors in page_fields:
        nearest_matches = _select_nearest(finalized_matches, field_bbox, k=3)
        local_matrix = compute_transform(nearest_matches) if len(nearest_matches) >= 2 else None

        aligned_bbox: BBox | None = None
        if local_matrix is not None:
            aligned_bbox = _apply_matrix_or_fail(
                field_bbox, local_matrix, page_width, page_height
            )
        if aligned_bbox is None and global_matrix is not None:
            aligned_bbox = _apply_matrix_or_fail(
                field_bbox, global_matrix, page_width, page_height
            )

        if aligned_bbox is not None:
            aligned_fields.append((aligned_bbox, "auto"))
        else:
            aligned_fields.append((field_bbox, "alignment_failed"))
            failed_count += 1

    if failed_count:
        logger.warning(
            "页对齐：%d/%d 个字段标记为 alignment_failed（保留模板原 bbox 供人工调整）",
            failed_count,
            len(page_fields),
        )

    return PageAlignmentResult(
        fields=aligned_fields,
        global_matrix=global_matrix,
        anchor_matches=finalized_matches,
    )
