import json
import os
from typing import List, Dict, Any, Tuple

def get_latest_two_snapshots(snapshots_dir: str) -> Tuple[Dict|None, Dict|None]:
    if not os.path.exists(snapshots_dir):
        return None, None
        
    files = [f for f in os.listdir(snapshots_dir) if f.endswith('.json')]
    files.sort(reverse=True) # newest first
    
    if len(files) < 2:
        return None, None
        
    def load_json(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
            
    latest = load_json(os.path.join(snapshots_dir, files[0]))
    previous = load_json(os.path.join(snapshots_dir, files[1]))
    
    return latest, previous

def normalize_list(lst: List[str]) -> set:
    return set([item.lower().strip() for item in lst])

def generate_diff() -> Dict[str, Any]:
    snapshots_dir = os.path.join("backend", "data", "snapshots")
    latest, previous = get_latest_two_snapshots(snapshots_dir)
    
    if not latest or not previous:
        return {"status": "error", "message": "Need at least 2 snapshots to generate a diff"}
        
    latest_data = {comp["url"]: comp for comp in latest.get("competitors_data", [])}
    prev_data = {comp["url"]: comp for comp in previous.get("competitors_data", [])}
    
    changes = []
    
    for url, current_comp in latest_data.items():
        if url not in prev_data:
            changes.append({
                "url": url,
                "type": "new_competitor",
                "description": f"New competitor detected: {current_comp.get('title', url)}"
            })
            continue
            
        old_comp = prev_data[url]
        brand = current_comp.get('title', url)
        
        # Check Pricing
        old_pricing = normalize_list(old_comp.get('pricing', []))
        new_pricing = normalize_list(current_comp.get('pricing', []))
        
        added_pricing = new_pricing - old_pricing
        removed_pricing = old_pricing - new_pricing
        
        if added_pricing or removed_pricing:
            changes.append({
                "url": url,
                "brand": brand,
                "category": "Pricing",
                "added": list(added_pricing),
                "removed": list(removed_pricing),
                "description": f"{brand} updated their pricing."
            })
            
        # Check Features
        old_features = normalize_list(old_comp.get('features', []))
        new_features = normalize_list(current_comp.get('features', []))
        
        added_features = new_features - old_features
        removed_features = old_features - new_features
        
        if added_features or removed_features:
            changes.append({
                "url": url,
                "brand": brand,
                "category": "Features",
                "added": list(added_features),
                "removed": list(removed_features),
                "description": f"{brand} updated their feature list."
            })
            
        # Check Messaging (Headings)
        old_headings = normalize_list(old_comp.get('headings', []))
        new_headings = normalize_list(current_comp.get('headings', []))
        
        added_headings = new_headings - old_headings
        removed_headings = old_headings - new_headings
        
        if added_headings or removed_headings:
            changes.append({
                "url": url,
                "brand": brand,
                "category": "Messaging",
                "added": list(added_headings),
                "removed": list(removed_headings),
                "description": f"{brand} updated their messaging/headings."
            })
            
    return {
        "status": "success",
        "timestamp_latest": latest.get("timestamp"),
        "timestamp_previous": previous.get("timestamp"),
        "changes": changes
    }
