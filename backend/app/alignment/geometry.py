"""边界框与仿射几何工具。"""

from __future__ import annotations

import numpy as np

from app.schemas.common import BBox


def bbox_iou(left: BBox, right: BBox) -> float:
    """计算两个边界框的交并比。"""
    x1 = max(left.x1, right.x1)
    y1 = max(left.y1, right.y1)
    x2 = min(left.x2, right.x2)
    y2 = min(left.y2, right.y2)

    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    if intersection == 0.0:
        return 0.0

    left_area = left.width() * left.height()
    right_area = right.width() * right.height()
    union = left_area + right_area - intersection
    if union <= 0.0:
        return 0.0
    return intersection / union


def bbox_distance(left: BBox, right: BBox) -> float:
    """计算两个边界框边缘之间的最短距离。"""
    dx = max(0.0, max(left.x1, right.x1) - min(left.x2, right.x2))
    dy = max(0.0, max(left.y1, right.y1) - min(left.y2, right.y2))
    return float(np.hypot(dx, dy))


def bbox_contains_point(bbox: BBox, point: tuple[float, float]) -> bool:
    """判断点是否落在边界框内部或边界上。"""
    x, y = point
    return bbox.x1 <= x <= bbox.x2 and bbox.y1 <= y <= bbox.y2


def _validate_affine_matrix(matrix: np.ndarray) -> np.ndarray:
    """验证仿射矩阵形状为 2x3。"""
    if matrix.shape != (2, 3):
        raise ValueError("matrix 必须是 2x3 仿射矩阵。")
    return matrix


def apply_affine_to_point(point: tuple[float, float], matrix: np.ndarray) -> tuple[float, float]:
    """使用 2x3 仿射矩阵变换一个点。"""
    valid_matrix = _validate_affine_matrix(matrix)
    x, y = point
    tx = valid_matrix[0, 0] * x + valid_matrix[0, 1] * y + valid_matrix[0, 2]
    ty = valid_matrix[1, 0] * x + valid_matrix[1, 1] * y + valid_matrix[1, 2]
    return (float(tx), float(ty))


def apply_affine_to_bbox(bbox: BBox, matrix: np.ndarray) -> BBox:
    """使用仿射矩阵变换边界框，并返回外接矩形。"""
    corners = [
        (bbox.x1, bbox.y1),
        (bbox.x2, bbox.y1),
        (bbox.x2, bbox.y2),
        (bbox.x1, bbox.y2),
    ]
    transformed = [apply_affine_to_point(corner, matrix) for corner in corners]
    xs = [point[0] for point in transformed]
    ys = [point[1] for point in transformed]
    return BBox(x1=min(xs), y1=min(ys), x2=max(xs), y2=max(ys))


def clamp_bbox_to_page(bbox: BBox, page_width: float, page_height: float) -> BBox:
    """将边界框限制在页面范围内。"""
    if page_width <= 0 or page_height <= 0:
        raise ValueError("page_width 和 page_height 必须为正数。")

    clamped = BBox(
        x1=max(0.0, min(bbox.x1, page_width)),
        y1=max(0.0, min(bbox.y1, page_height)),
        x2=max(0.0, min(bbox.x2, page_width)),
        y2=max(0.0, min(bbox.y2, page_height)),
    )
    if clamped.x2 <= clamped.x1 or clamped.y2 <= clamped.y1:
        raise ValueError("边界框完全落在页面外部，无法裁剪为有效区域。")
    return clamped
