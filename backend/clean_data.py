import json
import os
import glob

def get_latest_snapshot():
    files = glob.glob('snapshots/*.json')
    if not files:
        return None
    return max(files, key=os.path.getctime)

def clean_text_list(texts, min_len=5, max_len=150, is_price=False):
    cleaned = []
    seen = set()
    for text in texts:
        text = text.strip()
        
        # 1. Filter out extremely short or very long generic strings
        if len(text) < min_len or len(text) > max_len:
            continue
            
        # 2. Filter out obvious UI navigation terms and boilerplate
        nav_terms = {
            'shop', 'finance', 'support', 'resources', 'tools', 'sell', 'buy',
            'home', 'about', 'contact', 'menu', 'sign in', 'log in', 'search',
            'find a dealer', 'inventory', 'build & price', 'explore', 'compare',
            'popular categories', 'buyer resources', 'selling resources',
            'research & news', 'tools & services', 'our company',
            'login / register', 'login/register', 'register', 'login',
            'explore new cars', 'new cars', 'used cars', 'news & reviews',
            'download app', 'view all', 'read more', 'view details',
            'call dealer', 'contact dealer', 'write a review', 'view march offers',
            'download brochure', 'emi calculator', 'view all answers',
        }
        if text.lower() in nav_terms:
            continue

        # 2b. Prefix-based nav link patterns (e.g. "View All Wagon R Reviews", "Start a new Comparison")
        nav_prefixes = ('view all', 'see all', 'show all', 'load more', 'start a new',
                        'read all', 'show more', 'latest questions', 'popular mentions')
        if text.lower().startswith(nav_prefixes):
            continue

        # 3. For features (not pricing), exclude items that look like non-content cards.
        #    Pricing cards: contain currency/vehicle signals → belong in pricing field.
        #    Dealer cards: contain dealer/branch signals.
        #    Video/media metadata: contain view counts or timestamps.
        listing_signals = {
            'lakh', '\u20b9', 'rs.', ' rs ', 'petrol', 'cng', 'diesel',   # vehicle/price
            'preferred dealer', 'call dealer', 'contact dealer',           # dealer cards
            'k views', 'views by', 'years ago', 'months ago',             # video metadata
        }
        if not is_price and any(sig in text.lower() for sig in listing_signals):
            continue

        # 4. Specific price/number parsing logic if looking for deals
        if is_price:
            # Must contain a number to be considered price/deal info
            if not any(char.isdigit() for char in text):
                continue
            # Exclude rating widgets that happen to contain a currency symbol
            # e.g. "4.7 102 Reviews Rate & Win ₹1000"
            review_rating_signals = {'reviews rate', 'rate & win', 'win \u20b9', 'win $', 'rate and win'}
            if any(sig in text.lower() for sig in review_rating_signals):
                continue
                
        # 4. Remove exact duplicates (case-insensitive)
        normalized = text.lower()
        if normalized not in seen:
            seen.add(normalized)
            # Remove any excessive internal whitespace
            clean_str = " ".join(text.split())
            cleaned.append(clean_str)
            
    return cleaned

def display_data(data):
    print("="*70)
    print(f"COMPETITOR: {data.get('title', 'N/A')}")
    print(f"URL:        {data.get('url', 'N/A')}")
    print("="*70)
    
    print("\nKEY MESSAGING & HEADINGS:")
    cleaned_headings = clean_text_list(data.get('headings', []), min_len=10, max_len=100)
    for i, item in enumerate(cleaned_headings[:8], 1): # type: ignore
        print(f"  {i}. {item}")
    if not cleaned_headings:
        print("  (No relevant headings found)")
        
    print("\nNOTABLE FEATURES & SERVICES:")
    cleaned_features = clean_text_list(data.get('features', []), min_len=15, max_len=120)
    for i, item in enumerate(cleaned_features[:10], 1): # type: ignore
        print(f"  {i}. {item}")
    if not cleaned_features:
        print("  (No relevant features found)")
        
    print("\nPRICING, DEALS & INVENTORY:")
    cleaned_pricing = clean_text_list(data.get('pricing', []), min_len=5, max_len=150, is_price=True)
    # Filter out duplicate substrings to make it even cleaner
    final_pricing = []
    for p in cleaned_pricing:
        if not any((p in fp and p != fp) for fp in cleaned_pricing):
            final_pricing.append(p)
            
    for i, item in enumerate(final_pricing[:10], 1): # type: ignore
        print(f"  {i}. {item}")
    if not final_pricing:
        print("  (No specific pricing info found)")
    print("\n")

def main():
    latest = get_latest_snapshot()
    if not latest:
        print("ERROR: No snapshots found in the 'snapshots' directory!")
        return
        
    print(f"\nDATA REPORT (Source: {latest})\n")
    with open(latest, 'r', encoding='utf-8') as f:
        try:
            snapshot = json.load(f)
        except json.JSONDecodeError:
            print(f"ERROR: {latest} is not a valid JSON file.")
            return
        
    competitors = snapshot.get('competitors_data', [])
    if not competitors:
        print("No competitor data found in this snapshot.")
        return
        
    for comp in competitors:
        display_data(comp)
        
    print(f"Displayed {len(competitors)} competitor profile(s).")

if __name__ == '__main__':
    main()
