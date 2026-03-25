import logging
import os
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException, Query

from backend.competitor_discovery.competitor_engine import (
    CompanyNotFoundError,
    IndustryMissingError,
    CompetitorDiscoveryError,
    get_competitors,
)
from backend.competitor_discovery.url_resolver import UrlFetchFailureError


def _configure_logging() -> None:
    debug_enabled = os.environ.get("COMPETITOR_DEBUG", "").lower() in {"1", "true", "yes", "y"}
    level = logging.DEBUG if debug_enabled else logging.INFO

    # Avoid duplicate handlers when running with reloaders.
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    else:
        root.setLevel(level)


_configure_logging()

app = FastAPI(title="Deterministic Competitor Discovery API")


@app.get("/get-competitors")
def get_competitors_endpoint(company: str = Query(..., description="Company name (e.g. Hyundai, Slack)")) -> Dict[str, Any]:
    """
    Returns:
      {
        "target": "...",
        "industry": "...",
        "competitors": [{"name": "...", "url": "..."}]
      }
    """

    try:
        return get_competitors(company)
    except CompanyNotFoundError as e:
        payload: Dict[str, Any] = {"error": str(e)}
        if e.suggestions:
            payload["suggestions"] = e.suggestions
        raise HTTPException(status_code=404, detail=payload)
    except IndustryMissingError as e:
        raise HTTPException(status_code=500, detail={"error": str(e)})
    except UrlFetchFailureError as e:
        raise HTTPException(status_code=502, detail={"error": str(e)})
    except CompetitorDiscoveryError as e:
        raise HTTPException(status_code=400, detail={"error": str(e)})
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": f"Unexpected error: {e}"})

