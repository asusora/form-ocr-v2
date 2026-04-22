"""对齐算法模块导出。"""

from app.alignment.aligner import PageAlignmentResult, align_page
from app.alignment.anchors import extract_anchors_for_field, pick_diverse_anchors
from app.alignment.geometry import (
    apply_affine_to_bbox,
    apply_affine_to_point,
    bbox_contains_point,
    bbox_distance,
    bbox_iou,
    clamp_bbox_to_page,
)
from app.alignment.matching import CandidatePair, build_candidate_pairs, finalize_anchor_matches
from app.alignment.transform import AnchorMatch, compute_transform

__all__ = [
    "bbox_iou",
    "bbox_distance",
    "bbox_contains_point",
    "apply_affine_to_point",
    "apply_affine_to_bbox",
    "clamp_bbox_to_page",
    "extract_anchors_for_field",
    "pick_diverse_anchors",
    "AnchorMatch",
    "compute_transform",
    "CandidatePair",
    "build_candidate_pairs",
    "finalize_anchor_matches",
    "PageAlignmentResult",
    "align_page",
]
