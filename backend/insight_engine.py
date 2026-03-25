"""
insight_engine.py — Gemini-powered strategic insight and whitespace generation.

Design:
- Results are cached on disk (backend/data/insights_cache.json) keyed by the
  latest snapshot timestamp.  GET /api/insights returns the cache instantly —
  no Gemini call.  POST /api/insights/generate forces a fresh generation.
- This prevents quota exhaustion from multiple page loads, and gives users
  explicit control over when to spend API quota.

Insight schema:
  title, description, action,
  scores: { novelty, frequency, relevance, composite },
  source_traces: [{ url, field, snippet }]

Whitespace schema:
  description, opportunity_score, suggested_action, supporting_evidence
"""

import os
import json
import time
from google import genai
from typing import Dict, Any

from backend.diff_engine import get_latest_two_snapshots

_CACHE_FILE = os.path.join("backend", "data", "insights_cache.json")

# Override with GEMINI_MODEL in .env (e.g. gemini-2.5-flash-lite, gemini-1.5-flash).
_DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"


# ── Cache helpers ─────────────────────────────────────────────────────────────

def _load_cache() -> dict:
    if os.path.exists(_CACHE_FILE):
        try:
            with open(_CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_cache(data: dict) -> None:
    os.makedirs(os.path.dirname(_CACHE_FILE), exist_ok=True)
    with open(_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_cached_insights() -> Dict[str, Any]:
    """Return the last cached insights + whitespace, or empty defaults."""
    cache = _load_cache()
    return {
        "insights":  cache.get("insights", []),
        "whitespace": cache.get("whitespace", []),
        "generated_at": cache.get("generated_at"),
        "snapshot_timestamp": cache.get("snapshot_timestamp"),
    }


# ── Gemini helpers ────────────────────────────────────────────────────────────

def _call_gemini(prompt: str) -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError("GEMINI_API_KEY is not set. Add it to your .env file.")
    model = os.environ.get("GEMINI_MODEL", _DEFAULT_GEMINI_MODEL).strip()
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=prompt,
    )
    return response.text.strip()


def _parse_json_response(raw: str) -> dict:
    if raw.startswith("```json"):
        raw = raw[7:]
    elif raw.startswith("```"):
        raw = raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3]
    return json.loads(raw.strip())


# ── Insight generation ────────────────────────────────────────────────────────

