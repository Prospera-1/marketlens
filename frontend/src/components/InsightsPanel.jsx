import { TrendingUp, Target, Plus } from 'lucide-react';

export function InsightsPanel({ insights }) {
  return (
    <section className="bg-gradient-to-br from-indigo-900 to-slate-900 text-white rounded-xl shadow-lg p-6">
      <div className="flex items-center mb-6">
        <TrendingUp className="w-6 h-6 text-indigo-400 mr-3" />
        <h2 className="text-xl font-bold">Strategic Insights</h2>
      </div>

      {!insights || insights.length === 0 ? (
        <p className="text-indigo-200/60 text-sm">
          Insufficient data changes to generate insights. Waiting for market shifts…
        </p>
      ) : (
        <div className="space-y-5">
          {insights.map((insight, idx) => (
            <div key={idx} className="bg-white/10 rounded-lg p-4 border border-white/10 backdrop-blur-sm">
              <div className="flex justify-between items-start mb-2">
                <h3 className="font-bold text-indigo-300 leading-tight">{insight.title}</h3>
                <span className="text-xs font-bold px-2 py-1 bg-indigo-500/30 text-indigo-200 rounded ml-2 shrink-0">
                  {insight.score}/10
                </span>
              </div>
              <p className="text-sm text-slate-300 mb-3 leading-relaxed">{insight.description}</p>
              <div className="bg-indigo-950/50 border border-indigo-500/30 p-3 rounded text-sm">
                <span className="text-amber-400 font-bold block mb-1">Recommended Action</span>
                {insight.action}
              </div>
              {insight.source_urls?.length > 0 && (
                <div className="mt-3 text-xs text-slate-400">
                  Source:{' '}
                  {insight.source_urls.map((u, i) => (
                    <a key={i} href={u} target="_blank" rel="noreferrer"
                       className="text-indigo-400 hover:text-indigo-300 truncate block">
                      {u}
                    </a>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

export function WhitespacePanel({ whitespace }) {
  return (
    <section className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 border-t-4 border-t-emerald-500">
      <div className="flex items-center mb-5">
        <Target className="w-6 h-6 text-emerald-600 mr-3" />
        <h2 className="text-xl font-bold text-slate-900">Whitespace Opportunities</h2>
      </div>

      {!whitespace || whitespace.length === 0 ? (
        <p className="text-slate-500 text-sm">Evaluating market gaps…</p>
      ) : (
        <ul className="space-y-4">
          {whitespace.map((item, idx) => {
            const text = typeof item === 'string' ? item : (item.description || item.title || JSON.stringify(item));
            return (
              <li key={idx} className="flex items-start">
                <Plus className="w-5 h-5 text-emerald-500 mt-0.5 mr-3 shrink-0" />
                <span className="text-sm text-slate-700 font-medium leading-relaxed">{text}</span>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
