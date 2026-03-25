"""
trend_engine.py — Multi-snapshot trend analysis.

Answers questions like:
  - "Has this competitor been raising prices consistently?"
  - "Which messaging themes keep appearing across multiple snapshots?"
  - "Who changes their CTAs most frequently?"
  - "Are multiple competitors converging on the same positioning angle?"

All analysis is rule-based, no API calls needed.

Trend types surfaced:
  rising_signal    — a field that keeps gaining new items across snapshots
  falling_signal   — a field that keeps losing items across snapshots
  volatile         — a competitor that changes a particular field very frequently
  converging_theme — a keyword/phrase appearing across multiple competitors
  stable           — a field that hasn't changed at all (good baseline signal)
"""

import json
import os
import re
from collections import defaultdict, Counter
from datetime import datetime
from typing import Dict, Any, List, Tuple


# ── Snapshot loader ───────────────────────────────────────────────────────────

def _load_all_snapshots(snapshots_dir: str) -> List[Dict]:
    """Return all snapshots sorted oldest → newest."""
    if not os.path.exists(snapshots_dir):
        return []
    files = sorted(
        [f for f in os.listdir(snapshots_dir) if f.endswith('.json')]
    )
    snapshots = []
    for f in files:
        try:
            with open(os.path.join(snapshots_dir, f), 'r', encoding='utf-8') as fh:
                snap = json.load(fh)
                snap['_filename'] = f
                snapshots.append(snap)
        except Exception:
            pass
    return snapshots


def _comp_map(snapshot: Dict) -> Dict[str, Dict]:
    """URL → competitor data dict for a snapshot."""
    return {c['url']: c for c in snapshot.get('competitors_data', [])}


# ── Field-level change history ────────────────────────────────────────────────

_LIST_FIELDS = ['pricing', 'features', 'headings', 'ctas', 'testimonials']


