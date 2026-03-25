import json
import time
import requests # type: ignore
from bs4 import BeautifulSoup # type: ignore
from datetime import datetime
import os
import argparse
import warnings
from urllib3.exceptions import InsecureRequestWarning  # type: ignore
from dotenv import load_dotenv  # type: ignore

load_dotenv()

# Suppress insecure request warnings for robust scraping
warnings.simplefilter('ignore', InsecureRequestWarning)

def fetch_html(url):
    print(f"Fetching {url}...")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10, verify=False)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def gemini_clean_data(headings, features, pricing):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("⚠️ GEMINI_API_KEY not set. Falling back to manual cleaning script.")
        from backend.clean_data import clean_text_list  # type: ignore
        cleaned_headings = clean_text_list(headings, min_len=10, max_len=100)[:15]  # type: ignore
        cleaned_features = clean_text_list(features, min_len=15, max_len=120)[:20]  # type: ignore
        cleaned_pricing = clean_text_list(pricing, min_len=5, max_len=150, is_price=True)
        final_pricing = []
        for p in cleaned_pricing:
            if not any((p in fp and p != fp) for fp in cleaned_pricing):
                final_pricing.append(p)
        return cleaned_headings, cleaned_features, final_pricing[:15]  # type: ignore

    try:
        from google import genai  # type: ignore
        client = genai.Client(api_key=api_key)
        
        prompt = f"""
        You are an expert data cleaner. I scraped a competitor's website. The extracted text arrays contain boilerplate noise (e.g. 'Shop', 'Tools', 'Contact', short unrelated phrases) and raw unformatted content.
        Filter out the noise and return ONLY the substantive content. For Pricing, include only actual deals, prices, and numbers.
        Return a strictly formatted JSON object with exactly three keys: "headings", "features", and "pricing", each containing an array of strings. Do not include any markdown block formatting in the output, just raw JSON.

        Raw Headings:
        {json.dumps(headings)}
        
        Raw Features:
        {json.dumps(features)}
        
        Raw Pricing:
        {json.dumps(pricing)}
        """
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
        
        return result.get("headings", [])[:15], result.get("features", [])[:20], result.get("pricing", [])[:15]
    except Exception as e:
        print(f"⚠️ Error during Gemini API cleaning: {e}. Falling back to manual cleaning script.")
        from backend.clean_data import clean_text_list  # type: ignore
        cleaned_headings = clean_text_list(headings, min_len=10, max_len=100)[:15]  # type: ignore
        cleaned_features = clean_text_list(features, min_len=15, max_len=120)[:20]  # type: ignore
        cleaned_pricing = clean_text_list(pricing, min_len=5, max_len=150, is_price=True)
        final_pricing = []
        for p in cleaned_pricing:
            if not any((p in fp and p != fp) for fp in cleaned_pricing):
                final_pricing.append(p)
        return cleaned_headings, cleaned_features, final_pricing[:15]  # type: ignore

def extract_data(html, url, is_fallback=False):
    if not html:
        return None
        
    soup = BeautifulSoup(html, 'html.parser')
    
    # Extract Title (brand)
    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    
    # Extract Headings (messaging)
    headings: list[str] = []
    for tag in ['h1', 'h2', 'h3']:
        for h_tag in soup.find_all(tag):
            text = h_tag.get_text(strip=True)
            if text and text not in headings:
                headings.append(text)
                
    # Extract Features (bullet points)
    features: list[str] = []
    for li in soup.find_all('li'):
        text = li.get_text(separator=' ', strip=True)
        # basic filter for substantive list items, avoid very short menu items
        if text and len(text) > 10 and text not in features: 
            features.append(text)
            
    # Extract Pricing (numbers, plans)
    pricing: list[str] = []
    # simple attempt to find pricing related text
    pricing_keywords = ['price', 'pricing', 'plan', '$', '€', '£', 'month', 'year']
    for elem in soup.find_all(['div', 'p', 'span', 'li', 'h2', 'h3', 'h4']):
        text = elem.get_text(separator=' ', strip=True)
        if any(keyword in text.lower() for keyword in pricing_keywords) and len(text) < 150:
             if text not in pricing:
                 pricing.append(text)
                 
    # --- Hybrid Fallback Logic (Method B) ---
    # If we found suspiciously little data, it might be a JS-rendered page (SPA).
    if not is_fallback and (not headings or len(features) < 3):
        print(f"⚠️ Insufficient static data found for {url}. Falling back to Playwright (JS rendering)...")
        try:
            from playwright.sync_api import sync_playwright # type: ignore
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page()
                page.goto(url, wait_until="networkidle", timeout=20000)
                pw_html = page.content()
                browser.close()
            # Recursively call extract_data with the rendered HTML
            return extract_data(pw_html, url, is_fallback=True)
        except ImportError:
            print("⚠️ Playwright not installed. Please run: pip install playwright && playwright install")
        except Exception as e:
            print(f"⚠️ Playwright fallback failed for {url}: {e}")
            
    cleaned_headings, cleaned_features, final_pricing = gemini_clean_data(headings, features, pricing)
             
    return {
        "url": url,
        "title": title,
        "headings": cleaned_headings,
        "features": cleaned_features,
        "pricing": final_pricing    
    }

def save_snapshot(data):
    if not data:
        return
        
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs('backend/data/snapshots', exist_ok=True)
    
    filename = f"backend/data/snapshots/snapshot_{timestamp}.json"
    
    snapshot_data = {
        "timestamp": datetime.now().isoformat(),
        "competitors_data": data
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(snapshot_data, f, indent=2, ensure_ascii=False)
        
    print(f"\n✅ Snapshot saved to {filename}")
    return filename

def main():
    parser = argparse.ArgumentParser(description='Competitor Website Scraper')
    parser.add_argument('urls', metavar='URL', type=str, nargs='*',
                        help='Competitor URLs to scrape')
    
    args = parser.parse_args()
    
    urls = args.urls
    
    if not urls:
        print("Competitor Scraper")
        print("------------------")
        print("Input 2-3 competitor websites manually.")
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
                print(f"✅ Successfully extracted data from {url}")
                
    if all_extracted_data:
        save_snapshot(all_extracted_data)

if __name__ == '__main__':
    main()
