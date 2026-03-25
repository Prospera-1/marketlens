import { TrendingUp, Target, Plus, ExternalLink, Zap } from 'lucide-react';

// ── Score pill ────────────────────────────────────────────────────────────────

function ScoreBadge({ label, value, color }) {
  const colors = {
    indigo: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30',
    amber:  'bg-amber-500/20  text-amber-300  border-amber-500/30',
    emerald:'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
    slate:  'bg-white/10      text-white       border-white/20',
  };
  return (
    <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full border ${colors[color] || colors.slate}`}>
      <span className="opacity-70">{label}</span>
      <span className="font-bold">{value}</span>
    </span>
  );
}

// ── Single insight card ───────────────────────────────────────────────────────

function InsightCard({ insight }) {
  const { title, description, action, scores, source_traces } = insight;

  // Support both the new {scores} shape and the legacy flat {score} number
  const composite = scores?.composite ?? insight.score ?? '–';
  const novelty   = scores?.novelty;
  const frequency = scores?.frequency;
  const relevance = scores?.relevance;

  const compositeColor =
    composite >= 8 ? 'text-emerald-300' :
    composite >= 5 ? 'text-amber-300' :
    'text-slate-400';

  return (
    <div className="bg-white/10 rounded-lg p-4 border border-white/10 backdrop-blur-sm space-y-3">

      {/* Header */}
      <div className="flex justify-between items-start gap-2">
        <h3 className="font-bold text-indigo-200 leading-tight">{title}</h3>
        <span className={`text-lg font-extrabold shrink-0 ${compositeColor}`}>
          {composite}<span className="text-xs font-normal opacity-60">/10</span>
        </span>
      </div>

      {/* Score breakdown */}
      {(novelty || frequency || relevance) && (
        <div className="flex flex-wrap gap-1.5">
          {novelty   && <ScoreBadge label="Novelty"   value={novelty}   color="indigo" />}
          {frequency && <ScoreBadge label="Frequency" value={frequency} color="amber"  />}
          {relevance && <ScoreBadge label="Relevance" value={relevance} color="emerald"/>}
        </div>
      )}

      {/* Description */}
      <p className="text-sm text-slate-300 leading-relaxed">{description}</p>

      {/* Recommended action */}
      {action && (
        <div className="bg-indigo-950/50 border border-indigo-500/30 p-3 rounded text-sm">
          <span className="text-amber-400 font-bold flex items-center gap-1 mb-1">
            <Zap className="w-3.5 h-3.5" /> Recommended Action
          </span>
          <span className="text-slate-200">{action}</span>
        </div>
      )}

      {/* Source traces */}
      {source_traces?.length > 0 && (
        <div className="border-t border-white/10 pt-2 space-y-1">
          <span className="text-xs text-slate-500 uppercase tracking-wide">Sources</span>
          {source_traces.map((trace, i) => {
            const url    = typeof trace === 'string' ? trace : trace.url;
            const field  = trace.field;
            const snippet = trace.snippet;
            return (
              <div key={i} className="text-xs text-slate-400 space-y-0.5">
                <a href={url} target="_blank" rel="noreferrer"
                   className="flex items-center gap-1 text-indigo-400 hover:text-indigo-300 truncate">
                  <ExternalLink className="w-3 h-3 shrink-0" />
                  {url}
                </a>
                {field && (
                  <span className="text-slate-500">
                    <span className="text-slate-400 font-medium">{field}:</span>{' '}
                    {snippet ? `"${snippet}"` : ''}
                  </span>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Legacy: flat source_urls (backward compat) */}
      {!source_traces && insight.source_urls?.length > 0 && (
        <div className="border-t border-white/10 pt-2">
          {insight.source_urls.map((u, i) => (
            <a key={i} href={u} target="_blank" rel="noreferrer"
               className="flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300 truncate">
              <ExternalLink className="w-3 h-3 shrink-0" />
              {u}
            </a>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Insights panel ────────────────────────────────────────────────────────────

export function InsightsPanel({ insights }) {
  return (
    <section className="bg-gradient-to-br from-indigo-900 to-slate-900 text-white rounded-xl shadow-lg p-6">
      <div className="flex items-center mb-5">
        <TrendingUp className="w-6 h-6 text-indigo-400 mr-3" />
        <h2 className="text-xl font-bold">Strategic Insights</h2>
      </div>

      {!insights || insights.length === 0 ? (
        <p className="text-indigo-200/60 text-sm">
          Waiting for market shifts — run the scraper, then seed a baseline to see insights here.
        </p>
      ) : (
        <div className="space-y-4">
          {[...insights]
            .sort((a, b) => (b.scores?.composite ?? b.score ?? 0) - (a.scores?.composite ?? a.score ?? 0))
            .map((insight, idx) => (
              <InsightCard key={idx} insight={insight} />
            ))}
        </div>
      )}
    </section>
  );
}

// ── Whitespace panel ──────────────────────────────────────────────────────────

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
          {[...whitespace]
            .sort((a, b) => {
              const sa = typeof a === 'object' ? (a.opportunity_score ?? 0) : 0;
              const sb = typeof b === 'object' ? (b.opportunity_score ?? 0) : 0;
              return sb - sa;
            })
            .map((item, idx) => {
              if (typeof item === 'string') {
                return (
                  <li key={idx} className="flex items-start gap-3">
                    <Plus className="w-5 h-5 text-emerald-500 mt-0.5 shrink-0" />
                    <span className="text-sm text-slate-700 leading-relaxed">{item}</span>
                  </li>
                );
              }

              const { description, opportunity_score, suggested_action, supporting_evidence } = item;
              const scoreColor =
                opportunity_score >= 8 ? 'bg-emerald-100 text-emerald-700 border-emerald-200' :
                opportunity_score >= 5 ? 'bg-amber-100  text-amber-700  border-amber-200' :
                                         'bg-slate-100  text-slate-600  border-slate-200';

              return (
                <li key={idx} className="rounded-lg border border-slate-200 p-4 space-y-2 bg-slate-50">
                  <div className="flex justify-between items-start gap-2">
                    <p className="text-sm font-semibold text-slate-800 leading-snug">{description}</p>
                    {opportunity_score && (
                      <span className={`text-xs font-bold px-2 py-0.5 rounded-full border shrink-0 ${scoreColor}`}>
                        {opportunity_score}/10
                      </span>
                    )}
                  </div>

                  {suggested_action && (
                    <div className="flex items-start gap-2 text-sm">
                      <Zap className="w-4 h-4 text-amber-500 mt-0.5 shrink-0" />
                      <span className="text-slate-600">{suggested_action}</span>
                    </div>
                  )}

                  {supporting_evidence && (
                    <p className="text-xs text-slate-400 italic border-t border-slate-200 pt-2">
                      {supporting_evidence}
                    </p>
                  )}
                </li>
              );
            })}
        </ul>
      )}
    </section>
  );
}
