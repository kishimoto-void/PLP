"""
PLP Capsule Memory — Difference
================================
M3 Difference First

記憶は一致ではなく差異を観測する。
Difference は解釈しない。
"""

from __future__ import annotations

from typing import Any, Mapping
import math

from .types import (
    CapsuleDifference,
    ObservationDifference,
    DifferenceVelocity,
    MemoryDrift,
)


def _numeric_values(values: Mapping[str, Any]) -> dict[str, float]:
    out: dict[str, float] = {}
    for k, v in values.items():
        try:
            fv = float(v)
            if math.isfinite(fv):
                out[str(k)] = fv
        except (TypeError, ValueError):
            continue
    return out


def compare_observations(base_obs: Any, target_obs: Any) -> ObservationDifference:
    name = getattr(base_obs, "name", None) or getattr(target_obs, "name", "unknown")
    base_vals = _numeric_values(getattr(base_obs, "values", {}) or {})
    target_vals = _numeric_values(getattr(target_obs, "values", {}) or {})

    keys = set(base_vals) | set(target_vals)
    delta: dict[str, float] = {}
    for k in keys:
        b = base_vals.get(k)
        t = target_vals.get(k)
        if b is None or t is None:
            continue
        delta[k] = t - b

    if not delta and not base_vals and not target_vals:
        return ObservationDifference(
            name=str(name),
            delta={},
            norm=0.0,
            changed=False,
            confidence=0.0,
            missing_in_base=not bool(base_vals),
            missing_in_target=not bool(target_vals),
        )

    common = set(base_vals) & set(target_vals)
    union = set(base_vals) | set(target_vals)
    conf = (len(common) / len(union)) if union else 0.0
    norm = math.sqrt(sum(v * v for v in delta.values())) if delta else 0.0
    changed = norm > 1e-12

    return ObservationDifference(
        name=str(name),
        delta=delta,
        norm=float(norm),
        changed=changed,
        confidence=float(conf),
        missing_in_base=len(base_vals) == 0,
        missing_in_target=len(target_vals) == 0,
    )


def compare_capsules(base: Any, target: Any) -> CapsuleDifference:
    base_id = getattr(getattr(base, "header", None), "capsule_id", "") or ""
    target_id = getattr(getattr(target, "header", None), "capsule_id", "") or ""

    base_obs_list = list(getattr(base, "observations", []) or [])
    target_obs_list = list(getattr(target, "observations", []) or [])

    base_map = {getattr(o, "name", f"obs_{i}"): o for i, o in enumerate(base_obs_list)}
    target_map = {getattr(o, "name", f"obs_{i}"): o for i, o in enumerate(target_obs_list)}

    names = sorted(set(base_map) | set(target_map))
    diffs: list[ObservationDifference] = []

    for name in names:
        b = base_map.get(name)
        t = target_map.get(name)
        if b is not None and t is not None:
            diffs.append(compare_observations(b, t))
        elif b is not None:
            diffs.append(
                ObservationDifference(
                    name=name, delta={}, norm=0.0, changed=True, confidence=0.0,
                    missing_in_base=False, missing_in_target=True,
                )
            )
        else:
            diffs.append(
                ObservationDifference(
                    name=name, delta={}, norm=0.0, changed=True, confidence=0.0,
                    missing_in_base=True, missing_in_target=False,
                )
            )

    summary = float(sum(d.norm for d in diffs))
    base_clock = int(getattr(getattr(base, "header", None), "clock", 0) or 0)
    target_clock = int(getattr(getattr(target, "header", None), "clock", 0) or 0)
    base_seq = int(getattr(getattr(base, "header", None), "sequence", 0) or 0)
    target_seq = int(getattr(getattr(target, "header", None), "sequence", 0) or 0)

    return CapsuleDifference(
        base_capsule_id=str(base_id),
        target_capsule_id=str(target_id),
        observation_differences=tuple(diffs),
        summary_norm=summary,
        clock_delta=target_clock - base_clock,
        sequence_delta=target_seq - base_seq,
    )


def difference_velocity(diff_t: CapsuleDifference, diff_t1: CapsuleDifference) -> DifferenceVelocity:
    per: dict[str, float] = {}
    map_t = {d.name: d.norm for d in diff_t.observation_differences}
    map_t1 = {d.name: d.norm for d in diff_t1.observation_differences}
    for name in set(map_t) | set(map_t1):
        per[name] = map_t1.get(name, 0.0) - map_t.get(name, 0.0)
    return DifferenceVelocity(
        base_diff_summary=diff_t.summary_norm,
        target_diff_summary=diff_t1.summary_norm,
        velocity=diff_t1.summary_norm - diff_t.summary_norm,
        per_observation=per,
    )


def compute_drift(
    episode_id: str,
    capsule_id: str,
    reference: CapsuleDifference,
    current: CapsuleDifference,
) -> MemoryDrift:
    ref_map = {d.name: d.norm for d in reference.observation_differences}
    cur_map = {d.name: d.norm for d in current.observation_differences}
    scores: dict[str, float] = {}
    total = 0.0
    for name in set(ref_map) | set(cur_map):
        s = abs(cur_map.get(name, 0.0) - ref_map.get(name, 0.0))
        scores[name] = s
        total += s * s
    return MemoryDrift(
        episode_id=episode_id,
        capsule_id=capsule_id,
        drift_score=math.sqrt(total),
        observation_scores=scores,
    )
