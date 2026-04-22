"""锚点候选匹配与页级消歧。"""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher

import numpy as np

from app.alignment.geometry import apply_affine_to_point
from app.alignment.transform import AnchorMatch
from app.schemas.common import Anchor, TextBlock

try:  # pragma: no cover - 依赖是否安装由运行环境决定
    from rapidfuzz import fuzz, process
except ImportError:  # pragma: no cover - 本地静态检查环境可能未安装依赖
    class _FallbackFuzz:
        """rapidfuzz 缺失时的简化兼容实现。"""

        @staticmethod
        def ratio(left: str, right: str) -> int:
            """返回 0-100 的相似度分数。"""
            return int(round(SequenceMatcher(None, left, right).ratio() * 100))

    class _FallbackProcess:
        """rapidfuzz.process 的简化兼容实现。"""

        @staticmethod
        def extract(
            query: str,
            choices: list[str],
            scorer,
            limit: int,
        ) -> list[tuple[str, int, int]]:
            """返回按得分排序的前若干候选。"""
            scored = [
                (choice, int(scorer(query, choice)), index)
                for index, choice in enumerate(choices)
            ]
            scored.sort(key=lambda item: item[1], reverse=True)
            return scored[:limit]

    fuzz = _FallbackFuzz()
    process = _FallbackProcess()


@dataclass(frozen=True)
class CandidatePair:
    """锚点到目标文本块的候选匹配。"""

    anchor_index: int
    anchor_text: str
    template_point: tuple[float, float]
    target_point: tuple[float, float]
    score: float


def build_candidate_pairs(
    anchors: list[Anchor],
    target_blocks: list[TextBlock],
    score_threshold: float = 60,
    top_k: int = 3,
) -> list[CandidatePair]:
    """为每个锚点构造目标页上的 top-k 模糊匹配候选。"""
    if not anchors or not target_blocks or top_k <= 0:
        return []

    target_texts = [block.text for block in target_blocks]
    pairs: list[CandidatePair] = []

    for anchor_index, anchor in enumerate(anchors):
        matched_items = process.extract(
            anchor.text,
            target_texts,
            scorer=fuzz.ratio,
            limit=top_k,
        )
        template_center = anchor.template_bbox.center()
        for _text, score, matched_index in matched_items:
            if score < score_threshold:
                continue
            block_center = target_blocks[matched_index].bbox.center()
            pairs.append(
                CandidatePair(
                    anchor_index=anchor_index,
                    anchor_text=anchor.text,
                    template_point=template_center,
                    target_point=block_center,
                    score=float(score),
                )
            )

    return pairs


def finalize_anchor_matches(
    candidates: list[CandidatePair],
    global_matrix: np.ndarray | None,
    direct_score_threshold: float = 70,
) -> list[AnchorMatch]:
    """将每个锚点的多个候选收敛为唯一匹配。"""
    grouped_candidates: dict[int, list[CandidatePair]] = {}
    for candidate in candidates:
        grouped_candidates.setdefault(candidate.anchor_index, []).append(candidate)

    matches: list[AnchorMatch] = []
    for group in grouped_candidates.values():
        chosen_candidate: CandidatePair | None = None

        if global_matrix is not None:
            predicted_point = apply_affine_to_point(group[0].template_point, global_matrix)
            chosen_candidate = min(
                group,
                key=lambda item: (
                    (item.target_point[0] - predicted_point[0]) ** 2
                    + (item.target_point[1] - predicted_point[1]) ** 2,
                    -item.score,
                ),
            )
        else:
            highest_score_candidate = max(group, key=lambda item: item.score)
            if highest_score_candidate.score >= direct_score_threshold:
                chosen_candidate = highest_score_candidate

        if chosen_candidate is None:
            continue

        matches.append(
            AnchorMatch(
                template_point=chosen_candidate.template_point,
                target_point=chosen_candidate.target_point,
                score=chosen_candidate.score,
            )
        )

    return matches
