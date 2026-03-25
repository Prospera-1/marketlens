import { useState, useEffect } from 'react';
import axios from 'axios';
import { RefreshCw, Play, AlertCircle, Search, FlaskConical, Sparkles } from 'lucide-react';
import CompetitorCard from './components/CompetitorCard';
import DiffPanel from './components/DiffPanel';
import { InsightsPanel, WhitespacePanel } from './components/InsightsPanel';
import PositioningMatrix from './components/PositioningMatrix';
import TrendsPanel from './components/TrendsPanel';
import ExportButton from './components/ExportButton';
import AdLibraryPanel from './components/AdLibraryPanel';

const API_BASE = "http://localhost:8000/api";
const COMPETITOR_DISCOVERY_BASE = "http://localhost:8000";
const USER_COMPANY = "Hyundai";

export default function App() {
  const [includeReviews, setIncludeReviews] = useState(true);
  const [loading, setLoading] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const [generatingInsights, setGeneratingInsights] = useState(false);
  const [seedSuccess, setSeedSuccess] = useState(false);
  const [error, setError] = useState("");
  const [data, setData] = useState(null);
  const [positioning, setPositioning] = useState(null);
  const [trends, setTrends] = useState(null);
  const [competitorDiscovery, setCompetitorDiscovery] = useState(null);
  const [competitorDiscoveryLoading, setCompetitorDiscoveryLoading] = useState(true);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      setError("");

      const [snapshotsRes, diffRes, insightsRes, positioningRes, trendsRes] = await Promise.all([
        axios.get(`${API_BASE}/snapshots`),
        axios.get(`${API_BASE}/diff`),
        axios.get(`${API_BASE}/insights`),
        axios.get(`${API_BASE}/positioning`),
        axios.get(`${API_BASE}/trends`),
      ]);

      const snapshots = snapshotsRes.data.snapshots || [];
      const diff = diffRes.data;
      const insightsData = insightsRes.data;

      setPositioning(positioningRes.data);
      setTrends(trendsRes.data);
      setData({
        latestSnapshot: snapshots.length > 0 ? snapshots[0] : null,
        diff: diff.changes || [],
        scoringSummary: diff.scoring_summary || null,
        insights: insightsData.insights || [],
        whitespace: insightsData.whitespace || [],
        insightsGeneratedAt: insightsData.generated_at || null,
      });
    } catch (err) {
      setError("Failed to fetch dashboard data. Ensure backend is running. " + err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchDashboardData(); }, []);

  const loadCompetitorDiscovery = async () => {
    setCompetitorDiscoveryLoading(true);
    setError("");
    try {
      const res = await axios.get(
        `${COMPETITOR_DISCOVERY_BASE}/get-competitors?company=${encodeURIComponent(USER_COMPANY)}`
      );
      setCompetitorDiscovery(res.data);
    } catch (err) {
      const detail = err.response?.data?.detail;
      const msg =
        typeof detail === "object" && detail?.error
          ? detail.error
          : typeof detail === "string"
            ? detail
            : err.message;
      setError("Competitor discovery failed. " + msg);
    } finally {
      setCompetitorDiscoveryLoading(false);
    }
  };

  useEffect(() => {
    loadCompetitorDiscovery();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const competitorUrls = competitorDiscovery?.competitors?.map((c) => c.url).filter(Boolean) || [];

  const handleScrape = async () => {
    if (competitorUrls.length === 0) return;

    setLoading(true);
    setError("");
    setSeedSuccess(false);
    try {
      await axios.post(`${API_BASE}/fetch`, { urls: competitorUrls, include_reviews: includeReviews });
      await fetchDashboardData();
    } catch (err) {
      setError("Failed to scrape competitor pages. " + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const handleSeed = async () => {
    if (competitorUrls.length === 0) return;

    setSeeding(true);
    setError("");
    setSeedSuccess(false);
    try {
      const res = await axios.post(`${API_BASE}/seed`, { urls: competitorUrls, days_ago: 7 });
      setSeedSuccess(res.data.urls_seeded);
    } catch (err) {
      setError("Seed failed. " + (err.response?.data?.detail || err.message));
    } finally {
      setSeeding(false);
    }
  };

  const handleGenerateInsights = async () => {
    setGeneratingInsights(true);
    setError("");
    try {
      const res = await axios.post(`${API_BASE}/insights/generate`);
      setData((prev) =>
        prev
          ? {
              ...prev,
              insights: res.data.insights || [],
              whitespace: res.data.whitespace || [],
            }
          : prev
      );
    } catch (err) {
      const detail = err.response?.data?.detail || err.message;
      const is429 =
        detail?.includes("429") || detail?.includes("RESOURCE_EXHAUSTED") || detail?.includes("quota");
      setError(
        is429
          ? "Gemini API quota reached. Wait a minute and try again, or check your plan at https://ai.dev/rate-limit."
          : "Failed to generate insights. " + detail
      );
    } finally {
      setGeneratingInsights(false);
    }
  };

  const competitorsForDisplay = data?.latestSnapshot?.competitors_data?.length
    ? data.latestSnapshot.competitors_data
    : (competitorDiscovery?.competitors || []).map((c) => ({
        title: c.name,
        url: c.url,
        reviews: {},
      }));

  const diffChanges = data?.diff || [];
  const scoringSummary = data?.scoringSummary ?? null;
  const insights = data?.insights || [];
  const whitespace = data?.whitespace || [];

  return (
    <div className="min-h-screen bg-slate-50 p-8 font-sans text-slate-900">
      <div className="max-w-7xl mx-auto space-y-8">

        {/* Header */}
        <header className="flex justify-between items-end border-b border-slate-200 pb-6">
          <div>
            <h1 className="text-4xl font-extrabold tracking-tight">Competitor Intelligence</h1>
            <p className="text-slate-500 mt-1">Pricing · Messaging · CTAs · Reviews · Whitespace</p>
          </div>

          <div className="flex flex-col items-end gap-3">
            <div className="flex items-center gap-3 flex-wrap justify-end">
              <button
                onClick={handleSeed}
                disabled={seeding || loading || competitorDiscoveryLoading || competitorUrls.length === 0}
                title="Creates a modified baseline snapshot (Hyundai competitors) dated 7 days ago."
                className="bg-amber-500 hover:bg-amber-600 text-white px-4 py-2 rounded-lg font-medium flex items-center gap-2 transition shadow shadow-amber-400/30 disabled:opacity-70 text-sm"
              >
                {seeding ? <RefreshCw className="w-4 h-4 animate-spin" /> : <FlaskConical className="w-4 h-4" />}
                Seed Demo
              </button>
              <button
                onClick={handleGenerateInsights}
                disabled={generatingInsights || loading || seeding}
                title="Call Gemini AI to generate strategic insights and whitespace opportunities from current data."
                className="bg-violet-600 hover:bg-violet-700 text-white px-4 py-2 rounded-lg font-medium flex items-center gap-2 transition shadow shadow-violet-500/30 disabled:opacity-70 text-sm"
              >
                {generatingInsights ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                Generate Insights
              </button>
              <button
                onClick={handleScrape}
                disabled={loading || seeding || competitorDiscoveryLoading || competitorUrls.length === 0}
                className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2 rounded-lg font-medium flex items-center gap-2 transition shadow shadow-blue-500/30 disabled:opacity-70 text-sm"
              >
                {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                Fetch Competitor Pages
              </button>
              <ExportButton />
              <button
                onClick={fetchDashboardData}
                className="p-2 border rounded-lg hover:bg-slate-100 text-slate-600"
                title="Refresh dashboard"
              >
                <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
              </button>
            </div>

            <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer">
              <input
                type="checkbox"
                checked={includeReviews}
                onChange={(e) => setIncludeReviews(e.target.checked)}
                className="rounded"
              />
              Include G2 &amp; Trustpilot reviews <span className="text-slate-400">(slower)</span>
            </label>
          </div>
        </header>

        {/* Seed Demo banner */}
        {seedSuccess && (
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-sm text-amber-800">
            <p className="font-semibold mb-1">Demo baseline seeded for {seedSuccess.length} URL(s)</p>
            <p className="text-amber-700">
              A modified snapshot dated 7 days ago has been saved. Now click
              <strong> Fetch Competitor Pages</strong> with the same URLs — the dashboard will show realistic changes.
            </p>
            <ul className="mt-2 list-disc pl-5 text-amber-600 space-y-0.5">
              {seedSuccess.map((u, i) => <li key={i}>{u}</li>)}
            </ul>
          </div>
        )}

        {/* Error banner */}
        {error && (
          <div className="bg-red-50 text-red-700 p-4 rounded-lg flex items-center gap-3 border border-red-200 text-sm">
            <AlertCircle className="w-5 h-5 shrink-0" />
            {error}
          </div>
        )}

        {/* Loading / seeding state */}
        {(loading || seeding || generatingInsights || competitorDiscoveryLoading) && (
          <div className="text-center py-6 text-slate-500 text-sm flex items-center justify-center gap-2">
            <RefreshCw className="w-4 h-4 animate-spin" />
            {competitorDiscoveryLoading
              ? `Loading competitors for ${USER_COMPANY}…`
              : generatingInsights
                ? "Calling Gemini AI… generating strategic insights and whitespace opportunities."
                : seeding
                  ? "Seeding demo baseline… scraping pages and applying mutations."
                  : includeReviews
                    ? "Scraping pages + G2/Trustpilot reviews… this may take 30–60 seconds."
                    : "Scraping pages…"}
          </div>
        )}

        {/* Empty state */}
        {!data?.latestSnapshot && !loading && !competitorDiscoveryLoading && competitorUrls.length === 0 && (
          <div className="text-center py-20 bg-white rounded-xl border border-dashed border-slate-300">
            <Search className="w-12 h-12 text-slate-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium">No Data Yet</h3>
            <p className="text-slate-500 mt-1 text-sm">
              No competitor URLs found for {USER_COMPANY}.
            </p>
          </div>
        )}

        {/* Main dashboard */}
        {(data?.latestSnapshot || competitorsForDisplay?.length > 0) && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">

            {/* Left column */}
            <div className="lg:col-span-2 space-y-8">
              <DiffPanel changes={diffChanges} scoringSummary={scoringSummary} />

              <section className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
                <h2 className="text-xl font-bold mb-6">
                  {data?.latestSnapshot ? "Current Market Landscape" : `Hyundai Competitors (${competitorUrls.length})`}
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {competitorsForDisplay.map((comp, idx) => (
                    <CompetitorCard key={idx} comp={comp} />
                  ))}
                </div>
              </section>

              <PositioningMatrix positioningData={positioning} />
              <TrendsPanel trendsData={trends} />
              <AdLibraryPanel />
            </div>

            {/* Right column */}
            <div className="space-y-8">
              <InsightsPanel insights={insights} generatedAt={data?.insightsGeneratedAt} />
              <WhitespacePanel whitespace={whitespace} />
            </div>

          </div>
        )}
      </div>
    </div>
  );
}