def generate_insights(diff_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate strategic insights from detected competitor changes.
    Each insight includes title, description, action, score breakdown,
    and source_traces linking to specific fields and snippets.
    """
    changes = diff_data.get("changes", [])
    if not changes:
        return {"insights": [], "message": "No changes detected to analyze."}

    prompt = f"""
You are a senior strategy consultant analyzing competitor intelligence data.
Below are structured changes detected between two web scrape snapshots of competitor pages.

COMPETITOR CHANGES:
{json.dumps(changes, indent=2)}

Your task:
Generate 3-5 high-impact strategic insights from these changes.

For EACH insight you MUST:
1. Identify the strategic signal (e.g. "Competitor X is shifting toward outcome-based messaging").
2. Explain WHY this matters for our company.
3. Provide ONE specific recommended action our team should take.
4. Score the insight on three dimensions (1-10 each):
   - novelty: How new/surprising is this signal vs. known market trends?
   - frequency: How often is this pattern appearing across competitors?
   - relevance: How directly does this affect our strategy or revenue?
5. List the exact source traces (url + field name + exact text snippet from the data)
   that support this insight. Only cite what appears in the COMPETITOR CHANGES above.

Output ONLY valid JSON — no markdown, no extra text:
{{
  "insights": [
    {{
      "title": "Short title (max 8 words)",
      "description": "2-3 sentence explanation of the strategic signal and why it matters.",
      "action": "One specific, actionable recommendation for our team.",
      "scores": {{
        "novelty": 7,
        "frequency": 5,
        "relevance": 9,
        "composite": 7
      }},
      "source_traces": [
        {{
          "url": "https://example.com",
          "field": "pricing",
          "snippet": "exact text from the data"
        }}
      ]
    }}
  ]
}}
"""

    raw = _call_gemini(prompt)
    result = _parse_json_response(raw)

    # Recompute composite as a clean average regardless of what Gemini returned
    for insight in result.get("insights", []):
        s = insight.get("scores", {})
        if s.get("novelty") and s.get("frequency") and s.get("relevance"):
            s["composite"] = round(
                (s["novelty"] + s["frequency"] + s["relevance"]) / 3, 1
            )
    return result


# ── Whitespace detection ──────────────────────────────────────────────────────

def detect_whitespace(latest_data: list) -> Dict[str, Any]:
    """
    Identify unserved market niches from the latest competitor snapshot.
    Returns structured whitespace items with score, action, and evidence.
    """
    lean_data = [
        {
            "url": comp.get("url"),
            "title": comp.get("title"),
            "meta_description": comp.get("meta_description"),
            "hero_text": comp.get("hero_text"),
            "features": comp.get("features"),
            "pricing": comp.get("pricing"),
            "ctas": comp.get("ctas"),
            "testimonials": comp.get("testimonials"),
        }
        for comp in latest_data
    ]

    prompt = f"""
You are a market strategy analyst identifying whitespace opportunities.
Below is the current competitive landscape scraped from competitor websites.

COMPETITOR LANDSCAPE:
{json.dumps(lean_data, indent=2)}

Your task:
Identify 3-5 whitespace opportunities — things NO competitor in this dataset is doing,
but that customers likely want or need.

For EACH whitespace opportunity:
1. Describe the gap clearly (e.g. "No competitor offers a free AI-powered trial with onboarding support").
2. Assign an opportunity_score (1-10): how large and addressable is this gap?
3. Suggest a concrete action our team could take to fill this gap.
4. Cite what is absent in the competitor data that reveals this gap.

Output ONLY valid JSON — no markdown, no extra text:
{{
  "whitespace": [
    {{
      "description": "Clear description of the unserved niche.",
      "opportunity_score": 8,
      "suggested_action": "Specific action our team should take.",
      "supporting_evidence": "What is absent in the competitor data that reveals this gap."
    }}
  ]
}}
"""

    raw = _call_gemini(prompt)
    result = _parse_json_response(raw)
    return result


# ── Public entry point (called by /api/insights/generate) ────────────────────

def generate_and_cache_all() -> Dict[str, Any]:
    """
    Run both insight generation and whitespace detection, cache the result,
    and return it.  Raises on Gemini errors so the caller can surface them.
    """
    snapshots_dir = os.path.join("backend", "data", "snapshots")
    latest, previous = get_latest_two_snapshots(snapshots_dir)

    if not latest:
        return {"insights": [], "whitespace": [], "error": "No snapshots found."}

    # ── Build diff for insights ──────────────────────────────────────────────
    from backend.diff_engine import generate_diff
    diff_data = generate_diff()

    insights_result  = {"insights": []}
    whitespace_result = {"whitespace": []}
    errors = []

    # Insights need a diff with actual changes
    if diff_data.get("status") == "success" and diff_data.get("changes"):
        try:
            insights_result = generate_insights(diff_data)
        except Exception as e:
            errors.append(f"Insights: {e}")
            print(f"Insight Generation Error: {e}")
    else:
        insights_result = {"insights": [], "message": "No changes to analyse yet."}

    # Whitespace only needs the latest snapshot
    try:
        whitespace_result = detect_whitespace(latest.get("competitors_data", []))
    except Exception as e:
        errors.append(f"Whitespace: {e}")
        print(f"Whitespace Generation Error: {e}")

    cache_entry = {
        "insights":           insights_result.get("insights", []),
        "whitespace":         whitespace_result.get("whitespace", []),
        "generated_at":       time.strftime("%Y-%m-%dT%H:%M:%S"),
        "snapshot_timestamp": latest.get("timestamp"),
        "errors":             errors,
    }
    _save_cache(cache_entry)
    return cache_entry
