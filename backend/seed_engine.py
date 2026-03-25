"""
seed_engine.py — Demo baseline generator.

Creates a backdated "past" snapshot by scraping current URLs and applying
deterministic mutations that simulate what the pages looked like before recent
changes. When you then scrape the same URLs live, the diff engine surfaces
realistic-looking competitive changes.

Demo flow:
  1. Call /api/seed with your URLs  → creates a modified snapshot dated N days ago
  2. Call /api/fetch with same URLs → creates a live snapshot dated now
  3. Dashboard shows the diff       → changes are real page data, not fabricated

Mutations applied (all simulate "additions" the competitor made since the seed):
  - Pricing     : keep first ~50% of entries  (live shows new tiers added)
  - Features    : keep first ~60% of entries  (live shows new features added)
  - Headings    : keep first ~70% of entries  (live shows messaging expanded)
  - CTAs        : keep first ~50% of entries  (live shows new CTAs launched)
  - Hero text   : keep first item only        (live shows hero copy refreshed)
  - Testimonials: cleared entirely            (live shows social proof added)
  - Positioning : truncated to ~70% length    (live shows copy tightened)
"""

import copy
import json
import os
import argparse
from datetime import datetime, timedelta

from backend.scraper import fetch_html, extract_data


# ── Mutation helpers ──────────────────────────────────────────────────────────

def _drop_tail(lst: list, keep_ratio: float) -> list:
    """Keep only the first keep_ratio fraction of a list (minimum 1 item)."""
    if not lst:
        return lst
    keep = max(1, int(len(lst) * keep_ratio))
    return lst[:keep]


def _truncate_text(text: str, keep_ratio: float = 0.7) -> str:
    """Truncate a string to keep_ratio of its length, cutting at a word boundary."""
    if not text:
        return text
    cutoff = int(len(text) * keep_ratio)
    truncated = text[:cutoff].rsplit(' ', 1)[0]
    return truncated + ('.' if not truncated.endswith('.') else '')


def mutate_for_seed(data: dict) -> dict:
    """
    Return a copy of competitor data with fields trimmed to simulate an older
    state. The live scrape of the same page will appear to have additions in
    every tracked signal category.
    """
    seeded = copy.deepcopy(data)

    seeded['pricing']        = _drop_tail(seeded.get('pricing', []),    keep_ratio=0.50)
    seeded['features']       = _drop_tail(seeded.get('features', []),   keep_ratio=0.60)
    seeded['headings']       = _drop_tail(seeded.get('headings', []),   keep_ratio=0.70)
    seeded['ctas']           = _drop_tail(seeded.get('ctas', []),       keep_ratio=0.50)
    seeded['hero_text']      = _drop_tail(seeded.get('hero_text', []),  keep_ratio=0.50)
    seeded['testimonials']   = []   # cleared → live shows new social proof
    seeded['meta_description'] = _truncate_text(seeded.get('meta_description', ''))

    # No reviews in seed — simulates review tracking was not yet active
    seeded['reviews'] = {'g2': None, 'trustpilot': None}

    return seeded


# ── Core seeding function ─────────────────────────────────────────────────────

def seed_snapshots(urls: list[str], days_ago: int = 7) -> str | None:
    """
    Scrape each URL, apply mutations, and persist as a backdated snapshot.

    Args:
        urls:     Competitor URLs to scrape and seed.
        days_ago: How far back to date the snapshot (default 7 days).

    Returns:
        Path to the saved snapshot file, or None on failure.
    """
    print(f"\nSeeding demo baseline ({days_ago}d ago) for {len(urls)} URL(s)...")

    all_data = []
    for url in urls:
        html = fetch_html(url)
        if not html:
            print(f"  SKIP (fetch failed): {url}")
            continue
        data = extract_data(html, url)
        if not data:
            print(f"  SKIP (extract failed): {url}")
            continue
        all_data.append(mutate_for_seed(data))
        print(f"  Seeded: {url}")

    if not all_data:
        print("No data could be seeded.")
        return None

    backdated = datetime.now() - timedelta(days=days_ago)
    timestamp_str = backdated.strftime("%Y%m%d_%H%M%S")

    os.makedirs('backend/data/snapshots', exist_ok=True)
    filename = f"backend/data/snapshots/snapshot_{timestamp_str}.json"

    snapshot = {
        "timestamp": backdated.isoformat(),
        "seeded": True,         # audit tag — this snapshot was generated for demo purposes
        "competitors_data": all_data,
    }

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)

    print(f"\nSeed snapshot saved: {filename}")
    print("Next: scrape the same URLs via Run Scraper to see detected changes.")
    return filename


# ── Helper: auto-detect URLs from latest snapshot ────────────────────────────

def get_tracked_urls() -> list[str]:
    """Return the competitor URLs in the most recent snapshot, if any."""
    snapshots_dir = os.path.join('backend', 'data', 'snapshots')
    if not os.path.exists(snapshots_dir):
        return []
    files = sorted(
        [f for f in os.listdir(snapshots_dir) if f.endswith('.json')],
        reverse=True
    )
    if not files:
        return []
    with open(os.path.join(snapshots_dir, files[0]), 'r', encoding='utf-8') as f:
        latest = json.load(f)
    return [comp['url'] for comp in latest.get('competitors_data', [])]


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Seed a demo baseline snapshot for diff engine demonstration.'
    )
    parser.add_argument('urls', metavar='URL', type=str, nargs='*',
                        help='URLs to seed. Omit to reuse URLs from latest snapshot.')
    parser.add_argument('--days-ago', type=int, default=7,
                        help='Days back to date the seed snapshot (default: 7).')
    args = parser.parse_args()

    urls = args.urls or get_tracked_urls()

    if not urls:
        print("No URLs provided and no existing snapshots to reuse.")
        print("Usage: python -m backend.seed_engine https://example.com")
        return

    seed_snapshots(urls, days_ago=args.days_ago)


if __name__ == '__main__':
    main()
