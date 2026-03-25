from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import os
import json
import sys

# Ensure stdout/stderr can handle UTF-8 on Windows (avoids UnicodeEncodeError for
# non-ASCII characters in print statements when the console uses cp1252).
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from backend.scraper import fetch_html, extract_data, save_snapshot
from backend.review_scraper import scrape_all_reviews
from backend.diff_engine import generate_diff
from backend.insight_engine import generate_insights, detect_whitespace
from backend.seed_engine import seed_snapshots, get_tracked_urls

app = FastAPI(title="Competitor AI Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
        html = fetch_html(url)
        if not html:
            continue

        data = extract_data(html, url)
        if not data:
            continue

        # Enrich with review platform data
        if req.include_reviews:
            reviews = scrape_all_reviews(url)
            data["reviews"] = reviews
        else:
            data["reviews"] = {"g2": None, "trustpilot": None}

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
    return generate_diff()


@app.get("/api/insights")
def get_insights():
    diff = generate_diff()
    if diff.get("status") == "error":
        return {"insights": [], "whitespace": []}

    insights_res = generate_insights(diff)
    whitespace_res = detect_whitespace()

    return {
        "insights": insights_res.get("insights", []),
        "whitespace": whitespace_res.get("whitespace", []),
    }
