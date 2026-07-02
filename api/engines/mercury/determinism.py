"""
Winter AI - Mercury layer runtime (Python port)

The Mercury compiler isn't available via standard apt/Docker base images
Render can build from, so this is a faithful, line-for-line port of
engine.m's determinism_check/6 predicate — same thresholds, same branches —
executed natively instead of shelling out to a `mmc`-compiled binary.
See engine.m in this folder for the authoritative Mercury source.
"""

from __future__ import annotations


def determinism_check(top_score: float, second_score: float, confidence_min: float = 0.15) -> str:
    gap = top_score - second_score
    if gap < 0.05 and top_score > 0.0:
        return "ambiguous"
    if top_score < confidence_min:
        return "low_confidence"
    return "confident"
