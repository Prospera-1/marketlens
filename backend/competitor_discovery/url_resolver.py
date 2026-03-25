import difflib
import logging
import os
from typing import Dict, List, Optional
from urllib.parse import parse_qs, urlparse

import requests
from bs4 import BeautifulSoup

from backend.competitor_discovery.data_loader import load_dataset


logger = logging.getLogger("competitor_discovery")


class UrlFetchFailureError(RuntimeError):
    pass


def _debug_enabled() -> bool:
    return os.environ.get("COMPETITOR_DEBUG", "").lower() in {"1", "true", "yes", "y"}


def _log_debug(message: str, *args: object) -> None:
    if _debug_enabled():
        logger.debug(message, *args)


def _extract_google_first_result_url(html: str) -> Optional[str]:
    """
    Attempts to extract the first "real" result URL from a Google search response.

    Note: Google HTML can change; this uses a best-effort heuristic:
    - Look for anchors with href like /url?q=<target>&...
    - Extract and return the q= parameter.
    """

    soup = BeautifulSoup(html, "html.parser")
    for a in soup.select("a[href]"):
        href = a.get("href") or ""
        if not href:
            continue

        # Common pattern: /url?q=https://example.com&sa=...
        if "/url?" in href:
            parsed = urlparse(href)
            qs = parse_qs(parsed.query)
            target = qs.get("q", [None])[0]
            if isinstance(target, str) and target.startswith("http"):
                return target

        # Fallback: sometimes direct http(s) links appear.
        if href.startswith("http"):
            return href

    return None


def resolve_url(company_name: str) -> str:
    """
    Deterministic first: if the company exists in our dataset, return its URL.

    Fallback:
      - If the exact company is missing, use difflib to suggest the closest match
        from dataset keys and return that URL.
      - If still missing (no good match), perform a Google search and take the
        first result URL.
    """

    companies_by_industry, industry_map, company_url_lookup = load_dataset()
    _ = companies_by_industry  # kept for potential future extensions

    normalized = (company_name or "").strip().lower()
    if not normalized:
        raise UrlFetchFailureError("Empty company_name for URL resolution")

    _log_debug("URL resolver step: company=%r normalized=%r", company_name, normalized)

    # 1) Exact match in dataset
    exact_url = company_url_lookup.get(normalized)
    if exact_url:
        _log_debug("URL resolver: exact match found for %r", normalized)
        return exact_url

    # 2) Fuzzy match within dataset keys
    close_matches: List[str] = difflib.get_close_matches(
        normalized, list(company_url_lookup.keys()), n=1, cutoff=0.6
    )
    if close_matches:
        closest = close_matches[0]
        _log_debug("URL resolver: fuzzy match closest=%r for %r", closest, normalized)
        return company_url_lookup[closest]

    # 3) Google search fallback
    query = f"official website of {company_name}"
    _log_debug("URL resolver: running Google search query=%r", query)

    google_url = "https://www.google.com/search"
    headers = {
        # Helps with bot detection; still no guarantee Google will return results.
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        )
    }

    try:
        resp = requests.get(
            google_url,
            params={"q": query, "num": 1},
            headers=headers,
            timeout=20,
        )
        resp.raise_for_status()
    except Exception as e:
        raise UrlFetchFailureError(f"URL fetch failure: Google request failed: {e}") from e

    first_url = _extract_google_first_result_url(resp.text)
    if not first_url:
        raise UrlFetchFailureError("URL fetch failure: no result URL extracted from Google HTML")

    _log_debug("URL resolver: extracted first result url=%r", first_url)
    return first_url

