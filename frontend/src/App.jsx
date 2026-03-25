import { useState, useEffect } from 'react';
import axios from 'axios';
import { RefreshCw, Play, AlertCircle, Search, FlaskConical } from 'lucide-react';
import CompetitorCard from './components/CompetitorCard';
import DiffPanel from './components/DiffPanel';
import { InsightsPanel, WhitespacePanel } from './components/InsightsPanel';

const API_BASE = "http://localhost:8000/api";

export default function App() {
  const [urls, setUrls] = useState("");
  const [includeReviews, setIncludeReviews] = useState(true);
  const [loading, setLoading] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const [seedSuccess, setSeedSuccess] = useState(false);
  const [error, setError] = useState("");
  const [data, setData] = useState(null);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      setError("");

      const [snapshotsRes, diffRes, insightsRes] = await Promise.all([
        axios.get(`${API_BASE}/snapshots`),
        axios.get(`${API_BASE}/diff`),
        axios.get(`${API_BASE}/insights`),
      ]);

      const snapshots = snapshotsRes.data.snapshots || [];
      const diff = diffRes.data;
      const insightsData = insightsRes.data;

      setData({
        latestSnapshot: snapshots.length > 0 ? snapshots[0] : null,
        diff: diff.changes || [],
        insights: insightsData.insights || [],
        whitespace: insightsData.whitespace || [],
      });
    } catch (err) {
      setError("Failed to fetch dashboard data. Ensure backend is running. " + err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchDashboardData(); }, []);

  const handleScrape = async () => {
    const urlList = urls.split(',').map(u => u.trim()).filter(u => u);
    if (urlList.length === 0) return;

    setLoading(true);
    setError("");
    setSeedSuccess(false);
    try {
      await axios.post(`${API_BASE}/fetch`, { urls: urlList, include_reviews: includeReviews });
      await fetchDashboardData();
      setUrls("");
    } catch (err) {
      setError("Failed to scrape URLs. " + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const handleSeed = async () => {
    const urlList = urls.split(',').map(u => u.trim()).filter(u => u);
    // If no URLs typed, the backend will reuse the latest snapshot's URLs
    setSeeding(true);
    setError("");
    setSeedSuccess(false);
    try {
      const res = await axios.post(`${API_BASE}/seed`, { urls: urlList, days_ago: 7 });
      setSeedSuccess(res.data.urls_seeded);
    } catch (err) {
      setError("Seed failed. " + (err.response?.data?.detail || err.message));
    } finally {
      setSeeding(false);
    }
  };

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
            <div className="flex items-center gap-3">
              <input
                type="text"
                placeholder="Enter URLs (comma separated)"
                className="px-4 py-2 border rounded-lg w-80 shadow-sm focus:ring-2 focus:ring-blue-500 outline-none text-sm"
                value={urls}
                onChange={e => setUrls(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleScrape()}
              />
              <button
                onClick={handleSeed}
                disabled={seeding || loading}
                title="Creates a modified baseline snapshot dated 7 days ago. Then run the scraper to see changes."
                className="bg-amber-500 hover:bg-amber-600 text-white px-4 py-2 rounded-lg font-medium flex items-center gap-2 transition shadow shadow-amber-400/30 disabled:opacity-70 text-sm"
              >
                {seeding ? <RefreshCw className="w-4 h-4 animate-spin" /> : <FlaskConical className="w-4 h-4" />}
                Seed Demo
              </button>
              <button
                onClick={handleScrape}
                disabled={loading || seeding}
                className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2 rounded-lg font-medium flex items-center gap-2 transition shadow shadow-blue-500/30 disabled:opacity-70 text-sm"
              >
                {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                Run Scraper
              </button>
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
                onChange={e => setIncludeReviews(e.target.checked)}
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
              <strong> Run Scraper</strong> with the same URLs — the dashboard will show realistic changes.
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
        {(loading || seeding) && (
          <div className="text-center py-6 text-slate-500 text-sm flex items-center justify-center gap-2">
            <RefreshCw className="w-4 h-4 animate-spin" />
            {seeding
              ? "Seeding demo baseline… scraping pages and applying mutations."
              : includeReviews
                ? "Scraping pages + G2/Trustpilot reviews… this may take 30–60 seconds."
                : "Scraping pages…"}
          </div>
        )}

        {/* Empty state */}
        {!data?.latestSnapshot && !loading && (
          <div className="text-center py-20 bg-white rounded-xl border border-dashed border-slate-300">
            <Search className="w-12 h-12 text-slate-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium">No Data Yet</h3>
            <p className="text-slate-500 mt-1 text-sm">
              Add competitor URLs above to generate the first snapshot.
            </p>
          </div>
        )}

        {/* Main dashboard */}
        {data?.latestSnapshot && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">

            {/* Left column */}
            <div className="lg:col-span-2 space-y-8">
              <DiffPanel changes={data.diff} />

              <section className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
                <h2 className="text-xl font-bold mb-6">Current Market Landscape</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {data.latestSnapshot.competitors_data.map((comp, idx) => (
                    <CompetitorCard key={idx} comp={comp} />
                  ))}
                </div>
              </section>
            </div>

            {/* Right column */}
            <div className="space-y-8">
              <InsightsPanel insights={data.insights} />
              <WhitespacePanel whitespace={data.whitespace} />
            </div>

          </div>
        )}
      </div>
    </div>
  );
}
