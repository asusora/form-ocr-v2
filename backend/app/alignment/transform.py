"""锚点变换矩阵计算。"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

import numpy as np


@dataclass(frozen=True)
class AnchorMatch:
    """锚点匹配结果。"""

    template_point: tuple[float, float]
    target_point: tuple[float, float]
    score: float


def _translation_matrix(dx: float, dy: float) -> np.ndarray:
    """构造平移矩阵。"""
    return np.array([[1.0, 0.0, dx], [0.0, 1.0, dy]], dtype=float)


def _fit_affine_least_squares(matches: list[AnchorMatch]) -> np.ndarray | None:
    """用最小二乘拟合 2x3 仿射矩阵。"""
    if len(matches) < 3:
        return None

    system_rows: list[list[float]] = []
    targets: list[float] = []
    for match in matches:
        x, y = match.template_point
        tx, ty = match.target_point
        system_rows.append([x, y, 1.0, 0.0, 0.0, 0.0])
        system_rows.append([0.0, 0.0, 0.0, x, y, 1.0])
        targets.extend([tx, ty])

    coefficients = np.array(system_rows, dtype=float)
    values = np.array(targets, dtype=float)
    solution, _residuals, rank, _singular_values = np.linalg.lstsq(
        coefficients,
        values,
        rcond=None,
    )
    if rank < 6:
        return None

    return np.array(
        [[solution[0], solution[1], solution[2]], [solution[3], solution[4], solution[5]]],
        dtype=float,
    )


def _similarity_matrix_from_two_matches(matches: list[AnchorMatch]) -> np.ndarray:
    """根据两个点计算相似变换矩阵。"""
    first_match, second_match = matches
    source_first = np.array(first_match.template_point, dtype=float)
    source_second = np.array(second_match.template_point, dtype=float)
    target_first = np.array(first_match.target_point, dtype=float)
    target_second = np.array(second_match.target_point, dtype=float)

    source_vector = source_second - source_first
    target_vector = target_second - target_first
    source_length = float(np.linalg.norm(source_vector))
    target_length = float(np.linalg.norm(target_vector))

    if source_length == 0.0 or target_length == 0.0:
        delta_x, delta_y = target_first - source_first
        return _translation_matrix(float(delta_x), float(delta_y))

    scale = target_length / source_length
    cos_theta = float(np.dot(source_vector, target_vector) / (source_length * target_length))
    sin_theta = float(
        (source_vector[0] * target_vector[1] - source_vector[1] * target_vector[0])
        / (source_length * target_length)
    )
    rotation_scale = scale * np.array([[cos_theta, -sin_theta], [sin_theta, cos_theta]])
    translation = target_first - rotation_scale @ source_first

    return np.array(
        [
            [rotation_scale[0, 0], rotation_scale[0, 1], translation[0]],
            [rotation_scale[1, 0], rotation_scale[1, 1], translation[1]],
        ],
        dtype=float,
    )


def _projection_errors(matrix: np.ndarray, matches: list[AnchorMatch]) -> np.ndarray:
    """计算矩阵对所有匹配点的投影误差。"""
    source_points = np.array([match.template_point for match in matches], dtype=float)
    target_points = np.array([match.target_point for match in matches], dtype=float)
    homogeneous_points = np.concatenate(
        [source_points, np.ones((len(source_points), 1), dtype=float)],
        axis=1,
    )
    predicted_points = homogeneous_points @ matrix.T
    return np.linalg.norm(predicted_points - target_points, axis=1)


def _compute_affine_with_ransac(
    matches: list[AnchorMatch],
    ransac_threshold: float = 5.0,
    max_pool_size: int = 12,
) -> np.ndarray | None:
    """对三点及以上的匹配结果做仿射拟合，并使用简单 RANSAC 剔除离群点。"""
    if len(matches) == 3:
        return _fit_affine_least_squares(matches)

    sorted_matches = sorted(matches, key=lambda match: match.score, reverse=True)
    candidate_pool = sorted_matches[:max_pool_size]

    best_inliers: list[AnchorMatch] = []
    best_mean_error = float("inf")
    for subset in combinations(candidate_pool, 3):
        candidate_matrix = _fit_affine_least_squares(list(subset))
        if candidate_matrix is None:
            continue

        errors = _projection_errors(candidate_matrix, matches)
        inliers = [match for match, error in zip(matches, errors, strict=True) if error <= ransac_threshold]
        if len(inliers) < 3:
            continue

        mean_error = float(np.mean([error for error in errors if error <= ransac_threshold]))
        if len(inliers) > len(best_inliers):
            best_inliers = inliers
            best_mean_error = mean_error
            continue
        if len(inliers) == len(best_inliers) and mean_error < best_mean_error:
            best_inliers = inliers
            best_mean_error = mean_error

    if best_inliers:
        refined_matrix = _fit_affine_least_squares(best_inliers)
        if refined_matrix is not None:
            return refined_matrix

    return _fit_affine_least_squares(matches)


def compute_transform(matches: list[AnchorMatch]) -> np.ndarray | None:
    """根据匹配数量计算变换矩阵。

    Args:
        matches: 模板点到目标点的匹配结果。

    Returns:
        `2x3` 仿射矩阵；没有可用匹配时返回 `None`。
    """

    if not matches:
        return None

    if len(matches) == 1:
        template_x, template_y = matches[0].template_point
        target_x, target_y = matches[0].target_point
        return _translation_matrix(target_x - template_x, target_y - template_y)

    if len(matches) == 2:
        return _similarity_matrix_from_two_matches(matches)

    return _compute_affine_with_ransac(matches)
