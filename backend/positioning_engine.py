"""
positioning_engine.py — Rule-based competitive positioning classifier.

Analyses each competitor's scraped signals (pricing, CTAs, features,
testimonials, meta description) to place them on three strategic axes:

  Axis 1 — Price positioning:   cost_score  (0–10)  0=cost-leader, 10=premium
  Axis 2 — Value framing:       outcome_score (0–10) 0=feature-rich, 10=outcome-driven
  Axis 3 — Go-to-market motion: sales_score (0–10)   0=self-serve, 10=sales-led

The two most readable axes for a 2D matrix are:
  X = cost_score       (Cost-leader ←→ Premium)
  Y = sales_score      (Self-serve  ←→ Sales-led)

outcome_score is included as a third dimension (shown as bubble size or
colour in the UI).

All scoring is deterministic keyword/heuristic matching — no API calls.
"""

from typing import Dict, Any, List


# ── Keyword signal libraries ──────────────────────────────────────────────────

# Pricing signals
_FREE_TIER_SIGNALS   = {'free', 'free forever', 'free plan', 'free trial', 'no credit card',
                        'open source', 'community', 'starter', 'basic free', '0/mo', '$0'}
_CHEAP_SIGNALS       = {'affordable', 'budget', 'low cost', 'cost effective', 'value',
                        'cheapest', 'per user', '/month', '/mo', 'from $', 'starting at $'}
_PREMIUM_SIGNALS     = {'enterprise', 'premium', 'custom pricing', 'contact sales for pricing',
                        'tailored', 'bespoke', 'white glove', 'dedicated', 'concierge',
                        'platinum', 'unlimited', 'fortune 500', 'sla'}

# CTA signals
_SELF_SERVE_CTAS     = {'start free', 'get started', 'try free', 'sign up', 'signup',
                        'try for free', 'create account', 'start for free', 'get for free',
                        'download', 'install', 'join free', 'start now', 'get started free'}
_SALES_LED_CTAS      = {'contact sales', 'talk to sales', 'book a demo', 'request demo',
                        'schedule a call', 'get a quote', 'speak to an expert',
                        'talk to us', 'contact us', 'request a demo', 'watch demo',
                        'get pricing', 'get a demo'}

# Feature-focused signals
_FEATURE_SIGNALS     = {'feature', 'integration', 'api', 'automation', 'dashboard',
                        'reporting', 'analytics', 'workflow', 'template', 'plugin',
                        'module', 'tool', 'capability', 'functionality', 'built-in'}

# Outcome / benefit signals
_OUTCOME_SIGNALS     = {'save', 'increase', 'reduce', 'grow', 'improve', 'faster',
                        'easier', 'boost', 'transform', 'drive', 'achieve', 'results',
                        'roi', 'revenue', 'efficiency', 'success', 'win', 'scale',
                        'empower', 'accelerate'}


# ── Scoring helpers ───────────────────────────────────────────────────────────

def _text_hits(text: str, signals: set) -> int:
    """Count how many signal keywords appear in a lowercased text."""
    lower = text.lower()
    return sum(1 for s in signals if s in lower)


def _list_hits(items: List[str], signals: set) -> int:
    total = 0
    for item in (items or []):
        total += _text_hits(item, signals)
    return total


def _clamp(value: float, lo: float = 0.0, hi: float = 10.0) -> float:
    return max(lo, min(hi, value))


# ── Per-competitor classifier ─────────────────────────────────────────────────

