"""锚点自动提取算法。"""

from __future__ import annotations

from app.alignment.geometry import bbox_distance, bbox_iou
from app.schemas.common import Anchor, BBox, TextBlock


def _quadrant(field_bbox: BBox, block_bbox: BBox) -> str:
    """根据候选块相对字段中心的位置返回方位象限。"""
    field_center_x, field_center_y = field_bbox.center()
    block_center_x, block_center_y = block_bbox.center()
    delta_x = block_center_x - field_center_x
    delta_y = block_center_y - field_center_y

    if abs(delta_x) > abs(delta_y):
        return "left" if delta_x < 0 else "right"
    return "above" if delta_y < 0 else "below"


def _is_valid_candidate(block: TextBlock, all_field_bboxes: list[BBox]) -> bool:
    """判断文本块是否可以作为锚点候选。"""
    normalized_text = block.text.strip()
    if len(normalized_text) < 2:
        return False
    if normalized_text.isdigit():
        return False
    return all(bbox_iou(block.bbox, field_bbox) <= 0.3 for field_bbox in all_field_bboxes)


def pick_diverse_anchors(
    candidates: list[tuple[float, TextBlock]],
    field_bbox: BBox,
    n: int,
) -> list[TextBlock]:
    """从已排序候选中优先选择方位分散的锚点。"""
    if n <= 0:
        return []

    picked_by_quadrant: dict[str, TextBlock] = {}
    for _distance, block in candidates:
        quadrant = _quadrant(field_bbox, block.bbox)
        if quadrant not in picked_by_quadrant:
            picked_by_quadrant[quadrant] = block
        if len(picked_by_quadrant) >= n:
            break

    picked_blocks = list(picked_by_quadrant.values())
    if len(picked_blocks) >= n:
        return picked_blocks[:n]

    for _distance, block in candidates:
        if block not in picked_blocks:
            picked_blocks.append(block)
        if len(picked_blocks) >= n:
            break

    return picked_blocks


def extract_anchors_for_field(
    field_bbox: BBox,
    page_blocks: list[TextBlock],
    all_field_bboxes: list[BBox],
    n: int = 3,
) -> list[Anchor]:
    """为单个字段自动提取锚点列表。

    Args:
        field_bbox: 当前字段的模板坐标。
        page_blocks: 当前页整页 OCR 文本块。
        all_field_bboxes: 当前页所有字段框，用于排除变量内容。
        n: 期望提取的锚点数量。

    Returns:
        最多 `n` 个锚点，优先保证方位分散。
    """

    if n <= 0:
        return []

    candidates: list[tuple[float, TextBlock]] = []
    for block in page_blocks:
        if not _is_valid_candidate(block, all_field_bboxes):
            continue
        distance = bbox_distance(block.bbox, field_bbox)
        candidates.append((distance, block))

    candidates.sort(key=lambda item: item[0])
    picked_blocks = pick_diverse_anchors(candidates, field_bbox, n)

    field_center_x, field_center_y = field_bbox.center()
    anchors: list[Anchor] = []
    for block in picked_blocks:
        block_center_x, block_center_y = block.bbox.center()
        anchors.append(
            Anchor(
                text=block.text.strip(),
                template_bbox=block.bbox,
                offset_from_field=(
                    block_center_x - field_center_x,
                    block_center_y - field_center_y,
                ),
            )
        )

    return anchors
