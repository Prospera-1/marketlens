import json
import re
import requests # type: ignore
from bs4 import BeautifulSoup # type: ignore
from datetime import datetime
import os
import argparse
import warnings
from urllib3.exceptions import InsecureRequestWarning  # type: ignore
from backend.clean_data import clean_text_list  # type: ignore

warnings.simplefilter('ignore', InsecureRequestWarning)

_FETCH_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# ── HTML fetch ────────────────────────────────────────────────────────────────

def fetch_html(url: str) -> str | None:
    print(f"Fetching {url}...")
    try:
        response = requests.get(url, headers=_FETCH_HEADERS, timeout=15, verify=False)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

# ── DOM pre-processing ────────────────────────────────────────────────────────

def _remove_chrome(soup: BeautifulSoup) -> BeautifulSoup:
    """Strip nav/header/footer/script chrome so content extractors only see body."""
    nav_indicators = {'nav', 'navigation', 'menu', 'header', 'footer', 'sidebar', 'breadcrumb'}

    to_remove: set[int] = set()

    for tag in soup.find_all(['nav', 'header', 'footer', 'script', 'style', 'noscript']):
        to_remove.add(id(tag))

    for tag in soup.find_all(True):
        tag_id = (tag.get('id') or '').lower()
        tag_classes = ' '.join(tag.get('class') or []).lower()
        combined = f"{tag_id} {tag_classes}"
        if any(ind in combined for ind in nav_indicators):
            to_remove.add(id(tag))

    # Only decompose tags still in the tree; guards against already-destroyed children
    for tag in soup.find_all(True):
        if id(tag) in to_remove and tag.parent is not None:
            tag.decompose()

    return soup

# ── Signal extractors ─────────────────────────────────────────────────────────

def _extract_meta_description(soup: BeautifulSoup) -> str:
    """Extract the brand's positioning statement from meta tags."""
    for attrs in [
        {'name': 'description'},
        {'property': 'og:description'},
        {'name': 'twitter:description'},
    ]:
        tag = soup.find('meta', attrs)
        if tag and tag.get('content'):
            return tag['content'].strip()
    return ""


def _extract_hero_text(soup: BeautifulSoup) -> list[str]:
    """Extract above-the-fold / hero section content."""
    hero_keywords = {'hero', 'banner', 'jumbotron', 'masthead', 'headline', 'above-fold', 'intro', 'lead'}
    texts: list[str] = []
    seen: set[str] = set()

    for tag in soup.find_all(['section', 'div', 'article']):
        combined = f"{(tag.get('id') or '')} {' '.join(tag.get('class') or [])}".lower()
        if any(kw in combined for kw in hero_keywords):
            for el in tag.find_all(['h1', 'h2', 'p'], limit=6):
                text = el.get_text(strip=True)
                if text and len(text) > 10 and text.lower() not in seen:
                    seen.add(text.lower())
                    texts.append(text)
            if texts:
                return texts[:6]

    # Fallback: first h1 on the page
    h1 = soup.find('h1')
    if h1:
        text = h1.get_text(strip=True)
        if text and text.lower() not in seen:
            texts.append(text)

    return texts[:6]


def _extract_ctas(soup: BeautifulSoup) -> list[str]:
    """Extract calls-to-action from buttons and button-like anchor tags.

    Strict rules to avoid picking up content links:
    - Max 6 words (real CTAs are short)
    - <button> tags always considered; <a> tags only if they have button-like classes
      or are very short (≤ 4 words)
    """
    cta_keywords = {
        'free', 'trial', 'demo', 'get started', 'try', 'sign up', 'signup',
        'register', 'buy', 'purchase', 'subscribe', 'join', 'download', 'install',
        'request', 'book', 'schedule', 'contact us', 'learn more', 'watch demo',
        'access', 'unlock', 'claim', 'get a quote', 'get pricing', 'start free',
        'start trial', 'start for free',
    }
    button_class_signals = {'btn', 'button', 'cta', 'pill', 'action', 'primary', 'signup'}
    ctas: list[str] = []
    seen: set[str] = set()

    for tag in soup.find_all(['button', 'a']):
        text = ' '.join(tag.get_text().split())  # normalise whitespace
        if not text or len(text) < 3 or len(text) > 60:
            continue
        word_count = len(text.split())
        if word_count > 6:
            continue
        normalized = text.lower()
        if normalized in seen:
            continue

        is_button = tag.name == 'button'
        tag_classes = ' '.join(tag.get('class') or []).lower()
        has_button_class = any(s in tag_classes for s in button_class_signals)

        # For <a> tags: require button class OR very short text
        if not is_button and not has_button_class and word_count > 4:
            continue

        if any(kw in normalized for kw in cta_keywords):
            seen.add(normalized)
            ctas.append(text)

    return ctas[:15]


