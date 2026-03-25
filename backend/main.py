from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import os
import json

from backend.scraper import fetch_html, extract_data, save_snapshot
from backend.diff_engine import generate_diff
from backend.insight_engine import generate_insights, detect_whitespace

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
        if html:
            data = extract_data(html, url)
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
    files.sort(reverse=True) # newest first
    
    snapshots = []
    for f in files:
        filepath = os.path.join(snapshots_dir, f)
        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                data = json.load(file)
                snapshots.append(data)
        except Exception as e:
            print(f"Error reading {f}: {e}")
            
    return {"snapshots": snapshots}

@app.get("/api/diff")
def get_diff():
    diff = generate_diff()
    return diff
    
@app.get("/api/insights")
def get_insights():
    diff = generate_diff()
    if diff.get("status") == "error":
        return {"insights": [], "whitespace": []}
        
    insights_res = generate_insights(diff)
    whitespace_res = detect_whitespace()
    
    return {
        "insights": insights_res.get("insights", []),
        "whitespace": whitespace_res.get("whitespace", [])
    }
