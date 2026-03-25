"""
crawler.py — Smart shallow crawler for competitor intelligence.

Strategy (two-pass link discovery):
  Pass 1 — Nav harvest:  Extract links from <nav>, <header>, and top-level
            menus BEFORE chrome is stripped.  These are the pages the company
            considers most important.

  Pass 2 — URL scoring:  Score every remaining internal <a href> by how
            likely the URL path is to contain intelligence signals.
            e.g. /pricing → 10,  /features → 9,  /about → 7

  Combined: deduplicate, sort by score, take up to MAX_SUBPAGES.

Then scrape each sub-page, merge all extracted data into one rich profile.

The merged profile has the same shape as a single-page extract so the rest
of the pipeline (diff, scoring, positioning) needs no changes.
"""

from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup  # type: ignore
from typing import List, Dict, Any

from backend.scraper import fetch_html, extract_data

# ── Config ────────────────────────────────────────────────────────────────────

MAX_SUBPAGES = 5   # max additional pages to crawl beyond the root

# URL-path keyword scores (higher = more likely to contain intelligence)
_PATH_SCORES: Dict[str, int] = {
    # Pricing / plans
    'pricing':   10, 'price':    10, 'prices':   10,
    'plans':     10, 'plan':     10, 'packages': 10,
    'subscribe': 9,  'billing':   9,
    # Products / features
    'features':  9,  'feature':   9,
    'product':   9,  'products':  9,
    'solutions': 8,  'solution':  8,
    'platform':  8,  'overview':  7,
    # Cars / models (automotive)
    'cars':      9,  'models':    9,  'model':    9,
    'suv':       8,  'sedan':     8,  'hatchback':8,
    'ev':        8,  'electric':  8,
    # About / company
    'about':     7,  'company':   7,  'who-we-are':7,
    # Compare
    'compare':   8,  'vs':        7,  'versus':   7,
    # Use cases / customers
    'use-cases': 7,  'customers': 7,  'case-studies':6,
    'enterprise':6,  'teams':     6,
}

# Paths to exclude — these pages are primarily transactional/service and add
# mostly noise (booking calendars, accessory lists, dealer locators, etc.)
_EXCLUDED_PATH_FRAGMENTS = {
    'accessories', 'accessory', 'service', 'dealer', 'locator',
    'careers', 'career', 'jobs', 'press', 'newsroom', 'blog',
    'sitemap', 'privacy', 'terms', 'legal', 'cookie', 'faq',
    'test-drive', 'booking', 'book-a', 'contact', 'support',
    'login', 'signin', 'signup', 'register', 'account',
    'investor', 'csr', 'sustainability',
}

