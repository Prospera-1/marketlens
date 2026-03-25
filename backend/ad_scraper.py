"""
ad_scraper.py — Facebook Ad Library scraper (no API key required).

Uses Playwright to query the publicly accessible Facebook Ad Library search page
(https://www.facebook.com/ads/library) which does not require login for
searching ads by keyword. Returns structured ad signal data.

What we extract per ad:
  - ad_text       : Main body copy of the ad
  - page_name     : Advertiser name
  - started_date  : When the ad started running ("Started running on …")
  - platforms     : Where the ad is running (Facebook, Instagram, etc.)
  - cta_type      : Call-to-action button label if visible
  - media_type    : image / video / carousel / none

Rate limit / anti-bot notes:
  - We scrape the public search UI only; no login is attempted.
  - A human-like delay is added between scroll steps.
  - We limit to max_ads results per query to avoid triggering blocks.
  - Results are cached to disk for 6 hours to reduce repeat hits.
"""

import asyncio
import json
import os
import time
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any

ADS_CACHE_FILE = os.path.join('backend', 'data', 'ads_cache.json')
CACHE_TTL_HOURS = 6
MAX_ADS = 20  # per keyword query


# ── Cache helpers ──────────────────────────────────────────────────────────────

def _load_ads_cache() -> Dict:
    if os.path.exists(ADS_CACHE_FILE):
        try:
            with open(ADS_CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_ads_cache(cache: Dict):
    os.makedirs(os.path.dirname(ADS_CACHE_FILE), exist_ok=True)
    with open(ADS_CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def _cache_key(keyword: str) -> str:
    return keyword.lower().strip()


def _is_fresh(entry: Dict) -> bool:
    ts = entry.get('fetched_at')
    if not ts:
        return False
    try:
        fetched = datetime.fromisoformat(ts)
        return datetime.utcnow() - fetched < timedelta(hours=CACHE_TTL_HOURS)
    except Exception:
        return False


# ── Playwright scraper ────────────────────────────────────────────────────────

def _scrape_ads_impl(keyword: str) -> List[Dict]:
    """
    Synchronous Playwright scrape of the Facebook Ad Library public search.
    Runs in its own thread (called via _scrape_ads_thread).
    """
    from playwright.sync_api import sync_playwright

    url = (
        "https://www.facebook.com/ads/library/"
        f"?active_status=active&ad_type=all&country=IN"
        f"&q={keyword.replace(' ', '+')}&search_type=keyword_unordered"
    )

    ads: List[Dict] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
        page    = browser.new_page(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0 Safari/537.36"
            )
        )
        try:
            page.goto(url, wait_until='domcontentloaded', timeout=30000)
            page.wait_for_timeout(3000)

            # Accept cookie notice if present
            try:
                cookie_btn = page.locator('button[data-cookiebanner="accept_button"]')
                if cookie_btn.count() > 0:
                    cookie_btn.first.click()
                    page.wait_for_timeout(1500)
            except Exception:
                pass

            # Scroll to load more ads
            for _ in range(5):
                page.mouse.wheel(0, 2000)
                page.wait_for_timeout(1200)

            # Try to find ad cards — Facebook uses various class names that change,
            # so we look for structural patterns rather than specific class names.
            ad_containers = page.locator('[data-testid="ad_archive_preview"]').all()
            if not ad_containers:
                # Fallback: find cards by aria role
                ad_containers = page.locator('div[role="article"]').all()

            for container in ad_containers[:MAX_ADS]:
                try:
                    text   = container.inner_text()
                    ad     = _parse_ad_text(text)
                    if ad:
                        ads.append(ad)
                except Exception:
                    pass

        except Exception as e:
            print(f"[ad_scraper] Error scraping '{keyword}': {e}")
        finally:
            browser.close()

    return ads


def _parse_ad_text(raw: str) -> Dict | None:
    """
    Parse the inner_text() of a single ad card into structured fields.
    Facebook's ad card format is fairly consistent in its text layout.
    """
    lines = [l.strip() for l in raw.splitlines() if l.strip()]
    if len(lines) < 2:
        return None

    ad: Dict[str, Any] = {
        "page_name":    "",
        "ad_text":      "",
        "started_date": "",
        "platforms":    [],
        "cta_type":     "",
        "media_type":   "image",
    }

    text_lines = []
    for line in lines:
        low = line.lower()
        if 'started running on' in low:
            ad["started_date"] = line.split('on', 1)[-1].strip()
        elif any(p in low for p in ('facebook', 'instagram', 'messenger', 'audience network', 'whatsapp')):
            platforms = [p for p in ['Facebook', 'Instagram', 'Messenger', 'Audience Network', 'WhatsApp']
                         if p.lower() in low]
            if platforms:
                ad["platforms"] = platforms
        elif re.match(r'^(learn more|shop now|sign up|book now|contact us|apply now|get offer|download|watch more)$', low):
            ad["cta_type"] = line.title()
        elif len(line) > 20 and not ad["page_name"]:
            ad["page_name"] = line
        elif len(line) > 30:
            text_lines.append(line)

    ad["ad_text"] = ' '.join(text_lines[:3])  # keep top 3 copy lines

    # Detect media type from text cues
    raw_low = raw.lower()
    if 'video' in raw_low:
        ad["media_type"] = "video"
    elif 'carousel' in raw_low or 'multiple images' in raw_low:
        ad["media_type"] = "carousel"

    # Require at least a page name or ad text
    if not ad["page_name"] and not ad["ad_text"]:
        return None

    return ad


def _scrape_ads_thread(keyword: str) -> List[Dict]:
    """Run the Playwright scrape in its own event loop (Windows-safe)."""
    import concurrent.futures

    def _run():
        if os.name == 'nt':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return _scrape_ads_impl(keyword)
        finally:
            loop.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_run)
        return future.result(timeout=90)