def classify_competitor(comp: Dict[str, Any]) -> Dict[str, Any]:
    """
    Return a positioning profile for a single competitor data dict.
    """
    pricing      = comp.get("pricing", []) or []
    ctas         = comp.get("ctas", [])    or []
    features     = comp.get("features", []) or []
    testimonials = comp.get("testimonials", []) or []
    hero_text    = comp.get("hero_text", []) or []
    meta_desc    = comp.get("meta_description", "") or ""
    headings     = comp.get("headings", []) or []

    all_text_lists = [pricing, ctas, features, testimonials, hero_text, headings]
    all_text       = " ".join([meta_desc] + [t for lst in all_text_lists for t in lst]).lower()

    # ── Axis 1: Cost-leader (0) vs Premium (10) ──────────────────────────────
    free_hits    = _list_hits(pricing + ctas + features, _FREE_TIER_SIGNALS)
    cheap_hits   = _list_hits(pricing, _CHEAP_SIGNALS)
    premium_hits = _list_hits(pricing + ctas + [meta_desc] + headings, _PREMIUM_SIGNALS)

    # Positive = premium; negative = cost-leader; centre at 5
    cost_raw   = 5.0 + (premium_hits * 1.5) - (free_hits * 2.0) - (cheap_hits * 0.8)
    cost_score = round(_clamp(cost_raw), 1)

    # ── Axis 2: Feature-rich (0) vs Outcome-driven (10) ──────────────────────
    feature_hits = _list_hits(features + headings, _FEATURE_SIGNALS)
    outcome_hits = _list_hits(testimonials + hero_text + headings + [meta_desc], _OUTCOME_SIGNALS)

    outcome_raw   = 5.0 + (outcome_hits * 0.8) - (feature_hits * 0.6)
    outcome_score = round(_clamp(outcome_raw), 1)

    # ── Axis 3: Self-serve (0) vs Sales-led (10) ─────────────────────────────
    self_serve_hits = _list_hits(ctas, _SELF_SERVE_CTAS)
    sales_led_hits  = _list_hits(ctas + [meta_desc], _SALES_LED_CTAS)

    sales_raw   = 5.0 + (sales_led_hits * 2.0) - (self_serve_hits * 2.0)
    sales_score = round(_clamp(sales_raw), 1)

    # ── Labels ────────────────────────────────────────────────────────────────
    cost_label    = "Premium" if cost_score >= 6.5 else ("Cost-Leader" if cost_score <= 3.5 else "Mid-Market")
    outcome_label = "Outcome-Driven" if outcome_score >= 6.5 else ("Feature-Rich" if outcome_score <= 3.5 else "Balanced")
    sales_label   = "Sales-Led" if sales_score >= 6.5 else ("Self-Serve" if sales_score <= 3.5 else "Hybrid")

    # ── Evidence: which signals drove each score ──────────────────────────────
    evidence: Dict[str, List[str]] = {"pricing": [], "ctas": [], "outcomes": []}
    for p in pricing[:3]:
        if any(s in p.lower() for s in _FREE_TIER_SIGNALS | _PREMIUM_SIGNALS):
            evidence["pricing"].append(p)
    for c in ctas[:3]:
        if any(s in c.lower() for s in _SELF_SERVE_CTAS | _SALES_LED_CTAS):
            evidence["ctas"].append(c)
    for t in (testimonials + hero_text)[:3]:
        if any(s in t.lower() for s in _OUTCOME_SIGNALS):
            evidence["outcomes"].append(t[:120])

    return {
        "url":   comp.get("url", ""),
        "title": comp.get("title", comp.get("url", "")),
        "scores": {
            "cost":    cost_score,
            "outcome": outcome_score,
            "sales":   sales_score,
        },
        "labels": {
            "cost":    cost_label,
            "outcome": outcome_label,
            "sales":   sales_label,
        },
        "evidence": evidence,
    }


# ── Overused angle detector ──────────────────────────────────────────────────

# Positioning angle → keywords that signal it
_ANGLE_SIGNALS: Dict[str, List[str]] = {
    "Outcome-Driven Messaging":   ["save time", "save money", "increase revenue", "reduce cost",
                                   "boost", "grow", "faster results", "improve roi", "drive growth"],
    "Enterprise Focus":           ["enterprise", "fortune 500", "large team", "dedicated support",
                                   "sla", "compliance", "security"],
    "Simplicity / Ease of Use":   ["easy to use", "no code", "simple", "just works", "in minutes",
                                   "no setup", "plug and play", "beginner friendly"],
    "AI-Powered":                 ["ai", "artificial intelligence", "machine learning", "smart",
                                   "intelligent", "automated", "predictive"],
    "Free / Low Cost Entry":      ["free plan", "free trial", "free forever", "no credit card",
                                   "start free", "get started free", "$0"],
    "Speed / Performance":        ["fast", "instant", "real-time", "lightning", "quick", "seconds",
                                   "blazing", "high performance"],
    "Trusted / Social Proof":     ["trusted by", "used by", "customers", "reviews", "rated",
                                   "award", "recognized", "leading"],
    "Integration Ecosystem":      ["integrations", "connects with", "works with", "api", "zapier",
                                   "slack", "salesforce", "hubspot", "ecosystem"],
}

# Threshold: if this fraction of competitors use an angle, it is "overused"
_OVERUSE_THRESHOLD = 0.5  # 50% of competitors