# Link text hints (anchor text that suggests a high-value page)
_TEXT_SCORES: Dict[str, int] = {
    'pricing':   10, 'price':    10, 'plans':    10, 'packages': 10,
    'features':  9,  'products':  9,  'solutions': 8,
    'models':    8,  'cars':      8,  'compare':   8,
    'about':     6,  'overview':  6,
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _same_domain(href: str, base: str) -> bool:
    """True if href belongs to the same host as base (or is root-relative)."""
    if href.startswith('/'):
        return True
    try:
        return urlparse(href).netloc == urlparse(base).netloc
    except Exception:
        return False


def _score_link(path: str, text: str) -> int:
    """Return an intelligence-relevance score for a link. Returns 0 to exclude."""
    path_lower = path.lower()
    text_lower = text.lower().strip()

    # Hard-exclude noisy/transactional pages
    path_parts = set(path_lower.strip('/').replace('-', '_').split('/'))
    for fragment in _EXCLUDED_PATH_FRAGMENTS:
        if fragment.replace('-', '_') in path_lower:
            return 0

    score = 0
    for kw, s in _PATH_SCORES.items():
        if kw in path_lower:
            score = max(score, s)

    for kw, s in _TEXT_SCORES.items():
        if kw in text_lower:
            score = max(score, s)

    return score


def _is_ignorable(href: str) -> bool:
    """Skip anchors, mailto, tel, file downloads, and social links."""
    skip_prefixes = ('#', 'mailto:', 'tel:', 'javascript:', 'data:')
    skip_extensions = ('.pdf', '.zip', '.jpg', '.png', '.gif', '.svg',
                       '.mp4', '.mp3', '.xml', '.json')
    skip_domains = ('facebook.com', 'twitter.com', 'instagram.com',
                    'linkedin.com', 'youtube.com', 't.co', 'x.com')

    if any(href.startswith(p) for p in skip_prefixes):
        return True
    if any(href.lower().endswith(ext) for ext in skip_extensions):
        return True
    if any(d in href for d in skip_domains):
        return True
    return False


# ── Core discovery ────────────────────────────────────────────────────────────

def discover_subpages(html: str, base_url: str) -> List[str]:
    """
    Return a ranked list of sub-page URLs to crawl, up to MAX_SUBPAGES.

    Pass 1: harvest links from <nav> and <header> elements (nav-first).
    Pass 2: score all remaining internal links by URL path keywords.
    """
    soup = BeautifulSoup(html, 'html.parser')
    base_domain = urlparse(base_url).netloc
    scored: Dict[str, int] = {}  # url → best score

    def _register(tag):
        href = tag.get('href', '')
        if not href or _is_ignorable(href):
            return
        if not _same_domain(href, base_url):
            return
        full = urljoin(base_url, href).split('#')[0].rstrip('/')
        # Skip the root URL itself
        if full.rstrip('/') == base_url.rstrip('/'):
            return
        text = tag.get_text(strip=True)
        path = urlparse(full).path
        s = _score_link(path, text)
        if s > 0:
            scored[full] = max(scored.get(full, 0), s)

    # Pass 1: nav / header links get a +2 bonus (the company prioritises these)
    for container in soup.find_all(['nav', 'header']):
        for a in container.find_all('a', href=True):
            href = a.get('href', '')
            if not href or _is_ignorable(href):
                continue
            if not _same_domain(href, base_url):
                continue
            full = urljoin(base_url, href).split('#')[0].rstrip('/')
            if full.rstrip('/') == base_url.rstrip('/'):
                continue
            text = a.get_text(strip=True)
            path = urlparse(full).path
            s = _score_link(path, text)
            if s > 0:
                scored[full] = max(scored.get(full, 0), s + 2)  # nav bonus

    # Pass 2: all other internal links
    for a in soup.find_all('a', href=True):
        _register(a)

    # Sort by score descending, take top MAX_SUBPAGES
    ranked = sorted(scored.items(), key=lambda x: x[1], reverse=True)
    return [url for url, _ in ranked[:MAX_SUBPAGES]]


# ── Data merger ───────────────────────────────────────────────────────────────

def _dedup_list(items: List[str]) -> List[str]:
    """Deduplicate a list preserving order, case-insensitive."""
    seen = set()
    out = []
    for item in items:
        key = item.lower().strip()
        if key and key not in seen:
            seen.add(key)
            out.append(item)
    return out


def merge_pages(pages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Merge extracted data from multiple pages of the same competitor.

    Rules:
    - title, meta_description, hero_text → from the root page (index 0)
    - pricing, features, headings, ctas, testimonials → deduplicated union
    - reviews → from root page
    - pages_crawled → list of URLs that were successfully scraped
    """
    if not pages:
        return {}
    if len(pages) == 1:
        result = dict(pages[0])
        result['pages_crawled'] = [pages[0].get('url', '')]
        return result

    root = pages[0]

    # Accumulate list fields across all pages
    list_fields = ['pricing', 'features', 'headings', 'ctas', 'testimonials']
    merged_lists: Dict[str, List[str]] = {f: [] for f in list_fields}
    for page in pages:
        for field in list_fields:
            merged_lists[field].extend(page.get(field) or [])

    return {
        # Identity / above-fold from root only
        'url':              root.get('url'),
        'source_type':      root.get('source_type', 'landing_page'),
        'title':            root.get('title'),
        'meta_description': root.get('meta_description'),
        'hero_text':        root.get('hero_text') or [],
        # Merged list signals
        'pricing':      _dedup_list(merged_lists['pricing'])[:20],
        'features':     _dedup_list(merged_lists['features'])[:30],
        'headings':     _dedup_list(merged_lists['headings'])[:20],
        'ctas':         _dedup_list(merged_lists['ctas'])[:20],
        'testimonials': _dedup_list(merged_lists['testimonials'])[:15],
        # Reviews always from root
        'reviews':      root.get('reviews', {'g2': None, 'trustpilot': None}),
        # Audit trail
        'pages_crawled': [p.get('url') for p in pages if p.get('url')],
    }


# ── Public entry point ────────────────────────────────────────────────────────

def crawl_competitor(root_url: str, include_reviews: bool = False) -> Dict[str, Any] | None:
    """
    Crawl a competitor starting from root_url, discover and scrape key
    sub-pages, then return a single merged intelligence profile.

    Args:
        root_url:        The URL entered by the user.
        include_reviews: Whether to attach G2/Trustpilot data (slow).

    Returns:
        Merged competitor profile dict, or None if root page fails.
    """
    # ── Step 1: fetch and extract root page ──────────────────────────────────
    print(f"\nCrawling: {root_url}")
    root_html = fetch_html(root_url)
    if not root_html:
        return None

    root_data = extract_data(root_html, root_url)
    if not root_data:
        return None

    # ── Step 2: discover sub-pages ───────────────────────────────────────────
    subpages = discover_subpages(root_html, root_url)
    if subpages:
        print(f"  Discovered {len(subpages)} sub-page(s): {subpages}")
    else:
        print("  No high-value sub-pages found — using root page only.")

    # ── Step 3: scrape each sub-page ─────────────────────────────────────────
    all_pages = [root_data]
    for url in subpages:
        print(f"  Scraping sub-page: {url}")
        html = fetch_html(url)
        if not html:
            print(f"    SKIP (fetch failed): {url}")
            continue
        data = extract_data(html, url)
        if data:
            all_pages.append(data)

    print(f"  Merged {len(all_pages)} page(s) for {root_url}")

    # ── Step 4: merge all pages into one profile ──────────────────────────────
    merged = merge_pages(all_pages)

    # ── Step 5: attach reviews to merged profile ──────────────────────────────
    if include_reviews:
        from backend.review_scraper import scrape_all_reviews
        merged['reviews'] = scrape_all_reviews(root_url)

    return merged
