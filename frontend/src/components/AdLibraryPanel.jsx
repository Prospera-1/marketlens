/**
 * AdLibraryPanel.jsx — Facebook Ad Library signal explorer.
 *
 * Lets users search the public Facebook Ad Library by keyword.
 * Results are cached for 6 hours in the backend.
 *
 * Surfaces:
 *   - Top advertisers running active ads
 *   - Most common CTA labels in ads
 *   - Platform distribution (Facebook, Instagram, etc.)
 *   - Media mix (image / video / carousel)
 *   - Top copy themes extracted from ad text
 *   - Individual ad previews (page name + ad copy)
 */

import { useState } from 'react';
import axios from 'axios';
import { Megaphone, Search, RefreshCw, ChevronDown, ChevronUp, ExternalLink } from 'lucide-react';

const API_BASE = "http://localhost:8000/api";

// ── Small stat badge ──────────────────────────────────────────────────────────
function StatPill({ label, value, color = 'bg-slate-100 text-slate-700' }) {
  return (
    <div className={`rounded-lg px-3 py-2 flex flex-col items-center ${color}`}>
      <span className="text-lg font-bold">{value}</span>
      <span className="text-[10px] text-current opacity-70">{label}</span>
    </div>
  );
}

// ── Signals summary row ───────────────────────────────────────────────────────
function SignalsSummary({ signals }) {
  if (!signals || !signals.total_ads_found) return null;

  return (
    <div className="space-y-3">
      {/* Stat pills */}
      <div className="flex flex-wrap gap-2">
        <StatPill label="Ads found" value={signals.total_ads_found} color="bg-blue-50 text-blue-700" />
        {signals.media_mix && Object.entries(signals.media_mix).map(([type, count]) => (
          <StatPill key={type} label={type} value={count} color="bg-violet-50 text-violet-700" />
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Top advertisers */}
        {signals.top_advertisers?.length > 0 && (
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Top advertisers</p>
            <div className="space-y-1">
              {signals.top_advertisers.map(([name, count]) => (
                <div key={name} className="flex justify-between text-xs py-1 border-b border-slate-100">
                  <span className="text-slate-700 truncate max-w-[75%]">{name}</span>
                  <span className="text-slate-400 font-medium">{count} ads</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Common CTAs */}
        {signals.common_ctas?.length > 0 && (
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Common CTAs</p>
            <div className="flex flex-wrap gap-1.5">
              {signals.common_ctas.map(([cta, count]) => (
                <span key={cta} className="bg-emerald-50 text-emerald-700 text-xs px-2.5 py-1 rounded-full border border-emerald-200">
                  {cta} <span className="text-emerald-400">×{count}</span>
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Platforms */}
        {signals.platform_spread && Object.keys(signals.platform_spread).length > 0 && (
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Platforms</p>
            <div className="flex flex-wrap gap-1.5">
              {Object.entries(signals.platform_spread).map(([platform, count]) => (
                <span key={platform} className="bg-blue-50 text-blue-700 text-xs px-2.5 py-1 rounded-full border border-blue-200">
                  {platform} <span className="text-blue-400">×{count}</span>
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Top copy themes */}
        {signals.top_copy_themes?.length > 0 && (
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Copy themes</p>
            <div className="flex flex-wrap gap-1.5">
              {signals.top_copy_themes.map(theme => (
                <span key={theme} className="bg-amber-50 text-amber-700 text-xs px-2.5 py-1 rounded-full border border-amber-200">
                  {theme}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Individual ad card ────────────────────────────────────────────────────────
function AdCard({ ad }) {
  return (
    <div className="border border-slate-200 rounded-lg p-3 space-y-1.5 bg-slate-50 hover:bg-white transition">
      <div className="flex items-start justify-between gap-2">
        <p className="text-xs font-bold text-slate-800 truncate">{ad.page_name || 'Unknown advertiser'}</p>
        <div className="flex gap-1 shrink-0">
          {ad.media_type && ad.media_type !== 'image' && (
            <span className="text-[9px] bg-violet-100 text-violet-600 px-1.5 py-0.5 rounded">
              {ad.media_type}
            </span>
          )}
          {ad.cta_type && (
            <span className="text-[9px] bg-emerald-100 text-emerald-600 px-1.5 py-0.5 rounded">
              {ad.cta_type}
            </span>
          )}
        </div>
      </div>
      {ad.ad_text && (
        <p className="text-xs text-slate-600 line-clamp-3">{ad.ad_text}</p>
      )}
      <div className="flex items-center justify-between text-[10px] text-slate-400">
        {ad.started_date && <span>Started {ad.started_date}</span>}
        {ad.platforms?.length > 0 && (
          <span>{ad.platforms.join(' · ')}</span>
        )}
      </div>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────
export default function AdLibraryPanel() {
  const [keyword, setKeyword]     = useState('');
  const [loading, setLoading]     = useState(false);
  const [result, setResult]       = useState(null);
  const [error, setError]         = useState('');
  const [showAds, setShowAds]     = useState(false);

  const search = async (forceRefresh = false) => {
    const kw = keyword.trim();
    if (!kw) return;
    setLoading(true);
    setError('');
    setResult(null);
    setShowAds(false);
    try {
      const res = await axios.post(`${API_BASE}/ads`, { keyword: kw, force_refresh: forceRefresh });
      setResult(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-5">
      <div className="flex items-center gap-2">
        <Megaphone className="w-5 h-5 text-blue-500" />
        <h2 className="text-xl font-bold">Ad Library Signals</h2>
        <span className="text-xs text-slate-400">Facebook · public · no login required</span>
      </div>

      {/* Search bar */}
      <div className="flex gap-2">
        <input
          type="text"
          value={keyword}
          onChange={e => setKeyword(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && search()}
          placeholder="e.g. Tata Motors, Hyundai India, SUV offers…"
          className="flex-1 px-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none"
        />
        <button
          onClick={() => search(false)}
          disabled={loading || !keyword.trim()}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg flex items-center gap-2 transition disabled:opacity-60"
        >
          {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
          Search
        </button>
        {result && (
          <button
            onClick={() => search(true)}
            disabled={loading}
            title="Force re-scrape (bypasses 6-hour cache)"
            className="px-3 py-2 border border-slate-200 rounded-lg text-slate-500 hover:bg-slate-50 transition disabled:opacity-60 text-xs"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        )}
      </div>

      {error && (
        <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{error}</p>
      )}

      {loading && (
        <div className="text-sm text-slate-500 flex items-center gap-2 py-4 justify-center">
          <RefreshCw className="w-4 h-4 animate-spin" />
          Scraping Facebook Ad Library… this may take 30–60 seconds.
        </div>
      )}

      {result && !loading && (
        <div className="space-y-4">
          {/* Cache notice */}
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>
              {result.from_cache ? 'Cached result · ' : 'Fresh scrape · '}
              {result.fetched_at?.slice(0, 16).replace('T', ' ')} UTC
            </span>
            <a
              href={`https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=IN&q=${encodeURIComponent(result.keyword)}&search_type=keyword_unordered`}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-1 text-blue-500 hover:underline"
            >
              Open in Ad Library <ExternalLink className="w-3 h-3" />
            </a>
          </div>

          {result.signals?.total_ads_found === 0 && (
            <p className="text-sm text-slate-500 bg-slate-50 rounded-lg p-4 border border-dashed border-slate-200 text-center">
              No ads found for "{result.keyword}". The Ad Library may have been blocked or no active ads match this keyword.
            </p>
          )}

          <SignalsSummary signals={result.signals} />

          {/* Individual ads toggle */}
          {result.ads?.length > 0 && (
            <div>
              <button
                onClick={() => setShowAds(v => !v)}
                className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-700 transition font-medium"
              >
                {showAds ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                {showAds ? 'Hide' : 'Show'} {result.ads.length} individual ad{result.ads.length !== 1 ? 's' : ''}
              </button>

              {showAds && (
                <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-2">
                  {result.ads.map((ad, i) => <AdCard key={i} ad={ad} />)}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Empty state */}
      {!result && !loading && !error && (
        <p className="text-xs text-slate-400 text-center py-4">
          Search for a brand or category to surface active ad signals from Facebook Ad Library.
        </p>
      )}
    </section>
  );
}
