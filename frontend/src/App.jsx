import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { RefreshCw, Play, AlertCircle, TrendingUp, Target, Plus, Search, Activity } from 'lucide-react';

const API_BASE = "http://localhost:8000/api";

function App() {
  const [urls, setUrls] = useState("");
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      setError("");
      
      const snapshotsRes = await axios.get(`${API_BASE}/snapshots`);
      const snapshots = snapshotsRes.data.snapshots || [];
      
      const diffRes = await axios.get(`${API_BASE}/diff`);
      const diff = diffRes.data;
      
      const insightsRes = await axios.get(`${API_BASE}/insights`);
      const insightsData = insightsRes.data;
      
      setData({
        latestSnapshot: snapshots.length > 0 ? snapshots[0] : null,
        diff: diff.changes || [],
        insights: insightsData.insights || [],
        whitespace: insightsData.whitespace || []
      });
      
    } catch (err) {
      setError("Failed to fetch dashboard data. Ensure backend is running. " + err.message);
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const handleScrape = async () => {
    const urlList = urls.split(',').map(u => u.trim()).filter(u => u);
    if (urlList.length === 0) return;
    
    setLoading(true);
    try {
      await axios.post(`${API_BASE}/fetch`, { urls: urlList });
      await fetchDashboardData();
      setUrls("");
    } catch (err) {
      setError("Failed to scrape URLs. " + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 p-8 font-sans text-slate-900">
      <div className="max-w-7xl mx-auto space-y-8">
        
        {/* Header Section */}
        <header className="flex justify-between items-end border-b border-slate-200 pb-6">
          <div>
            <h1 className="text-4xl font-extrabold tracking-tight text-slate-900">Competitor Intelligence</h1>
            <p className="text-slate-500 mt-2">AI-driven insights & whitespace detection</p>
          </div>
          <div className="flex space-x-4 items-center">
             <input 
               type="text" 
               placeholder="Enter URLs (comma separated)"
               className="px-4 py-2 border rounded-lg w-80 shadow-sm focus:ring-2 focus:ring-blue-500 outline-none"
               value={urls}
               onChange={(e) => setUrls(e.target.value)}
             />
             <button 
                onClick={handleScrape}
                disabled={loading}
                className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2 rounded-lg font-medium flex items-center transition shadow shadow-blue-500/30 disabled:opacity-70"
             >
                {loading ? <RefreshCw className="w-5 h-5 animate-spin mr-2"/> : <Play className="w-5 h-5 mr-2" />}
                Run Scraper
             </button>
             <button 
               onClick={fetchDashboardData} 
               className="p-2 border rounded-lg hover:bg-slate-100 text-slate-600"
             >
               <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
             </button>
          </div>
        </header>

        {error && (
          <div className="bg-red-50 text-red-700 p-4 rounded-lg flex items-center border border-red-200">
            <AlertCircle className="w-5 h-5 mr-3" />
            {error}
          </div>
        )}

        {!data?.latestSnapshot ? (
          <div className="text-center py-20 bg-white rounded-xl border border-dashed border-slate-300">
             <Search className="w-12 h-12 text-slate-300 mx-auto mb-4" />
             <h3 className="text-lg font-medium text-slate-900">No Data Found</h3>
             <p className="text-slate-500">Add competitor URLs to generate the first snapshot and insights.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            
            {/* Left Column: Raw Data & Diff */}
            <div className="lg:col-span-2 space-y-8">
              
              {/* Diff Engine Results */}
              <section className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
                <div className="flex items-center mb-6">
                  <Activity className="w-6 h-6 text-purple-600 mr-3" />
                  <h2 className="text-xl font-bold">Recent Changes Detected</h2>
                </div>
                {data.diff.length === 0 ? (
                  <p className="text-slate-500">No changes detected since the last snapshot.</p>
                ) : (
                  <div className="space-y-4">
                    {data.diff.map((change, idx) => (
                      <div key={idx} className="p-4 rounded-lg border border-slate-100 bg-slate-50">
                         <div className="flex justify-between font-medium mb-2">
                            <span className="text-slate-900">{change.brand || 'Unknown'}</span>
                            <span className="text-xs px-2 py-1 bg-purple-100 text-purple-800 rounded-full">{change.category || change.type}</span>
                         </div>
                         <p className="text-sm text-slate-700 mt-1 mb-3">{change.description}</p>
                         
                         {change.added && change.added.length > 0 && (
                           <div className="mt-2 text-sm text-emerald-700 bg-emerald-50 p-2 rounded border border-emerald-100">
                             <strong>+ Added:</strong> {change.added.join(', ')}
                           </div>
                         )}
                         {change.removed && change.removed.length > 0 && (
                           <div className="mt-2 text-sm text-rose-700 bg-rose-50 p-2 rounded border border-rose-100">
                             <strong>- Removed:</strong> {change.removed.join(', ')}
                           </div>
                         )}
                      </div>
                    ))}
                  </div>
                )}
              </section>

              {/* Current Snapshot Overview */}
              <section className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
                 <h2 className="text-xl font-bold mb-6 text-slate-900">Current Market Landscape</h2>
                 <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                   {data.latestSnapshot.competitors_data.map((comp, idx) => (
                      <div key={idx} className="border border-slate-200 rounded-lg p-5">
                         <h3 className="font-bold text-lg mb-1">{comp.title || comp.url}</h3>
                         <a href={comp.url} target="_blank" rel="noreferrer" className="text-sm text-blue-600 hover:underline mb-4 block">Visit Site</a>
                         
                         <div className="space-y-4">
                           <div>
                             <h4 className="text-xs uppercase tracking-wider text-slate-500 font-semibold mb-2">Pricing Models</h4>
                             {comp.pricing.length > 0 ? (
                               <ul className="list-disc pl-4 text-sm space-y-1 text-slate-700">
                                 {comp.pricing.slice(0,3).map((p, i) => <li key={i}>{p}</li>)}
                               </ul>
                             ) : <span className="text-sm text-slate-400">None detected</span>}
                           </div>
                           
                           <div>
                             <h4 className="text-xs uppercase tracking-wider text-slate-500 font-semibold mb-2">Key Features</h4>
                             {comp.features.length > 0 ? (
                               <ul className="list-disc pl-4 text-sm space-y-1 text-slate-700">
                                 {comp.features.slice(0,4).map((f, i) => <li key={i}>{f}</li>)}
                               </ul>
                             ) : <span className="text-sm text-slate-400">None detected</span>}
                           </div>
                         </div>
                      </div>
                   ))}
                 </div>
              </section>
            </div>

            {/* Right Column: AI Insights & Whitespace */}
            <div className="space-y-8">
               
               {/* Insight Engine Results */}
               <section className="bg-gradient-to-br from-indigo-900 to-slate-900 text-white rounded-xl shadow-lg p-6">
                  <div className="flex items-center mb-6">
                    <TrendingUp className="w-6 h-6 text-indigo-400 mr-3" />
                    <h2 className="text-xl font-bold">Strategic Insights</h2>
                  </div>
                  
                  {!data.insights || data.insights.length === 0 ? (
                    <p className="text-indigo-200/60 text-sm">Insufficient data changes to generate insights. Waiting for market shifts...</p>
                  ) : (
                    <div className="space-y-5">
                      {data.insights.map((insight, idx) => (
                        <div key={idx} className="bg-white/10 rounded-lg p-4 border border-white/10 backdrop-blur-sm">
                           <div className="flex justify-between items-start mb-2">
                             <h3 className="font-bold text-indigo-300 leading-tight">{insight.title}</h3>
                             <span className="flex items-center text-xs font-bold px-2 py-1 bg-indigo-500/30 text-indigo-200 rounded">
                               {insight.score}/10
                             </span>
                           </div>
                           <p className="text-sm text-slate-300 mb-3 leading-relaxed">{insight.description}</p>
                           <div className="bg-indigo-950/50 border border-indigo-500/30 p-3 rounded text-sm">
                              <span className="text-amber-400 font-bold block mb-1">Recommended Action:</span>
                              {insight.action}
                           </div>
                           {insight.source_urls && (
                              <div className="mt-3 text-xs text-slate-400">
                                Trace: {insight.source_urls.map((u,i) => <a key={i} href={u} target="_blank" rel="noreferrer" className="text-indigo-400 hover:text-indigo-300 truncate block">{u}</a>)}
                              </div>
                           )}
                        </div>
                      ))}
                    </div>
                  )}
               </section>

               {/* Whitespace Detection */}
               <section className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 border-t-4 border-t-emerald-500">
                  <div className="flex items-center mb-5">
                    <Target className="w-6 h-6 text-emerald-600 mr-3" />
                    <h2 className="text-xl font-bold text-slate-900">Whitespace Opportunities</h2>
                  </div>
                  
                  {!data.whitespace || data.whitespace.length === 0 ? (
                    <p className="text-slate-500 text-sm">Evaluating market gaps...</p>
                  ) : (
                    <ul className="space-y-4">
                      {typeof data.whitespace[0] === 'string' ? data.whitespace.map((item, idx) => (
                        <li key={idx} className="flex items-start">
                          <Plus className="w-5 h-5 text-emerald-500 mt-0.5 mr-3 flex-shrink-0" />
                          <span className="text-sm text-slate-700 font-medium leading-relaxed">{item}</span>
                        </li>
                      )) : data.whitespace.map((item, idx) => (
                        <li key={idx} className="flex items-start">
                          <Plus className="w-5 h-5 text-emerald-500 mt-0.5 mr-3 flex-shrink-0" />
                          <span className="text-sm text-slate-700 font-medium leading-relaxed">{item.description || item.title || JSON.stringify(item)}</span>
                        </li>
                      ))}
                    </ul>
                  )}
               </section>

            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
