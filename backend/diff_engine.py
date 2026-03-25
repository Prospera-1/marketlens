import json
import os
from typing import List, Dict, Any, Tuple


def get_latest_two_snapshots(snapshots_dir: str) -> Tuple[Dict | None, Dict | None]:
    if not os.path.exists(snapshots_dir):
        return None, None

    files = [f for f in os.listdir(snapshots_dir) if f.endswith('.json')]
    files.sort(reverse=True)  # newest first

    if len(files) < 2:
        return None, None

    def load_json(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)

    latest = load_json(os.path.join(snapshots_dir, files[0]))
    previous = load_json(os.path.join(snapshots_dir, files[1]))
    return latest, previous


def normalize_list(lst: List[str]) -> set:
    return {item.lower().strip() for item in lst}


def _list_diff(old_comp: dict, new_comp: dict, field: str) -> tuple[set, set]:
    """Return (added, removed) sets for a list field."""
    old_set = normalize_list(old_comp.get(field) or [])
    new_set = normalize_list(new_comp.get(field) or [])
    return new_set - old_set, old_set - new_set


def generate_diff() -> Dict[str, Any]:
    snapshots_dir = os.path.join("backend", "data", "snapshots")
    latest, previous = get_latest_two_snapshots(snapshots_dir)

    if not latest or not previous:
        return {"status": "error", "message": "Need at least 2 snapshots to generate a diff"}

    latest_data = {comp["url"]: comp for comp in latest.get("competitors_data", [])}
    prev_data = {comp["url"]: comp for comp in previous.get("competitors_data", [])}

    changes = []

    for url, current_comp in latest_data.items():
        if url not in prev_data:
            changes.append({
                "url": url,
                "type": "new_competitor",
                "description": f"New competitor detected: {current_comp.get('title', url)}",
            })
            continue

        old_comp = prev_data[url]
        brand = current_comp.get('title', url)

        # ── Positioning (meta description) ────────────────────────────────────
        old_meta = (old_comp.get('meta_description') or '').strip()
        new_meta = (current_comp.get('meta_description') or '').strip()
        if old_meta and new_meta and old_meta.lower() != new_meta.lower():
            changes.append({
                "url": url, "brand": brand, "category": "Positioning",
                "description": f"{brand} changed their positioning statement.",
                "added": [new_meta], "removed": [old_meta],
            })

        # ── Hero / above-the-fold content ────────────────────────────────────
        added_hero, removed_hero = _list_diff(old_comp, current_comp, 'hero_text')
        if added_hero or removed_hero:
            changes.append({
                "url": url, "brand": brand, "category": "Hero Content",
                "description": f"{brand} changed their above-the-fold content.",
                "added": list(added_hero), "removed": list(removed_hero),
            })

        # ── Headings (messaging) ──────────────────────────────────────────────
        added_h, removed_h = _list_diff(old_comp, current_comp, 'headings')
        if added_h or removed_h:
            changes.append({
                "url": url, "brand": brand, "category": "Messaging",
                "description": f"{brand} updated their messaging / headings.",
                "added": list(added_h), "removed": list(removed_h),
            })

        # ── CTAs ──────────────────────────────────────────────────────────────
        added_ctas, removed_ctas = _list_diff(old_comp, current_comp, 'ctas')
        if added_ctas or removed_ctas:
            changes.append({
                "url": url, "brand": brand, "category": "CTAs",
                "description": f"{brand} updated their calls-to-action.",
                "added": list(added_ctas), "removed": list(removed_ctas),
            })

        # ── Pricing ───────────────────────────────────────────────────────────
        added_p, removed_p = _list_diff(old_comp, current_comp, 'pricing')
        if added_p or removed_p:
            changes.append({
                "url": url, "brand": brand, "category": "Pricing",
                "description": f"{brand} updated their pricing.",
                "added": list(added_p), "removed": list(removed_p),
            })

        # ── Features ──────────────────────────────────────────────────────────
        added_f, removed_f = _list_diff(old_comp, current_comp, 'features')
        if added_f or removed_f:
            changes.append({
                "url": url, "brand": brand, "category": "Features",
                "description": f"{brand} updated their feature list.",
                "added": list(added_f), "removed": list(removed_f),
            })

        # ── Testimonials ──────────────────────────────────────────────────────
        added_t, removed_t = _list_diff(old_comp, current_comp, 'testimonials')
        if added_t or removed_t:
            changes.append({
                "url": url, "brand": brand, "category": "Social Proof",
                "description": f"{brand} updated their testimonials.",
                "added": list(added_t), "removed": list(removed_t),
            })

        # ── G2 rating ─────────────────────────────────────────────────────────
        old_g2 = ((old_comp.get('reviews') or {}).get('g2') or {})
        new_g2 = ((current_comp.get('reviews') or {}).get('g2') or {})
        if old_g2.get('rating') and new_g2.get('rating'):
            delta = new_g2['rating'] - old_g2['rating']
            if abs(delta) >= 0.1:
                direction = "improved" if delta > 0 else "declined"
                changes.append({
                    "url": url, "brand": brand, "category": "G2 Rating",
                    "description": f"{brand}'s G2 rating {direction} from {old_g2['rating']} to {new_g2['rating']}.",
                    "added": [f"G2: {new_g2['rating']}/5"],
                    "removed": [f"G2: {old_g2['rating']}/5"],
                })

        # ── Trustpilot score ──────────────────────────────────────────────────
        old_tp = ((old_comp.get('reviews') or {}).get('trustpilot') or {})
        new_tp = ((current_comp.get('reviews') or {}).get('trustpilot') or {})
        if old_tp.get('trust_score') and new_tp.get('trust_score'):
            delta = new_tp['trust_score'] - old_tp['trust_score']
            if abs(delta) >= 0.1:
                direction = "improved" if delta > 0 else "declined"
                changes.append({
                    "url": url, "brand": brand, "category": "Trustpilot Score",
                    "description": f"{brand}'s Trustpilot score {direction} from {old_tp['trust_score']} to {new_tp['trust_score']}.",
                    "added": [f"Trustpilot: {new_tp['trust_score']}/5"],
                    "removed": [f"Trustpilot: {old_tp['trust_score']}/5"],
                })

    return {
        "status": "success",
        "timestamp_latest": latest.get("timestamp"),
        "timestamp_previous": previous.get("timestamp"),
        "changes": changes,
    }