def _extract_testimonials(soup: BeautifulSoup) -> list[str]:
    """Extract customer quotes and testimonials."""
    testimonials: list[str] = []
    seen: set[str] = set()

    # Semantic quote elements
    for tag in soup.find_all(['blockquote', 'q']):
        text = tag.get_text(strip=True)
        if text and 30 < len(text) < 500 and text.lower() not in seen:
            seen.add(text.lower())
            testimonials.append(text)

    # Container-based: divs/sections with testimonial/review class patterns
    testimonial_keywords = {'testimonial', 'quote', 'review', 'customer-story', 'case-study', 'social-proof'}
    for container in soup.find_all(['div', 'section', 'article']):
        classes = ' '.join(container.get('class') or []).lower()
        if any(kw in classes for kw in testimonial_keywords):
            for p in container.find_all('p'):
                text = p.get_text(strip=True)
                if text and 40 < len(text) < 400 and text.lower() not in seen:
                    seen.add(text.lower())
                    testimonials.append(text)

    return testimonials[:10]

# ── Cleaning ──────────────────────────────────────────────────────────────────

def clean_scraped_data(headings, features, pricing):
    """Clean raw scraped data using deterministic rules. No API calls."""
    cleaned_headings = clean_text_list(headings, min_len=10, max_len=100)[:15]
    cleaned_features = clean_text_list(features, min_len=15, max_len=120)[:20]
    cleaned_pricing = clean_text_list(pricing, min_len=5, max_len=150, is_price=True)

    # Remove pricing strings that are a strict substring of a longer entry
    final_pricing = [
        p for p in cleaned_pricing
        if not any(p in fp and p != fp for fp in cleaned_pricing)
    ]
    return cleaned_headings, cleaned_features, final_pricing[:15]

# ── Main extractor ────────────────────────────────────────────────────────────

def extract_data(html: str, url: str, is_fallback: bool = False) -> dict | None:
    if not html:
        return None

    soup = BeautifulSoup(html, 'html.parser')

    # Grab signals that live in <head> before stripping chrome
    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    meta_description = _extract_meta_description(soup)

    soup = _remove_chrome(soup)

    # Hero / above-the-fold
    hero_text = _extract_hero_text(soup)

    # Headings (messaging)
    headings: list[str] = []
    for tag in ['h1', 'h2', 'h3']:
        for h_tag in soup.find_all(tag):
            text = h_tag.get_text(strip=True)
            if text and text not in headings:
                headings.append(text)

    # CTAs
    ctas = _extract_ctas(soup)

    # Features — <li> items from content areas only (nav already stripped)
    features: list[str] = []
    for li in soup.find_all('li'):
        text = li.get_text(separator=' ', strip=True)
        if text and len(text) > 15 and text not in features:
            features.append(text)

    # Testimonials
    testimonials = _extract_testimonials(soup)

    # Pricing — covers Western and Indian currency formats; includes <td> for tables
    pricing: list[str] = []
    pricing_keywords = ['price', 'pricing', 'plan', '$', '\u20b9', 'lakh', 'rs.', 'month', 'year', '/mo']
    for elem in soup.find_all(['div', 'p', 'span', 'li', 'td', 'h2', 'h3', 'h4']):
        text = elem.get_text(separator=' ', strip=True)
        if any(kw in text.lower() for kw in pricing_keywords) and len(text) < 200:
            if text not in pricing:
                pricing.append(text)

    # Playwright fallback for JS-rendered SPAs
    if not is_fallback and (not headings or len(features) < 3):
        print(f"WARNING: Insufficient static data for {url}. Falling back to Playwright...")
        try:
            from playwright.sync_api import sync_playwright  # type: ignore
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, wait_until="networkidle", timeout=20000)
                pw_html = page.content()
                browser.close()
            return extract_data(pw_html, url, is_fallback=True)
        except ImportError:
            print("WARNING: Playwright not installed.")
        except Exception as e:
            print(f"WARNING: Playwright fallback failed for {url}: {e}")

    cleaned_headings, cleaned_features, final_pricing = clean_scraped_data(headings, features, pricing)

    return {
        "url": url,
        "source_type": "landing_page",
        "title": title,
        "meta_description": meta_description,
        "hero_text": hero_text,
        "headings": cleaned_headings,
        "ctas": ctas,
        "features": cleaned_features,
        "pricing": final_pricing,
        "testimonials": testimonials,
    }

# ── Snapshot persistence ──────────────────────────────────────────────────────

def save_snapshot(data: list) -> str | None:
    if not data:
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs('backend/data/snapshots', exist_ok=True)
    filename = f"backend/data/snapshots/snapshot_{timestamp}.json"

    snapshot_data = {
        "timestamp": datetime.now().isoformat(),
        "competitors_data": data
    }

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(snapshot_data, f, indent=2, ensure_ascii=False)

    print(f"\nSnapshot saved to {filename}")
    return filename

# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Competitor Website Scraper')
    parser.add_argument('urls', metavar='URL', type=str, nargs='*')
    args = parser.parse_args()
    urls = args.urls

    if not urls:
        print("Competitor Scraper\n------------------")
        while True:
            url = input("Enter a competitor URL (or press Enter to finish): ").strip()
            if not url:
                break
            if not url.startswith('http'):
                url = 'https://' + url
            urls.append(url)

    if not urls:
        print("No URLs provided. Exiting.")
        return

    all_extracted_data = []
    for url in urls:
        html = fetch_html(url)
        if html:
            data = extract_data(html, url)
            if data:
                all_extracted_data.append(data)
                print(f"Successfully extracted data from {url}")

    if all_extracted_data:
        save_snapshot(all_extracted_data)


if __name__ == '__main__':
    main()
