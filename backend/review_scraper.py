"""
Review platform scraper for G2 and Trustpilot.

Auto-discovers review pages from a competitor's website URL, then
extracts ratings, pros/cons, and recent review snippets using Playwright.
"""

import re
import asyncio
import warnings
import concurrent.futures
from urllib.parse import urlparse
from bs4 import BeautifulSoup  # type: ignore
from urllib3.exceptions import InsecureRequestWarning  # type: ignore

warnings.simplefilter('ignore', InsecureRequestWarning)

# ── URL helpers ───────────────────────────────────────────────────────────────

def _domain(url: str) -> str:
    """Extract bare domain from any URL. e.g. https://www.notion.so/foo → notion.so"""
    parsed = urlparse(url)
    return parsed.netloc.replace('www.', '').replace('app.', '').strip('/')


def _company_slug(url: str) -> str:
    """Derive a likely G2 product slug from a company URL. e.g. notion.so → notion"""
    return _domain(url).split('.')[0]


def _playwright_fetch_impl(url: str, wait_ms: int) -> tuple[str | None, int]:
    """Inner Playwright fetch — must run in a thread with a SelectorEventLoop."""
    from playwright.sync_api import sync_playwright  # type: ignore
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
        )
        page = context.new_page()
        response = page.goto(url, wait_until="domcontentloaded", timeout=25000)
        status = response.status if response else 0
        if status == 404:
            browser.close()
            return None, 404
        page.wait_for_timeout(wait_ms)
        html = page.content()
        browser.close()
        return html, status


def _playwright_fetch_thread(url: str, wait_ms: int) -> tuple[str | None, int]:
    """
    Run Playwright in a thread with an explicit SelectorEventLoop.

    On Windows, uvicorn uses ProactorEventLoop which cannot spawn subprocesses
    from worker threads (raises NotImplementedError).  Setting a SelectorEventLoop
    inside the dedicated thread resolves this without touching the main loop.
    """
    if hasattr(asyncio, 'WindowsSelectorEventLoopPolicy'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return _playwright_fetch_impl(url, wait_ms)
    finally:
        loop.close()


def _playwright_fetch(url: str, wait_ms: int = 3000) -> tuple[str | None, int]:
    """Fetch a JS-rendered page with Playwright. Returns (html, status_code)."""
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_playwright_fetch_thread, url, wait_ms)
            return future.result(timeout=35)
    except Exception as e:
        print(f"WARNING: Playwright fetch failed for {url}: {e}")
        return None, 0

# ── G2 scraper ────────────────────────────────────────────────────────────────

def scrape_g2(company_url: str) -> dict | None:
    """
    Scrape G2 review page for a company derived from its website URL.
    Attempts https://www.g2.com/products/{slug}/reviews
    Returns structured data or None if the page is not found / unusable.
    """
    slug = _company_slug(company_url)
    g2_url = f"https://www.g2.com/products/{slug}/reviews"

    html, status = _playwright_fetch(g2_url)
    if not html:
        return None

    soup = BeautifulSoup(html, 'html.parser')
    page_text = soup.get_text(separator=' ')

    result: dict = {
        "url": g2_url,
        "rating": None,
        "review_count": None,
        "pros": [],
        "cons": [],
        "recent_snippets": [],
    }

    # Overall rating — e.g. "4.7 out of 5"
    rating_match = re.search(r'(\d+\.\d+)\s*out of\s*5', page_text)
    if rating_match:
        result["rating"] = float(rating_match.group(1))

    # Review count — e.g. "1,234 reviews"
    count_match = re.search(r'([\d,]+)\s*(?:G2\s+)?reviews?', page_text, re.IGNORECASE)
    if count_match:
        result["review_count"] = int(count_match.group(1).replace(',', ''))

    seen: set[str] = set()

    # Pros — under "What do you like best?"
    for heading in soup.find_all(string=re.compile(r'like best', re.IGNORECASE)):
        parent = heading.find_parent()
        if parent:
            sibling = parent.find_next_sibling()
            if sibling:
                text = sibling.get_text(strip=True)
                if text and len(text) > 20 and text.lower() not in seen:
                    seen.add(text.lower())
                    result["pros"].append(text[:250])

    # Cons — under "What do you dislike?"
    seen_cons: set[str] = set()
    for heading in soup.find_all(string=re.compile(r"dislike|don.?t like", re.IGNORECASE)):
        parent = heading.find_parent()
        if parent:
            sibling = parent.find_next_sibling()
            if sibling:
                text = sibling.get_text(strip=True)
                if text and len(text) > 20 and text.lower() not in seen_cons:
                    seen_cons.add(text.lower())
                    result["cons"].append(text[:250])

    # Recent snippets — substantive paragraphs
    for p in soup.find_all('p'):
        text = p.get_text(strip=True)
        if 60 < len(text) < 350 and text not in result["recent_snippets"]:
            result["recent_snippets"].append(text)
        if len(result["recent_snippets"]) >= 6:
            break

    result["pros"] = result["pros"][:5]
    result["cons"] = result["cons"][:5]

    has_data = result["rating"] or result["pros"] or result["cons"] or result["recent_snippets"]
    return result if has_data else None

