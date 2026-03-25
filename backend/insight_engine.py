import os
import json
from google import genai
from typing import Dict, Any

from backend.diff_engine import get_latest_two_snapshots

def generate_insights(diff_data: Dict[str, Any]) -> Dict[str, Any]:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
         return {"error": "GEMINI_API_KEY required for insights"}
         
    client = genai.Client(api_key=api_key)
    
    changes = diff_data.get("changes", [])
    if not changes:
        return {"insights": [], "message": "No changes detected to analyze."}

    prompt = f"""
    You are an expert Strategy Consultant evaluating competitor changes.
    Here are the raw changes detected between the latest web snapshots of competitors:
    {json.dumps(changes, indent=2)}

    Task 1: Generate 2-4 High-Impact Insights explaining *why* they made these changes (e.g. "Shift toward AI positioning"). Include traceability back to the source URL.
    Task 2 (Insight Scoring): Score each insight from 1-10 based on Novelty, Frequency, and Importance.
    Task 3: Recommend 1 strict Action based on each insight.
    
    Output strictly in this JSON format:
    {{
      "insights": [
        {{
          "title": "Short title",
          "description": "Explanation",
          "score": 8,
          "source_urls": ["https://example.com"],
          "action": "Recommended action for our company"
        }}
      ]
    }}
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        
        raw_text = response.text.strip()
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        elif raw_text.startswith("```"):
            raw_text = raw_text[3:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
            
        result = json.loads(raw_text.strip())
        return result
    except Exception as e:
        print(f"Insight Generation Error: {e}")
        return {"insights": [], "error": str(e)}

def detect_whitespace() -> Dict[str, Any]:
    snapshots_dir = os.path.join("backend", "data", "snapshots")
    latest, _ = get_latest_two_snapshots(snapshots_dir)
    
    if not latest:
        return {"whitespace": []}
        
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
         return {"error": "GEMINI_API_KEY required for whitespace detection"}
         
    client = genai.Client(api_key=api_key)
    data = latest.get("competitors_data", [])
    
    prompt = f"""
    You are a strategy engine identifying 'Whitespace' (unserved market niches/features).
    Here is the full data of our competitors:
    {json.dumps(data, indent=2)}
    
    Identify 2-3 specific things NO ONE in this list is doing but customers might want (e.g., "No one offers a free tier combined with AI tools").
    
    Output strictly in this JSON format:
    {{
      "whitespace": [
        "Description of unserved niche 1",
        "Description of unserved niche 2"
      ]
    }}
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        
        raw_text = response.text.strip()
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        elif raw_text.startswith("```"):
            raw_text = raw_text[3:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
            
        result = json.loads(raw_text.strip())
        return result
    except Exception as e:
        print(f"Whitespace Generation Error: {e}")
        return {"whitespace": []}
