"""
scoring_engine.py — Rule-based relevance scoring for competitor diff changes.

Scores each change on three dimensions without any API calls:

  signal_weight  — how strategically important is this type of change?
                   Pricing=10, Positioning=9, Reviews=8, Features=7,
                   Hero=7, Messaging=6, CTAs=6, Social Proof=5

  magnitude      — how much changed? Scaled by number of items added/removed.
                   Capped at 1.0 to keep scores comparable.

  composite      — weighted average of signal_weight (60%) + magnitude (40%),
                   rounded to one decimal place on a 1–10 scale.

The composite score lets teams filter the diff by importance and focus on
the highest-signal changes first.
"""

from typing import Dict, Any, List

# ── Signal type weights (1–10) ────────────────────────────────────────────────

_SIGNAL_WEIGHTS: Dict[str, float] = {
    "Pricing":         10.0,
    "Positioning":      9.0,
    "G2 Rating":        8.0,
    "Trustpilot Score": 8.0,
    "Features":         7.0,
    "Hero Content":     7.0,
    "Messaging":        6.0,
    "CTAs":             6.0,
    "Social Proof":     5.0,
    "new_competitor":   9.0,   # discovering a new competitor is high-value
}

_DEFAULT_WEIGHT = 5.0


def _magnitude_score(added: List[str], removed: List[str]) -> float:
    """
    Score magnitude of a change on 0–1 scale.
    1 item changed → 0.3  |  3 items → 0.6  |  5+ items → 1.0
    """
    total = len(added) + len(removed)
    if total == 0:
        return 0.1   # change was detected but lists were empty (e.g. text change)
    return min(1.0, total / 5.0)


def score_change(change: Dict[str, Any]) -> Dict[str, Any]:
    """
    Attach scoring fields to a single diff change dict.

    Adds:
      signal_weight  (float 1–10)
      magnitude      (float 0–1, descriptive)
      composite      (float 1–10)
      priority       ('critical' | 'high' | 'medium' | 'low')
    """
    category = change.get("category", change.get("type", ""))
    added    = change.get("added", [])
    removed  = change.get("removed", [])

    signal_weight = _SIGNAL_WEIGHTS.get(category, _DEFAULT_WEIGHT)
    magnitude     = _magnitude_score(added, removed)

    # Composite: 60% signal importance + 40% magnitude (normalised to 10)
    composite = round(signal_weight * 0.6 + magnitude * 10 * 0.4, 1)
    composite = max(1.0, min(10.0, composite))

    if composite >= 8.5:
        priority = "critical"
    elif composite >= 6.5:
        priority = "high"
    elif composite >= 4.5:
        priority = "medium"
    else:
        priority = "low"

    return {
        **change,
        "signal_weight": signal_weight,
        "magnitude":     round(magnitude, 2),
        "composite":     composite,
        "priority":      priority,
    }


def score_diff(diff: Dict[str, Any]) -> Dict[str, Any]:
    """
    Score all changes in a diff result and add summary statistics.

    Returns the same structure as generate_diff() but with scores on each
    change and a 'scoring_summary' block at the top level.
    """
    changes = diff.get("changes", [])
    scored  = [score_change(c) for c in changes]

    # Sort by composite descending so highest-impact changes appear first
    scored.sort(key=lambda c: c["composite"], reverse=True)

    # Summary: count by priority bucket
    summary: Dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for c in scored:
        summary[c["priority"]] += 1

    return {
        **diff,
        "changes": scored,
        "scoring_summary": summary,
    }
