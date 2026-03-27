# 🔭 MarketLens — Competitor Intelligence Engine

> *Transform scattered competitor signals into your team's strategic advantage.*

MarketLens is a full-stack market intelligence platform built to address the challenge of continuously tracking competitors across the web. It automatically discovers competitor websites, crawls and extracts structured signals, detects changes over time, classifies positioning strategies, and surfaces actionable insights — all in a visual dashboard that non-technical teams can immediately use.

---

## 📋 Table of Contents

- [Problem Statement](#-problem-statement)
- [What We Built](#-what-we-built)
- [System Architecture](#-system-architecture)
- [Data Collection Pipeline](#-data-collection-pipeline)
- [Time-Series Tracking & Change Detection](#-time-series-tracking--change-detection)
- [Competitive Comparison & Scoring](#-competitive-comparison--scoring)
- [AI-Powered Insight Engine](#-ai-powered-insight-engine)
- [Trend Analysis Engine](#-trend-analysis-engine)
- [Positioning Matrix](#-positioning-matrix)
- [Ad Library Intelligence](#-ad-library-intelligence)
- [User-Facing Dashboard](#-user-facing-dashboard)
- [API Reference](#-api-reference)
- [Tech Stack](#-tech-stack)
- [Getting Started](#-getting-started)
- [Project Structure](#-project-structure)
- [Evaluation Criteria Coverage](#-evaluation-criteria-coverage)

---

## 🎯 Problem Statement

Companies constantly need to answer questions like:

- What are competitors launching?
- Which messaging angles are they testing?
- How are they positioning for different customer segments?
- What offers, product claims, and CTAs are becoming common?
- What objections are customers raising in reviews and forums?

Today, this intelligence is **scattered across websites, landing pages, ad libraries, review platforms, social media, and internal notes**. Market understanding is slow, manual, and dependent on individual effort.

**MarketLens solves this** by providing an intelligence engine that continuously tracks competitor websites — including pricing changes, ads, reviews, and content changes — to infer actionable strategic insights.

---

## 🚀 What We Built

| Component | Description |
|---|---|
| **Competitor Discovery** | Auto-identifies competitors from a company name using a curated dataset |
| **Multi-Page Crawler** | Two-pass link scoring to crawl the highest-value sub-pages |
| **Signal Scraper** | Extracts pricing, features, CTAs, headings, hero text, and testimonials |
| **Review Scraper** | Pulls G2 and Trustpilot ratings, pros/cons, and review snippets via Playwright |
| **Snapshot System** | Timestamped JSON snapshots that create a time-series history |
| **Seed Engine** | Generates realistic backdated baseline snapshots for demo/testing |
| **Diff Engine** | Detects and surfaces changes between snapshot pairs across 8 signal categories |
| **Scoring Engine** | Prioritizes changes by strategic importance (composite 1–10 score) |
| **Positioning Engine** | Places competitors on 3 strategic axes without any API calls |
| **Trend Engine** | Detects rising/falling signals, volatile fields, and converging themes across all snapshots |
| **Insight Engine** | Uses Google Gemini AI to generate strategic insights with source traceability |
| **Ad Library Scraper** | Scrapes Facebook Ad Library for active ad signals without requiring login |
| **React Dashboard** | Full-featured visual dashboard for non-technical team exploration |
| **Export System** | Download full intelligence reports as JSON or CSV |

---

## 🏗 System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        React Dashboard (Vite)                   │
│  CompetitorCard · DiffPanel · InsightsPanel · PositioningMatrix │
│  TrendsPanel · AdLibraryPanel · WhitespacePanel · ExportButton  │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP (REST)
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Backend (Python)                     │
│                         main.py                                 │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐     │
│  │  competitor_ │  │   crawler    │  │      scraper       │     │
│  │  discovery/  │  │ (2-pass link │  │ (hero, headings,   │     │
│  │ (auto-lookup)│  │   scoring)   │  │  pricing, CTAs,    │     │
│  └──────────────┘  └──────────────┘  │  features, tests)  │     │
│                                      └────────────────────┘     │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐     │
│  │   review_    │  │  diff_engine │  │   scoring_engine   │     │
│  │   scraper    │  │ (8 categories│  │ (signal_weight ×   │     │
│  │ (G2 + TP via │  │   of change) │  │    magnitude)      │     │
│  │  Playwright) │  └──────────────┘  └────────────────────┘     │
│  └──────────────┘                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐     │
│  │  insight_    │  │ positioning_ │  │   trend_engine     │     │
│  │  engine      │  │   engine     │  │  (rising, falling, │     │
│  │ (Gemini AI)  │  │ (3-axis rule │  │  volatile, stable, │     │
│  └──────────────┘  │    -based)   │  │  converging)       │     │
│                    └──────────────┘  └────────────────────┘     │
│  ┌──────────────┐  ┌──────────────┐                             │
│  │  ad_scraper  │  │ seed_engine  │                             │
│  │ (FB Ad Lib   │  │ (backdated   │                             │
│  │  Playwright) │  │   snapshots) │                             │
│  └──────────────┘  └──────────────┘                             │
│                                                                 │
│            ┌─ backend/data/ ─────────────────┐                  │
│            │  snapshots/snapshot_*.json       │                 │
│            │  insights_cache.json             │                 │
│            │  companies.json · industry_map   │                 │
│            └──────────────────────────────────┘                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🕷 Data Collection Pipeline

### 1. Competitor Discovery (`competitor_discovery/`)

Before any scraping begins, MarketLens auto-discovers competitors from the user's company name. The discovery engine:

- Looks up the company in a **curated JSON dataset** (`data/companies.json`) that maps company names to their industry and known competitors
- Falls back to **fuzzy name matching** if an exact match is not found (with suggestions surfaced to the UI)
- Returns competitor names, URLs, and industry classification — no manual URL entry required

**Example:** Set `USER_COMPANY = "Hyundai"` in the frontend and the system automatically identifies Maruti Suzuki, Tata Motors, Mahindra, Toyota, and Kia as competitors and pre-fills their URLs.

### 2. Two-Pass Smart Crawler (`crawler.py`)

For each competitor, MarketLens doesn't just scrape the homepage — it intelligently crawls up to **5 high-value sub-pages** using a two-pass link scoring strategy:

**Pass 1 — Nav Harvest:**
Links from `<nav>` and `<header>` elements get a +2 bonus score because companies surface their most important pages in navigation.

**Pass 2 — URL Path Scoring:**
Every internal link is scored by its URL path keywords:
```
/pricing → 10    /features → 9    /products → 9
/solutions → 8   /compare → 8     /about → 7
/customers → 7   /enterprise → 6  ...
```
Transactional and noisy paths (careers, blog, sitemap, login, legal) are excluded automatically.

The top-scoring URLs are scraped, and all extracted data is **merged into a single unified competitor profile**.

### 3. Structured Signal Extraction (`scraper.py`)

Each page is processed through a multi-stage extraction pipeline:

| Signal | Extraction Method |
|---|---|
| **Title** | `<title>` tag |
| **Meta Description** | `<meta name="description">`, og:description, twitter:description |
| **Hero Text** | CSS class pattern matching for hero/banner/jumbotron sections, fallback to first `<h1>` |
| **Headings** | All `<h1>`, `<h2>`, `<h3>` tags after chrome removal |
| **CTAs** | `<button>` and button-styled `<a>` tags, max 6 words, filtered by CTA keyword list |
| **Features** | `<li>` items from content areas (nav/header/footer stripped first) |
| **Pricing** | Currency-aware regex matching (`$`, `₹`, `/mo`, `lakh`, `rs.`) from price-containing elements |
| **Testimonials** | `<blockquote>`, `<q>`, and container divs with testimonial/quote/review class patterns |

**Playwright Fallback:** If insufficient data is extracted from static HTML (headings missing or fewer than 3 features), the scraper automatically retries using a headless Chromium browser to handle JS-rendered SPAs.

**Clean Data Pipeline (`clean_data.py`):** Raw extracted text is cleaned deterministically — removing duplicates, stripping noise, filtering by character length bounds, and applying substring deduplication to pricing entries.

### 4. Review Scraping (`review_scraper.py`)

Using **Playwright** (headless Chromium), MarketLens scrapes two major review platforms:

**G2:**
- Auto-derives product slug from company URL (e.g., `notion.so` → `g2.com/products/notion/reviews`)
- Extracts: overall rating, review count, pros (from "What do you like best?"), cons (from "What do you dislike?"), and recent review snippets

**Trustpilot:**
- Auto-derives review URL from company domain (e.g., `trustpilot.com/review/notion.so`)
- Extracts: TrustScore, rating label (Excellent/Great/Good/etc.), review count, and recent snippets

Reviews are **optional per scrape run** (toggled via checkbox in the UI) to allow faster runs when review data isn't needed.

### 5. Snapshot Persistence (`scraper.py → save_snapshot`)

Every scrape run saves a timestamped JSON snapshot to `backend/data/snapshots/`:
```json
{
  "timestamp": "2026-03-26T04:30:00",
  "competitors_data": [
    {
      "url": "https://maruti.com",
      "title": "Maruti Suzuki India",
      "meta_description": "...",
      "hero_text": ["Drive Your Dreams"],
      "headings": ["..."],
      "ctas": ["Book a Test Drive", "Explore Models"],
      "features": ["..."],
      "pricing": ["Starting at ₹4.99 Lakh"],
      "testimonials": ["..."],
      "reviews": { "g2": null, "trustpilot": { ... } },
      "pages_crawled": ["https://maruti.com", "https://maruti.com/cars"]
    }
  ]
}
```

### 6. Seed Engine (`seed_engine.py`)

For demonstration and testing purposes, the seed engine creates a **realistic backdated baseline snapshot** by:
1. Scraping the current competitor pages
2. Applying deterministic mutations (removing CTAs, slightly altering pricing, removing some features)
3. Saving the mutated snapshot with a timestamp from N days ago (default: 7 days)

This allows the diff engine to show realistic, meaningful changes without requiring weeks of actual data accumulation.

---

## ⏱ Time-Series Tracking & Change Detection

### Diff Engine (`diff_engine.py`)

The diff engine compares the **two most recent snapshots** and surfaces changes across 8 signal categories:

| Category | What Changed |
|---|---|
| **Positioning** | Meta description / brand positioning statement |
| **Hero Content** | Above-the-fold headlines and copy |
| **Messaging** | H1/H2/H3 headings across the site |
| **CTAs** | Call-to-action buttons and links |
| **Pricing** | Any pricing-related text |
| **Features** | Feature/benefit list items |
| **Social Proof** | Customer testimonials |
| **G2 Rating** | G2 star rating change (threshold: ±0.1) |
| **Trustpilot Score** | Trustpilot score change (threshold: ±0.1) |

Each change entry contains:
- `brand` — competitor name
- `category` — type of change
- `description` — human-readable summary
- `added` — list of new items
- `removed` — list of removed items

All set operations use **normalized comparison** (lowercase + trimmed) to avoid false positives from minor formatting differences.

---

## 🏆 Competitive Comparison & Scoring

### Scoring Engine (`scoring_engine.py`)

Every detected change is automatically scored on three dimensions, generating a **composite priority score (1–10)**:

**Signal Weight** — How strategically important is this type of change?
```
Pricing: 10    Positioning: 9    G2/Trustpilot Rating: 8
Features: 7    Hero Content: 7   Messaging: 6
CTAs: 6        Social Proof: 5   New Competitor: 9
```

**Magnitude** — How much changed?
```
1 item changed → 0.3    3 items → 0.6    5+ items → 1.0
```

**Composite Score:**
```
composite = (signal_weight × 0.6) + (magnitude × 10 × 0.4)
```

**Priority Buckets:**
| Score | Priority |
|---|---|
| 8.5 – 10 | 🔴 Critical |
| 6.5 – 8.4 | 🟠 High |
| 4.5 – 6.4 | 🟡 Medium |
| < 4.5 | 🟢 Low |

Changes are sorted by composite score descending so the highest-impact signals appear first. The dashboard shows a **scoring summary bar** (how many critical/high/medium/low changes exist) giving teams an at-a-glance priority view.

---

## 🤖 AI-Powered Insight Engine

### Gemini Integration (`insight_engine.py`)

MarketLens uses **Google Gemini 2.5 Flash** to generate two types of AI-powered intelligence:

#### Strategic Insights
Fed the structured diff data (competitor changes), Gemini acts as a **senior strategy consultant** and generates 3–5 high-impact insights. Each insight includes:

- **Title** — concise signal name (max 8 words)
- **Description** — 2–3 sentence explanation of the strategic signal and why it matters
- **Action** — one specific, concrete recommended action for the team
- **Scores:**
  - `novelty` (1–10): How new/surprising vs. known market trends?
  - `frequency` (1–10): How often is this pattern appearing across competitors?
  - `relevance` (1–10): How directly does this affect our strategy or revenue?
  - `composite` (1–10): Clean average of the three dimensions
- **Source Traces** — exact `url + field + snippet` citations from the raw diff data, ensuring every insight is **traceable back to its source**

#### Whitespace Detection
Fed the latest snapshot data, Gemini identifies **3–5 whitespace opportunities** — gaps that no competitor is addressing. Each opportunity includes:
- A clear description of the unserved niche
- An `opportunity_score` (1–10)
- A concrete suggested action
- Supporting evidence (what is absent in the competitive data)

#### Caching Architecture
Insights are **cached to disk** (`backend/data/insights_cache.json`, auto-generated at runtime and listed in `.gitignore` so it is never committed) keyed by snapshot timestamp. `GET /api/insights` returns the cache instantly (no Gemini call). `POST /api/insights/generate` triggers a fresh generation explicitly. This prevents quota exhaustion from multiple page loads and gives teams control over API usage.

---

## 📈 Trend Analysis Engine

### Multi-Snapshot Trend Detection (`trend_engine.py`)

Unlike the diff engine which compares just the last two snapshots, the trend engine analyses **all snapshots in history** to surface longitudinal patterns. It builds per-URL timelines (so URLs that don't appear together in the same snapshot file are still compared correctly):

| Trend Type | Description |
|---|---|
| **rising_signal** | A field consistently gaining new items across multiple tracked intervals (0 removals) |
| **falling_signal** | A field consistently losing items (0 additions) |
| **volatile** | A competitor changing a specific field in ≥60% of their tracked appearances — actively testing |
| **converging_theme** | A keyword/phrase appearing in the same field across multiple competitors — may be becoming table stakes |
| **stable** | A field completely unchanged across 3+ snapshot appearances — signal of deliberate locked-in strategy |

All trends are scored by **significance** (1–10) and sorted for prioritization. Converging themes surface up to 8 of the most widespread keywords across competitors and their source companies.

---

## 🗺 Positioning Matrix

### Rule-Based Competitive Classification (`positioning_engine.py`)

Without any API calls, MarketLens classifies every competitor on **three strategic axes** using keyword-heuristic matching:

**Axis 1 — Price Positioning (0=Cost-Leader → 10=Premium)**
- Scores free tier signals, cheap/affordable signals, and premium signals
- Formula: `5.0 + (premium_hits × 1.5) − (free_hits × 2.0) − (cheap_hits × 0.8)`

**Axis 2 — Value Framing (0=Feature-Rich → 10=Outcome-Driven)**
- Scores feature/integration/API signals vs. outcome/ROI/results signals
- Formula: `5.0 + (outcome_hits × 0.8) − (feature_hits × 0.6)`

**Axis 3 — Go-To-Market Motion (0=Self-Serve → 10=Sales-Led)**
- Scores self-serve CTAs ("Start Free", "Sign Up") vs. sales CTAs ("Book a Demo", "Contact Sales")
- Formula: `5.0 + (sales_led_hits × 2.0) − (self_serve_hits × 2.0)`

**Labels:** Premium / Mid-Market / Cost-Leader | Outcome-Driven / Balanced / Feature-Rich | Sales-Led / Hybrid / Self-Serve

**Axis Leaders:** The system identifies which competitor leads or trails on each axis (most premium, most cost-leader, most sales-led, etc.)

**Overused Angle Detection:**
Eight positioning angles are monitored for market saturation:
- Outcome-Driven Messaging, Enterprise Focus, Simplicity/Ease of Use, AI-Powered, Free/Low Cost Entry, Speed/Performance, Trusted/Social Proof, Integration Ecosystem

If ≥50% of competitors use an angle, it is flagged as **overused** with a saturation percentage, list of using competitors, strategic implication, and a **whitespace hint** — the counter-positioning angle that's currently unexplored.

---

## 📢 Ad Library Intelligence

### Facebook Ad Library Scraper (`ad_scraper.py`)

MarketLens scrapes the publicly accessible **Facebook Ad Library** (no login required) using Playwright. For any search keyword, it extracts per-ad signals:

- `page_name` — advertiser
- `ad_text` — main body copy (top 3 lines)
- `started_date` — when the ad began running
- `platforms` — Facebook, Instagram, Messenger, WhatsApp distribution
- `cta_type` — button label (Learn More, Shop Now, Sign Up, etc.)
- `media_type` — image / video / carousel

These are aggregated into **market-level signals**:
- Top advertisers by active ad volume
- Most common CTAs in the market
- Platform spread (which channels competitors favor)
- Media mix (image vs. video vs. carousel ratio)
- Top copy themes (most frequent keywords in ad copy)

Results are **cached for 6 hours** per keyword to avoid repeat scraping.

---

## 🖥 User-Facing Dashboard

### React Frontend (`frontend/src/`)

The dashboard is built with **React + Vite + TailwindCSS** and consists of 7 purpose-built components:

| Component | What It Shows |
|---|---|
| **CompetitorCard** | Per-competitor deep-dive: pricing, features, CTAs, headings, G2 & Trustpilot ratings, hero text, pages crawled |
| **DiffPanel** | Priority-sorted change feed with scoring summary (Critical/High/Medium/Low counts), expandable change details with added/removed items highlighted |
| **InsightsPanel** | AI-generated strategic insights with novelty/frequency/relevance scores, recommended actions, and clickable source traces |
| **WhitespacePanel** | Market gaps with opportunity scores and suggested actions |
| **PositioningMatrix** | 2D scatter plot (Price vs. GTM axes), competitor labels, axis leaders, and overused angle cards |
| **TrendsPanel** | Trend feed by type (rising/falling/volatile/converging/stable) with significance scores and competitor attribution |
| **AdLibraryPanel** | Facebook ad intelligence: top advertisers, CTAs, platform spread, media mix, copy themes |

**Dashboard Actions:**
1. **Seed Demo** (amber button) — Creates a backdated baseline snapshot for the discovered competitors
2. **Fetch Competitor Pages** (blue button) — Scrapes live competitor pages and refreshes all panels
3. **Generate Insights** (violet button) — Explicitly calls Gemini AI to generate fresh strategic insights
4. **Export** — Downloads a full intelligence report as JSON or CSV
5. **Include G2 & Trustpilot Reviews** toggle — Opt into slower-but-richer scraping with review platform data

---

## 📡 API Reference

All endpoints served from `http://localhost:8000`:

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Health check |
| `GET` | `/get-competitors?company=Hyundai` | Auto-discover competitors for a company |
| `POST` | `/api/fetch` | Scrape competitor URLs and save snapshot |
| `GET` | `/api/snapshots` | List all saved snapshots (newest first) |
| `POST` | `/api/seed` | Create backdated demo baseline snapshot |
| `GET` | `/api/seed/urls` | Get URLs tracked in latest snapshot |
| `GET` | `/api/diff` | Compare latest two snapshots, return scored changes |
| `GET` | `/api/insights` | Return cached Gemini insights + whitespace |
| `POST` | `/api/insights/generate` | Trigger fresh Gemini insight generation |
| `GET` | `/api/positioning` | Return competitive positioning map |
| `GET` | `/api/trends` | Return multi-snapshot trend analysis |
| `POST` | `/api/ads` | Scrape Facebook Ad Library for a keyword |
| `GET` | `/api/export?format=json` | Download full intelligence report as JSON |
| `GET` | `/api/export?format=csv` | Download full intelligence report as CSV |

---

## 🛠 Tech Stack

### Backend
| Technology | Purpose |
|---|---|
| **Python 3.11+** | Core language |
| **FastAPI** | REST API framework |
| **Uvicorn** | ASGI server |
| **BeautifulSoup4** | HTML parsing and signal extraction |
| **Requests** | HTTP scraping with encoding correction |
| **Playwright** | Headless Chromium for JS-rendered pages, G2, Trustpilot, and Facebook Ad Library |
| **Google Gemini 2.5 Flash** | AI-powered strategic insight and whitespace generation |
| **python-dotenv** | Environment variable management |
| **Pydantic** | Request/response validation |

### Frontend
| Technology | Purpose |
|---|---|
| **React 19** | UI framework |
| **Vite** | Build tool and dev server |
| **TailwindCSS** | Utility-first styling |
| **Axios** | API client |
| **Lucide React** | Icon system |

---

## 🚦 Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+
- A Google Gemini API key (get one free at [aistudio.google.com](https://aistudio.google.com))

### 1. Clone and Set Up Backend

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browsers (for review scraping and ad library)
python -m playwright install chromium
```

### 2. Configure Environment

Create a `.env` file in the project root:
```env
GEMINI_API_KEY=your_gemini_api_key_here
# Optional: override model
# GEMINI_MODEL=gemini-2.5-flash
```

### 3. Install Frontend Dependencies

```bash
cd frontend
npm install
```

### 4. Start Both Servers

**Linux/Mac:**
```bash
chmod +x start.sh && ./start.sh
```

**Windows (two terminals):**
```bash
# Terminal 1 — Backend
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 — Frontend
cd frontend && npm run dev
```

### 5. Use the Dashboard

Open **http://localhost:5173** in your browser.

**Recommended first-time flow:**
1. The dashboard auto-loads competitors for `Hyundai` (configurable in `App.jsx` → `USER_COMPANY`)
2. Click **Seed Demo** to create a realistic 7-day-old baseline snapshot
3. Click **Fetch Competitor Pages** to scrape the current state of competitor sites
4. The diff panel will now show meaningful changes between the baseline and live data
5. Click **Generate Insights** to run Gemini AI analysis on the detected changes
6. Explore the Positioning Matrix, Trends, and Ad Library panels

---

## 📁 Project Structure

```
marketlens/
├── .env                          # GEMINI_API_KEY
├── requirements.txt              # Python dependencies
├── start.sh                      # One-command startup script
│
├── backend/
│   ├── main.py                   # FastAPI app + all route definitions
│   ├── crawler.py                # Two-pass smart link scoring + multi-page crawl
│   ├── scraper.py                # HTML signal extraction + snapshot persistence
│   ├── clean_data.py             # Deterministic text cleaning pipeline
│   ├── review_scraper.py         # G2 + Trustpilot Playwright scraper
│   ├── ad_scraper.py             # Facebook Ad Library Playwright scraper
│   ├── diff_engine.py            # Change detection across 8 signal categories
│   ├── scoring_engine.py         # Signal weight × magnitude composite scoring
│   ├── insight_engine.py         # Gemini AI insights + whitespace + disk cache
│   ├── positioning_engine.py     # 3-axis rule-based positioning classifier
│   ├── trend_engine.py           # Multi-snapshot trend analysis (5 trend types)
│   ├── seed_engine.py            # Demo baseline snapshot generator
│   ├── competitor_discovery/
│   │   ├── competitor_engine.py  # Company lookup + fuzzy match + error types
│   │   ├── url_resolver.py       # URL validation and resolution
│   │   └── data_loader.py        # companies.json + industry_map.json loader
│   └── data/
│       ├── companies.json        # Curated competitor dataset
│       ├── industry_map.json     # Industry → competitors mapping
│       ├── insights_cache.json   # Gemini insight cache (auto-generated)
│       └── snapshots/            # Timestamped snapshot JSON files
│
└── frontend/
    ├── src/
    │   ├── App.jsx               # Root component + all dashboard orchestration
    │   ├── components/
    │   │   ├── CompetitorCard.jsx    # Per-competitor signal deep-dive card
    │   │   ├── DiffPanel.jsx         # Change feed with priority scoring
    │   │   ├── InsightsPanel.jsx     # AI insights + whitespace opportunities
    │   │   ├── PositioningMatrix.jsx # 2D scatter plot + overused angles
    │   │   ├── TrendsPanel.jsx       # Multi-snapshot trend visualization
    │   │   ├── AdLibraryPanel.jsx    # Facebook Ad Library intelligence
    │   │   └── ExportButton.jsx      # JSON/CSV report download
    │   └── main.jsx
    ├── package.json
    └── vite.config.js
```

---

## ✅ Evaluation Criteria Coverage

| Criterion | How We Address It |
|---|---|
| **Data Completeness** | Multi-page crawler covers pricing, features, CTAs, headings, hero text, testimonials, and G2/Trustpilot reviews across up to 6 pages per competitor. Facebook Ad Library adds active ad intelligence. |
| **Change Data Quality** | Diff engine uses normalized set comparison across 8 categories with millisecond-precision timestamped snapshots. G2/Trustpilot score deltas tracked with 0.1 threshold. |
| **Insight Accuracy** | Every Gemini insight includes `source_traces` with exact `url + field + snippet` citations. Positioning scores link to specific pricing/CTA/testimonial evidence. |
| **Actionability** | Every insight includes a specific `action` field. Whitespace entries have `suggested_action`. Overused angles include `whitespace_hint` with counter-positioning strategy. |
| **Usability** | Non-technical teams can click **Seed Demo → Fetch → Generate Insights** in minutes. Priority-sorted diff feed, visual positioning matrix, and plain-language trend descriptions require no data expertise. |

---

## 🔒 Constraints & Design Decisions

- **Source Traceability:** Every insight returned by Gemini includes `source_traces` (URL, field, and snippet) so teams can verify claims against raw data.
- **No Hallucination Guardrails:** The Gemini prompt explicitly instructs: *"Only cite what appears in the COMPETITOR CHANGES above"* — limiting the model to grounded citations from the actual scraped data.
- **API Quota Protection:** Gemini calls are triggered manually (`POST /api/insights/generate`), not on every page load. Results are disk-cached by snapshot timestamp.
- **Playwright on Windows:** The review and ad scraper run Playwright in dedicated threads with explicit `SelectorEventLoop` initialization to avoid Windows ProactorEventLoop conflicts with uvicorn.
- **Encoding Robustness:** HTTP responses are decoded using `apparent_encoding` with a UTF-8 fallback to correctly handle currencies like `₹` that are misread as ISO-8859-1.

---

*MarketLens — built to transform scattered competitor signals into your team's strategic advantage.*
