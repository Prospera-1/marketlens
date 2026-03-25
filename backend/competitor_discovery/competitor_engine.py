import difflib
import logging
import os
from typing import Dict, List

from backend.competitor_discovery.data_loader import load_dataset
from backend.competitor_discovery.url_resolver import UrlFetchFailureError, resolve_url


logger = logging.getLogger("competitor_discovery")


def _debug_enabled() -> bool:
    return os.environ.get("COMPETITOR_DEBUG", "").lower() in {"1", "true", "yes", "y"}


def _log_debug(message: str, *args: object) -> None:
    if _debug_enabled():
        logger.debug(message, *args)


class CompetitorDiscoveryError(RuntimeError):
    pass


class CompanyNotFoundError(CompetitorDiscoveryError):
    def __init__(self, target: str, suggestions: List[str] | None = None):
        super().__init__(f"Company not found: {target}")
        self.target = target
        self.suggestions = suggestions or []


class IndustryMissingError(CompetitorDiscoveryError):
    pass


def get_competitors(company_name: str) -> Dict[str, object]:
    """
    Deterministic competitor discovery (no LLM):
      1) Normalize input (lowercase)
      2) Identify industry using industry_map.json
      3) Return all companies in that industry except the input company

    Note: If any competitor URL is missing in the dataset, we use a
    best-effort URL resolver (dataset -> fuzzy -> Google).
    """

    companies_by_industry, industry_map, company_url_lookup = load_dataset()

    target_raw = (company_name or "").strip()
    target_norm = target_raw.lower()
    if not target_norm:
        raise CompanyNotFoundError(target_raw, suggestions=[])

    _log_debug("Industry detection step: target_raw=%r target_norm=%r", target_raw, target_norm)

    industry = industry_map.get(target_norm)
    if not industry:
        # Fuzzy-match company name against dataset keys for better UX.
        keys = list(industry_map.keys())
        close = difflib.get_close_matches(target_norm, keys, n=5, cutoff=0.6)
        suggestions = [s for s in close]
        _log_debug("Company not found: suggestions=%r", suggestions)
        raise CompanyNotFoundError(target_raw, suggestions=suggestions)

    if industry not in companies_by_industry or not companies_by_industry[industry]:
        _log_debug("Industry missing/empty: industry=%r", industry)
        raise IndustryMissingError(f"Industry missing in companies.json: {industry}")

    candidates = companies_by_industry[industry]
    competitors: List[Dict[str, str]] = []

    _log_debug("Industry match step: industry=%r candidates=%d", industry, len(candidates))

    for entry in candidates:
        entry_name = (entry.get("name") or "").strip()
        entry_norm = entry_name.lower()
        if not entry_name or entry_norm == target_norm:
            continue

        url = (entry.get("url") or "").strip()
        if url:
            competitors.append({"name": entry_name, "url": url})
            continue

        # Bonus: deterministic resolver fallback for missing URLs.
        _log_debug("URL missing for competitor=%r; resolving...", entry_name)
        try:
            url = resolve_url(entry_name)
        except UrlFetchFailureError as e:
            # Re-raise as a uniform discovery error so the API can report cleanly.
            raise UrlFetchFailureError(f"URL fetch failure for {entry_name}: {e}") from e
        competitors.append({"name": entry_name, "url": url})

    return {
        "target": target_raw,
        "industry": industry,
        "competitors": competitors,
    }