def detect_overused_angles(profiles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Examine all competitor profiles and identify positioning angles that appear
    in more than OVERUSE_THRESHOLD fraction of competitors.

    Returns a list of angle objects sorted by saturation (most overused first):
    [
      {
        "angle":       str,           # e.g. "AI-Powered"
        "saturation":  float,         # 0–1 (fraction of competitors using it)
        "count":       int,
        "competitors": [str, ...],
        "implication": str,           # strategic takeaway
        "whitespace_hint": str,       # the opposite / unexplored angle
      },
      ...
    ]
    """
    if not profiles:
        return []

    total = len(profiles)
    angle_hits: Dict[str, List[str]] = {a: [] for a in _ANGLE_SIGNALS}

    for profile in profiles:
        # Reconstruct a searchable text blob from evidence
        evidence = profile.get("evidence", {})
        evidence_text = " ".join(
            v if isinstance(v, str) else " ".join(v)
            for v in evidence.values()
        ).lower()
        title = profile.get("title", "")

        # Also use labels as cheap proxies
        labels_text = " ".join(profile.get("labels", {}).values()).lower()
        full_text   = evidence_text + " " + labels_text

        for angle, signals in _ANGLE_SIGNALS.items():
            if any(sig in full_text for sig in signals):
                angle_hits[angle].append(title)

    overused = []
    for angle, users in angle_hits.items():
        saturation = len(users) / total
        if saturation >= _OVERUSE_THRESHOLD and len(users) >= 2:
            overused.append({
                "angle":        angle,
                "saturation":   round(saturation, 2),
                "count":        len(users),
                "competitors":  users,
                "implication":  (
                    f"{len(users)} of {total} competitors ({int(saturation * 100)}%) "
                    f"use the '{angle}' positioning angle — this is becoming table stakes "
                    f"and differentiating on it alone will be increasingly hard."
                ),
                "whitespace_hint": _WHITESPACE_HINT.get(angle, "Consider an unexplored counter-positioning angle."),
            })

    overused.sort(key=lambda x: x["saturation"], reverse=True)
    return overused


_WHITESPACE_HINT: Dict[str, str] = {
    "Outcome-Driven Messaging":
        "Competitors obsess over outcomes — whitespace may exist in radical transparency "
        "(e.g. showing how the outcome is achieved, not just claiming it).",
    "Enterprise Focus":
        "Heavy enterprise coverage leaves SMB/mid-market segments underserved — "
        "a focused SMB play or a self-serve motion could capture neglected buyers.",
    "Simplicity / Ease of Use":
        "Everyone claims simplicity — consider owning 'power-user depth' or "
        "'customisability' as the differentiated angle for technical buyers.",
    "AI-Powered":
        "AI is ubiquitous; the whitespace is in 'explainable AI', human-in-the-loop "
        "control, or AI-free guarantees for compliance-sensitive markets.",
    "Free / Low Cost Entry":
        "A saturated free tier race erodes margins — 'no free tier, but 10× the value' "
        "or premium-only positioning could attract buyers fatigued by feature-limited free plans.",
    "Speed / Performance":
        "Speed is table stakes; the whitespace is in reliability, trust, or accuracy "
        "messaging — 'right over fast' for high-stakes use cases.",
    "Trusted / Social Proof":
        "Everyone claims trust — owning a very specific credential (e.g. SOC 2, "
        "ISO 27001, or a niche industry award) creates harder-to-copy proof.",
    "Integration Ecosystem":
        "Broad integration claims are common — depth in one critical platform "
        "(e.g. 'the best Salesforce native experience') can beat breadth.",
}


# ── Public entry point ────────────────────────────────────────────────────────

def build_positioning_map(competitors_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Classify all competitors and return the positioning map along with
    axis extremes (which competitor leads / trails on each axis).
    """
    profiles = [classify_competitor(c) for c in competitors_data]

    if not profiles:
        return {"profiles": [], "axis_leaders": {}}

    # Find leaders on each axis for context
    most_premium     = max(profiles, key=lambda p: p["scores"]["cost"])
    most_costleader  = min(profiles, key=lambda p: p["scores"]["cost"])
    most_salesled    = max(profiles, key=lambda p: p["scores"]["sales"])
    most_selfserve   = min(profiles, key=lambda p: p["scores"]["sales"])
    most_outcome     = max(profiles, key=lambda p: p["scores"]["outcome"])
    most_featurerich = min(profiles, key=lambda p: p["scores"]["outcome"])

    axis_leaders = {
        "most_premium":      most_premium["title"],
        "most_cost_leader":  most_costleader["title"],
        "most_sales_led":    most_salesled["title"],
        "most_self_serve":   most_selfserve["title"],
        "most_outcome":      most_outcome["title"],
        "most_feature_rich": most_featurerich["title"],
    }

    overused = detect_overused_angles(profiles)

    return {
        "profiles":       profiles,
        "axis_leaders":   axis_leaders,
        "overused_angles": overused,
        "axes": {
            "x": {"label": "Price Positioning", "low": "Cost-Leader", "high": "Premium"},
            "y": {"label": "Go-To-Market",       "low": "Self-Serve",  "high": "Sales-Led"},
            "z": {"label": "Value Framing",      "low": "Feature-Rich","high": "Outcome-Driven"},
        },
    }
