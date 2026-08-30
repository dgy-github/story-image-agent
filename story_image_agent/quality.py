from __future__ import annotations

from typing import Any

IMAGE_THRESHOLDS = {
    "story_alignment": 0.80,
    "composition": 0.80,
    "identity_consistency": 0.85,
    "artifact_free": 0.85,
}


def assess_image_quality(metrics: dict[str, Any] | None) -> dict[str, Any]:
    supplied = dict(metrics or {})
    failures: list[dict[str, Any]] = []
    normalized: dict[str, float] = {}
    for name, threshold in IMAGE_THRESHOLDS.items():
        value = supplied.get(name)
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0 <= value <= 1:
            failures.append({"metric": name, "reason": "missing_or_invalid", "threshold": threshold})
            continue
        normalized[name] = float(value)
        if value < threshold:
            failures.append({"metric": name, "reason": "below_threshold", "threshold": threshold,
                             "actual": float(value)})
    retry_stage = None
    if failures:
        names = {failure["metric"] for failure in failures}
        retry_stage = "prompt_revision" if "identity_consistency" in names else "candidate_generation"
    return {"passed": not failures, "metrics": normalized, "failures": failures,
            "retry_stage": retry_stage}