def _build_url_timeline(snapshots: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Group all competitor appearances by URL, sorted oldest → newest.

    Snapshots often contain different URLs from run to run, so we cannot
    rely on consecutive snapshot pairs sharing the same URL.  Instead we
    collect every time a URL appeared across *all* snapshots and build
    a per-URL ordered timeline.

    Returns: { url: [ comp_dict_with_ts, ... ] }  (sorted by timestamp)
    """
    url_timeline: Dict[str, List[Dict]] = defaultdict(list)

    for snap in snapshots:
        ts = snap.get('timestamp', snap['_filename'])
        for comp in snap.get('competitors_data', []):
            url = comp.get('url')
            if url:
                entry = dict(comp)
                entry['_ts'] = ts
                url_timeline[url].append(entry)

    # Sort each URL's appearances by their timestamp string (ISO-sortable)
    for url in url_timeline:
        url_timeline[url].sort(key=lambda c: c['_ts'])

    return url_timeline


def _build_change_history(snapshots: List[Dict]) -> Dict[str, Dict[str, List]]:
    """
    For each competitor URL and each list field, build a list of
    (timestamp, added_count, removed_count) tuples across its appearances.

    Uses per-URL timelines so that URLs that never appear together in the
    same snapshot file are still compared correctly across time.

    Returns: { url: { field: [(ts, added, removed), ...] } }
    """
    history: Dict[str, Dict[str, List]] = defaultdict(lambda: defaultdict(list))
    url_timeline = _build_url_timeline(snapshots)

    for url, appearances in url_timeline.items():
        if len(appearances) < 2:
            continue
        for i in range(1, len(appearances)):
            old  = appearances[i - 1]
            curr = appearances[i]
            ts   = curr['_ts']
            for field in _LIST_FIELDS:
                old_set = {x.lower().strip() for x in (old.get(field) or [])}
                new_set = {x.lower().strip() for x in (curr.get(field) or [])}
                added   = len(new_set - old_set)
                removed = len(old_set - new_set)
                if added or removed:
                    history[url][field].append((ts, added, removed))

    return history


# ── Trend detectors ───────────────────────────────────────────────────────────

def _detect_rising_falling(history: Dict[str, Dict[str, List]],
                            all_comps: Dict[str, str]) -> List[Dict]:
    """
    Detect fields that consistently gain or lose items across all tracked appearances.
    Requires only 1+ change interval (not 2) so URLs with few snapshots still surface.
    """
    trends = []
    for url, fields in history.items():
        title = all_comps.get(url, url)
        for field, changes in fields.items():
            if len(changes) < 1:
                continue
            net_adds    = sum(a - r for _, a, r in changes)
            total_adds  = sum(a for _, a, _ in changes)
            total_rems  = sum(r for _, _, r in changes)
            change_count = len(changes)

            if total_adds > 0 and total_rems == 0:
                trends.append({
                    "type":        "rising_signal",
                    "competitor":  title,
                    "url":         url,
                    "field":       field,
                    "description": (
                        f"{title} has been consistently adding to their "
                        f"{field} across {change_count} tracked interval(s) "
                        f"(+{total_adds} items added, 0 removed)."
                    ),
                    "change_count": change_count,
                    "net_delta":    net_adds,
                    "significance": min(10, change_count * 2 + total_adds),
                })
            elif total_rems > 0 and total_adds == 0:
                trends.append({
                    "type":        "falling_signal",
                    "competitor":  title,
                    "url":         url,
                    "field":       field,
                    "description": (
                        f"{title} has been consistently removing from their "
                        f"{field} across {change_count} tracked interval(s) "
                        f"(0 added, -{total_rems} removed)."
                    ),
                    "change_count": change_count,
                    "net_delta":    -total_rems,
                    "significance": min(10, change_count * 2 + total_rems),
                })

    return trends


def _detect_volatile(history: Dict[str, Dict[str, List]],
                     all_comps: Dict[str, str],
                     url_timeline: Dict[str, List]) -> List[Dict]:
    """Detect competitors that change a specific field in most of their appearances (volatile)."""
    trends = []
    for url, fields in history.items():
        appearances = len(url_timeline.get(url, []))
        if appearances < 2:
            continue
        title = all_comps.get(url, url)
        for field, changes in fields.items():
            change_rate = len(changes) / max(1, appearances - 1)
            if change_rate >= 0.6 and len(changes) >= 2:
                trends.append({
                    "type":        "volatile",
                    "competitor":  title,
                    "url":         url,
                    "field":       field,
                    "description": (
                        f"{title} changed their {field} in "
                        f"{len(changes)} of {appearances - 1} tracked intervals "
                        f"({int(change_rate * 100)}% change rate) — "
                        f"this signal is actively being tested or iterated."
                    ),
                    "change_count": len(changes),
                    "change_rate":  round(change_rate, 2),
                    "significance": min(10, int(change_rate * 10) + 2),
                })
    return trends


def _detect_converging_themes(snapshots: List[Dict],
                               min_competitors: int = 2,
                               url_timeline: Dict = None) -> List[Dict]:
    """
    Find keywords/phrases that appear in the same field across multiple
    competitors — signals of market-wide convergence.

    Uses the most recent appearance of every tracked URL, not just the
    competitors present in the latest single snapshot file. This is critical
    when recent snapshots contain only one or two URLs.
    """
    if not snapshots:
        return []

    if url_timeline:
        # Use the latest scraped data for each unique URL
        comps = [apps[-1] for apps in url_timeline.values() if apps]
    else:
        latest = snapshots[-1]
        comps  = latest.get('competitors_data', [])

    if len(comps) < 2:
        return []

    field_keyword_counts: Dict[str, Counter] = defaultdict(Counter)
    field_keyword_sources: Dict[str, Dict[str, List[str]]] = defaultdict(lambda: defaultdict(list))

    for comp in comps:
        title = comp.get('title', comp.get('url', ''))
        for field in _LIST_FIELDS + ['headings']:
            for item in (comp.get(field) or []):
                # Extract significant words (3+ chars, not stop words)
                words = re.findall(r'\b[a-zA-Z]{4,}\b', item.lower())
                stop = {'with', 'that', 'this', 'from', 'have', 'your', 'into',
                        'more', 'also', 'been', 'they', 'their', 'will', 'what',
                        'when', 'where', 'which', 'about', 'make', 'over', 'than',
                        'then', 'some', 'each', 'most', 'only', 'other', 'after',
                        'book', 'learn', 'view', 'find', 'read', 'show', 'load'}
                for word in set(words) - stop:
                    field_keyword_counts[field][word] += 1
                    if title not in field_keyword_sources[field][word]:
                        field_keyword_sources[field][word].append(title)

    trends = []
    # Sort by number of unique competitors using the keyword (not raw item count)
    seen_keywords: set = set()
    for field in field_keyword_sources:
        # Sort by unique competitor count descending
        by_comp_count = sorted(
            field_keyword_sources[field].items(),
            key=lambda kv: len(kv[1]),
            reverse=True
        )
        added = 0
        for keyword, sources in by_comp_count:
            if added >= 5:
                break
            comp_count = len(sources)
            dedup_key  = (field, keyword)
            if comp_count >= min_competitors and dedup_key not in seen_keywords:
                seen_keywords.add(dedup_key)
                added += 1
                trends.append({
                    "type":        "converging_theme",
                    "field":       field,
                    "keyword":     keyword,
                    "description": (
                        f'The theme "{keyword}" appears in the {field} of '
                        f"{comp_count} competitors ({', '.join(sources[:4])}) — "
                        f"this angle may be becoming table stakes in this market."
                    ),
                    "competitors": sources,
                    "count":       comp_count,
                    "significance": min(10, comp_count * 3),
                })

    return sorted(trends, key=lambda x: x['significance'], reverse=True)[:8]


def _detect_stable(url_timeline: Dict[str, List], all_comps: Dict[str, str]) -> List[Dict]:
    """
    Identify competitors + fields that have NEVER changed across their appearances.
    Stable pricing signals a brand confident in their positioning.
    Uses per-URL timelines so URLs that don't appear together still get compared.
    """
    trends = []

    for url, appearances in url_timeline.items():
        if len(appearances) < 3:
            continue
        title = all_comps.get(url, url)
        first = appearances[0]
        last  = appearances[-1]

        for field in ['pricing', 'headings', 'ctas']:
            old_set = {x.lower().strip() for x in (first.get(field) or [])}
            new_set = {x.lower().strip() for x in (last.get(field) or [])}
            if old_set and old_set == new_set and len(old_set) >= 2:
                # Verify truly unchanged across ALL appearances, not just first/last
                all_same = all(
                    {x.lower().strip() for x in (a.get(field) or [])} == old_set
                    for a in appearances
                )
                if all_same:
                    trends.append({
                        "type":        "stable",
                        "competitor":  title,
                        "url":         url,
                        "field":       field,
                        "description": (
                            f"{title}'s {field} has remained completely unchanged across "
                            f"all {len(appearances)} tracked appearances — strong signal of a "
                            f"deliberate, locked-in strategy."
                        ),
                        "snapshot_count": len(appearances),
                        "significance":   5,
                    })

    return trends


# ── Public entry point ────────────────────────────────────────────────────────

def build_trends() -> Dict[str, Any]:
    """
    Analyse all snapshots and return a structured trend report.
    Requires at least 2 snapshots; works best with 3+.
    """
    snapshots_dir = os.path.join('backend', 'data', 'snapshots')
    snapshots = _load_all_snapshots(snapshots_dir)

    if len(snapshots) < 2:
        return {
            "status":  "insufficient_data",
            "message": "Need at least 2 snapshots to detect trends. Seed a baseline then scrape again.",
            "trends":  [],
            "summary": {},
        }

    # Build a url→title map from all snapshots (latest title wins)
    all_comps = {}
    for snap in snapshots:
        for c in snap.get('competitors_data', []):
            url = c.get('url')
            if url:
                all_comps[url] = c.get('title') or url

    url_timeline = _build_url_timeline(snapshots)
    history      = _build_change_history(snapshots)

    rising   = _detect_rising_falling(history, all_comps)
    volatile = _detect_volatile(history, all_comps, url_timeline)
    converge = _detect_converging_themes(snapshots, url_timeline=url_timeline)
    stable   = _detect_stable(url_timeline, all_comps)

    all_trends = rising + volatile + converge + stable
    all_trends.sort(key=lambda t: t.get('significance', 0), reverse=True)

    summary = {
        "snapshots_analysed": len(snapshots),
        "competitors_tracked": len(url_timeline),
        "rising_signals":      len([t for t in all_trends if t['type'] == 'rising_signal']),
        "falling_signals":     len([t for t in all_trends if t['type'] == 'falling_signal']),
        "volatile_fields":     len([t for t in all_trends if t['type'] == 'volatile']),
        "converging_themes":   len([t for t in all_trends if t['type'] == 'converging_theme']),
        "stable_signals":      len([t for t in all_trends if t['type'] == 'stable']),
        "date_range": {
            "earliest": snapshots[0].get('timestamp', snapshots[0]['_filename']),
            "latest":   snapshots[-1].get('timestamp', snapshots[-1]['_filename']),
        },
    }

    return {
        "status":  "success",
        "trends":  all_trends,
        "summary": summary,
    }
