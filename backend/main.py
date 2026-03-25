from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import os
import json
import sys
from dotenv import load_dotenv

load_dotenv()  # loads GEMINI_API_KEY (and any other vars) from .env into os.environ

# Ensure stdout/stderr can handle UTF-8 on Windows (avoids UnicodeEncodeError for
# non-ASCII characters in print statements when the console uses cp1252).
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from backend.scraper import save_snapshot
from backend.crawler import crawl_competitor
from backend.diff_engine import generate_diff as compute_diff
from backend.insight_engine import get_cached_insights, generate_and_cache_all
from backend.seed_engine import seed_snapshots, get_tracked_urls
from backend.positioning_engine import build_positioning_map
from backend.trend_engine import build_trends
from backend.ad_scraper import fetch_ads
from backend.competitor_discovery.competitor_engine import (
    CompanyNotFoundError,
    CompetitorDiscoveryError,
    IndustryMissingError,
    get_competitors,
)
from backend.competitor_discovery.url_resolver import UrlFetchFailureError

app = FastAPI(title="Competitor AI Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


snapshots_dir = os.path.join("backend", "data", "snapshots")


class FetchRequest(BaseModel):
    urls: List[str]
    include_reviews: bool = True  # set False to skip G2/Trustpilot scraping for faster runs


class SeedRequest(BaseModel):
    urls: List[str] = []   # if empty, reuses URLs from latest snapshot
    days_ago: int = 7


@app.get("/")
def read_root():
    return {"status": "online", "message": "Competitor API is running"}


@app.post("/api/fetch")
def fetch_competitors(req: FetchRequest):
    if not req.urls:
        raise HTTPException(status_code=400, detail="No URLs provided")

    all_extracted_data = []

    for url in req.urls:
        # crawl_competitor scrapes the root page + up to 5 key sub-pages,
        # then merges all extracted data into one rich profile.
        data = crawl_competitor(url, include_reviews=req.include_reviews)
        if data:
            all_extracted_data.append(data)

    if all_extracted_data:
        saved_file = save_snapshot(all_extracted_data)
        return {"status": "success", "data": all_extracted_data, "snapshot_file": saved_file}

    raise HTTPException(status_code=500, detail="Failed to extract data from any URLs")


@app.get("/api/snapshots")
def get_snapshots():
    snapshots_dir = os.path.join("backend", "data", "snapshots")
    if not os.path.exists(snapshots_dir):
        return {"snapshots": []}

    files = [f for f in os.listdir(snapshots_dir) if f.endswith('.json')]
    files.sort(reverse=True)  # newest first

    snapshots = []
    for f in files:
        filepath = os.path.join(snapshots_dir, f)
        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                snapshots.append(json.load(file))
        except Exception as e:
            print(f"Error reading {f}: {e}")

    return {"snapshots": snapshots}


@app.post("/api/seed")
def seed_demo(req: SeedRequest):
    """
    Create a backdated baseline snapshot for demo purposes.
    Scrapes the given URLs (or reuses the latest snapshot's URLs),
    applies mutations to simulate an older state, and saves as a
    snapshot dated `days_ago` days in the past.
    After seeding, call /api/fetch with the same URLs to generate a
    live snapshot — the diff engine will show realistic changes.
    """
    urls = req.urls or get_tracked_urls()
    if not urls:
        raise HTTPException(status_code=400, detail="No URLs provided and no existing snapshots to reuse.")

    filename = seed_snapshots(urls, days_ago=req.days_ago)
    if not filename:
        raise HTTPException(status_code=500, detail="Failed to seed snapshot — check that URLs are reachable.")

    return {"status": "success", "snapshot_file": filename, "urls_seeded": urls}


@app.get("/api/seed/urls")
def get_seed_urls():
    """Return the URLs tracked in the latest snapshot, for pre-filling the seed form."""
    return {"urls": get_tracked_urls()}


@app.get("/api/diff")
def get_diff():
    return compute_diff()


@app.get("/api/positioning")
def get_positioning():
    """
    Return competitive positioning map for all competitors in the latest snapshot.
    Classifies each competitor on Cost, GTM, and Value-framing axes — no Gemini needed.
    """
    snapshots_dir = os.path.join("backend", "data", "snapshots")
    files = sorted(
        [f for f in os.listdir(snapshots_dir) if f.endswith(".json")],
        reverse=True
    ) if os.path.exists(snapshots_dir) else []

    if not files:
        return {"profiles": [], "axis_leaders": {}, "axes": {}}

    with open(os.path.join(snapshots_dir, files[0]), "r", encoding="utf-8") as f:
        latest = json.load(f)

    competitors = latest.get("competitors_data", [])
    return build_positioning_map(competitors)


@app.get("/api/insights")
def get_insights():
    """Return cached insights + whitespace (no Gemini call). Fast for dashboard loads."""
    return get_cached_insights()


@app.post("/api/insights/generate")
def generate_insights_endpoint():
    """
    Trigger a fresh Gemini generation of insights + whitespace and cache the result.
    Call this explicitly — not on every page load — to avoid quota exhaustion.
    """
    try:
        result = generate_and_cache_all()
        errors = result.pop("errors", [])
        if errors and not result["insights"] and not result["whitespace"]:
            raise HTTPException(status_code=503, detail="; ".join(str(e) for e in errors))
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class AdsRequest(BaseModel):
    keyword: str
    force_refresh: bool = False


@app.post("/api/ads")
def get_ads(req: AdsRequest):
    """
    Scrape Facebook Ad Library for a keyword (public search, no login).
    Results are cached for 6 hours to avoid hammering the public UI.
    """
    try:
        return fetch_ads(req.keyword, force_refresh=req.force_refresh)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/export")
def export_report(format: str = "json"):
    """
    Download the full intelligence report (latest snapshot + diff + positioning + trends).
    format: "json" or "csv"
    """
    try:
        # Gather all data
        snapshot_data = None
        if os.path.exists(snapshots_dir):
            files = sorted(os.listdir(snapshots_dir), reverse=True)
            if files:
                with open(os.path.join(snapshots_dir, files[0]), "r", encoding="utf-8") as f:
                    snapshot_data = json.load(f)

        diff_data       = compute_diff()
        insights_data   = get_cached_insights()
        trends_data     = build_trends()

        positioning_data = {"profiles": [], "axis_leaders": {}, "overused_angles": []}
        if snapshot_data:
            competitors = snapshot_data.get("competitors_data", [])
            positioning_data = build_positioning_map(competitors)

        if format == "csv":
            import io, csv
            output = io.StringIO()
            writer = csv.writer(output)

            writer.writerow(["=== COMPETITORS ==="])
            writer.writerow(["URL", "Title", "Pages Crawled", "Meta Description",
                             "Hero Text", "Pricing", "Features", "CTAs", "Headings"])
            for c in (snapshot_data or {}).get("competitors_data", []):
                writer.writerow([
                    c.get("url", ""),
                    c.get("title", ""),
                    c.get("pages_crawled", 1),
                    c.get("meta_description", ""),
                    "; ".join(c.get("hero_text") or []),
                    "; ".join(c.get("pricing") or []),
                    "; ".join(c.get("features") or []),
                    "; ".join(c.get("ctas") or []),
                    "; ".join(c.get("headings") or []),
                ])

            writer.writerow([])
            writer.writerow(["=== CHANGES (DIFF) ==="])
            writer.writerow(["Competitor", "Field", "Priority", "Score", "Added", "Removed"])
            for ch in diff_data.get("changes", []):
                writer.writerow([
                    ch.get("competitor", ""),
                    ch.get("field", ""),
                    ch.get("priority", ""),
                    ch.get("composite", ""),
                    "; ".join(ch.get("added") or []),
                    "; ".join(ch.get("removed") or []),
                ])

            writer.writerow([])
            writer.writerow(["=== INSIGHTS ==="])
            writer.writerow(["Title", "Description", "Action", "Composite Score"])
            for ins in insights_data.get("insights", []):
                writer.writerow([
                    ins.get("title", ""),
                    ins.get("description", ""),
                    ins.get("action", ""),
                    ins.get("scores", {}).get("composite", ""),
                ])

            writer.writerow([])
            writer.writerow(["=== TRENDS ==="])
            writer.writerow(["Type", "Description", "Significance"])
            for t in trends_data.get("trends", []):
                writer.writerow([t.get("type", ""), t.get("description", ""), t.get("significance", "")])

            writer.writerow([])
            writer.writerow(["=== OVERUSED ANGLES ==="])
            writer.writerow(["Angle", "Saturation %", "Competitors", "Whitespace Hint"])
            for a in positioning_data.get("overused_angles", []):
                writer.writerow([
                    a.get("angle", ""),
                    f"{int(a.get('saturation', 0) * 100)}%",
                    "; ".join(a.get("competitors", [])),
                    a.get("whitespace_hint", ""),
                ])

            from fastapi.responses import StreamingResponse
            output.seek(0)
            return StreamingResponse(
                iter([output.getvalue()]),
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=market_intelligence_report.csv"}
            )

        # Default: JSON
        report = {
            "generated_at":   snapshot_data.get("timestamp") if snapshot_data else None,
            "competitors":     (snapshot_data or {}).get("competitors_data", []),
            "changes":         diff_data.get("changes", []),
            "scoring_summary": diff_data.get("scoring_summary"),
            "insights":        insights_data.get("insights", []),
            "whitespace":      insights_data.get("whitespace", []),
            "trends":          trends_data.get("trends", []),
            "trend_summary":   trends_data.get("summary", {}),
            "positioning":     positioning_data.get("profiles", []),
            "overused_angles": positioning_data.get("overused_angles", []),
        }
        from fastapi.responses import JSONResponse
        return JSONResponse(
            content=report,
            headers={"Content-Disposition": "attachment; filename=market_intelligence_report.json"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/trends")
def get_trends():
    """
    Aggregate all saved snapshots and return trend analysis:
    rising/falling signals, volatile fields, converging themes, and stable baselines.
    """
    try:
        return build_trends()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/get-competitors")
def get_competitors_endpoint(company: str):
    """
    Deterministic competitor discovery (JSON dataset + optional fuzzy / URL fallback).
    Example: /get-competitors?company=Hyundai
    """
    try:
        return get_competitors(company)
    except CompanyNotFoundError as e:
        payload = {"error": str(e)}
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