# ── Trustpilot scraper ────────────────────────────────────────────────────────

def scrape_trustpilot(company_url: str) -> dict | None:
    """
    Scrape Trustpilot for a company derived from its website domain.
    Attempts https://www.trustpilot.com/review/{domain}
    Returns structured data or None if not found / unusable.
    """
    domain = _domain(company_url)
    tp_url = f"https://www.trustpilot.com/review/{domain}"

    html, status = _playwright_fetch(tp_url)
    if not html:
        return None

    soup = BeautifulSoup(html, 'html.parser')
    page_text = soup.get_text(separator=' ')

    result: dict = {
        "url": tp_url,
        "trust_score": None,
        "rating_label": None,
        "review_count": None,
        "recent_snippets": [],
    }

    # TrustScore — e.g. "TrustScore 4.2"
    score_match = re.search(r'TrustScore\s+([\d.]+)', page_text)
    if score_match:
        result["trust_score"] = float(score_match.group(1))
    else:
        # Fallback: bare rating number near "out of 5"
        fallback = re.search(r'(\d+\.\d+)\s*out of\s*5', page_text)
        if fallback:
            result["trust_score"] = float(fallback.group(1))

    # Rating label
    for label in ['Excellent', 'Great', 'Good', 'Average', 'Bad', 'Poor']:
        if label in page_text:
            result["rating_label"] = label
            break

    # Review count
    count_match = re.search(r'([\d,]+)\s*(?:total\s+)?reviews?', page_text, re.IGNORECASE)
    if count_match:
        result["review_count"] = int(count_match.group(1).replace(',', ''))

    # Recent review snippets — paragraphs with review-related classes
    seen: set[str] = set()
    for p in soup.find_all('p'):
        classes = ' '.join(p.get('class') or []).lower()
        text = p.get_text(strip=True)
        if ('review' in classes or 'text' in classes) and 30 < len(text) < 400:
            if text.lower() not in seen:
                seen.add(text.lower())
                result["recent_snippets"].append(text)

    # Fallback: any substantive paragraphs
    if not result["recent_snippets"]:
        for p in soup.find_all('p'):
            text = p.get_text(strip=True)
            if 50 < len(text) < 300 and text.lower() not in seen:
                seen.add(text.lower())
                result["recent_snippets"].append(text)
            if len(result["recent_snippets"]) >= 6:
                break

    has_data = result["trust_score"] or result["review_count"]
    return result if has_data else None

# ── Unified entry point ───────────────────────────────────────────────────────

def scrape_all_reviews(company_url: str) -> dict:
    """
    Attempt to scrape both G2 and Trustpilot for a given company URL.
    Returns a dict with 'g2' and 'trustpilot' keys; values are None if not found.
    """
    print(f"  Scraping G2 for {company_url}...")
    g2 = scrape_g2(company_url)

    print(f"  Scraping Trustpilot for {company_url}...")
    tp = scrape_trustpilot(company_url)

    return {"g2": g2, "trustpilot": tp}
