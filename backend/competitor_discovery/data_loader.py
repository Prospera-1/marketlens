import json
import logging
import os
from functools import lru_cache
from typing import Any, Dict, List, Tuple


logger = logging.getLogger("competitor_discovery")


def _get_data_dir() -> str:
    """
    Default data directory: backend/data
    Can be overridden with COMPETITOR_DATA_DIR for quick experimentation.
    """

    override = os.environ.get("COMPETITOR_DATA_DIR")
    if override:
        return os.path.abspath(override)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))


def _json_path(filename: str) -> str:
    return os.path.join(_get_data_dir(), filename)


def _load_json_file(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _validate_companies(companies: Any) -> Dict[str, List[Dict[str, str]]]:
    if not isinstance(companies, dict):
        raise ValueError("companies.json must be a JSON object keyed by industry")

    validated: Dict[str, List[Dict[str, str]]] = {}
    for industry, entries in companies.items():
        if not isinstance(industry, str):
            continue
        if not isinstance(entries, list):
            raise ValueError(f"companies.json[{industry!r}] must be a list")
        normalized_entries: List[Dict[str, str]] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            name = entry.get("name")
            url = entry.get("url")
            if not isinstance(name, str) or not isinstance(url, str):
                continue
            normalized_entries.append({"name": name, "url": url})
        validated[industry] = normalized_entries

    return validated


def _validate_industry_map(industry_map: Any) -> Dict[str, str]:
    if not isinstance(industry_map, dict):
        raise ValueError("industry_map.json must be a JSON object keyed by company (lowercase)")
    out: Dict[str, str] = {}
    for company_key, industry in industry_map.items():
        if not isinstance(company_key, str) or not isinstance(industry, str):
            continue
        out[company_key.strip().lower()] = industry
    return out


@lru_cache(maxsize=1)
def load_dataset() -> Tuple[Dict[str, List[Dict[str, str]]], Dict[str, str], Dict[str, str]]:
    """
    Loads:
      - companies.json: industry -> [{name, url}, ...]
      - industry_map.json: company(lowercase) -> industry
    Returns:
      companies_by_industry, industry_map, company_url_lookup(lowercase -> url)
    """

    companies_path = _json_path("companies.json")
    industry_map_path = _json_path("industry_map.json")

    companies_raw = _load_json_file(companies_path)
    industry_map_raw = _load_json_file(industry_map_path)

    companies_by_industry = _validate_companies(companies_raw)
    industry_map = _validate_industry_map(industry_map_raw)

    company_url_lookup: Dict[str, str] = {}
    for _, entries in companies_by_industry.items():
        for entry in entries:
            company_url_lookup[entry["name"].strip().lower()] = entry["url"].strip()

    if not companies_by_industry:
        raise ValueError("No companies found in companies.json")
    if not industry_map:
        raise ValueError("No entries found in industry_map.json")
    if not company_url_lookup:
        raise ValueError("No company URLs found in companies.json")

    logger.info(
        "Loaded competitor dataset: %d industries, %d companies",
        len(companies_by_industry),
        len(company_url_lookup),
    )

    return companies_by_industry, industry_map, company_url_lookup