# ── Public API ────────────────────────────────────────────────────────────────

def fetch_ads(keyword: str, force_refresh: bool = False) -> Dict[str, Any]:
    """
    Return ad library signals for a keyword, using cache when fresh.

    Returns:
        {
            "keyword": str,
            "ads": [ { page_name, ad_text, started_date, platforms, cta_type, media_type }, ... ],
            "fetched_at": ISO string,
            "from_cache": bool,
            "signals": { ... aggregated signals ... }
        }
    """
    key   = _cache_key(keyword)
    cache = _load_ads_cache()

    if not force_refresh and key in cache and _is_fresh(cache[key]):
        return {**cache[key], "from_cache": True}

    ads = _scrape_ads_thread(keyword)

    result = {
        "keyword":    keyword,
        "ads":        ads,
        "fetched_at": datetime.utcnow().isoformat(),
        "from_cache": False,
        "signals":    _aggregate_signals(ads, keyword),
    }

    cache[key] = result
    _save_ads_cache(cache)

    return result


def _aggregate_signals(ads: List[Dict], keyword: str) -> Dict:
    """
    Aggregate ad-level data into market-level signals:
      - top_advertisers  : who's running the most active ads
      - common_ctas      : most frequent CTA labels
      - platforms        : platform distribution
      - media_mix        : image vs video vs carousel
      - recent_starters  : ads that started in the last 30 days (fresh campaigns)
      - messaging_themes : top words appearing in ad copy
    """
    if not ads:
        return {}

    from collections import Counter

    cta_counter      = Counter()
    platform_counter = Counter()
    media_counter    = Counter()
    advertiser_counter = Counter()
    all_words        = []

    for ad in ads:
        if ad.get("cta_type"):
            cta_counter[ad["cta_type"]] += 1
        for p in (ad.get("platforms") or []):
            platform_counter[p] += 1
        if ad.get("media_type"):
            media_counter[ad["media_type"]] += 1
        if ad.get("page_name"):
            advertiser_counter[ad["page_name"]] += 1
        if ad.get("ad_text"):
            words = re.findall(r'\b[a-zA-Z]{4,}\b', ad["ad_text"].lower())
            all_words.extend(words)

    stop = {'with', 'that', 'this', 'from', 'have', 'your', 'into', 'more',
            'also', 'been', 'they', 'will', 'what', 'when', 'book', 'learn',
            'view', 'find', 'their', 'which', 'about', 'only', 'some', 'make'}
    word_counter = Counter(w for w in all_words if w not in stop)

    return {
        "total_ads_found":   len(ads),
        "top_advertisers":   advertiser_counter.most_common(5),
        "common_ctas":       cta_counter.most_common(5),
        "platform_spread":   dict(platform_counter.most_common()),
        "media_mix":         dict(media_counter.most_common()),
        "top_copy_themes":   [w for w, _ in word_counter.most_common(10)],
    }
