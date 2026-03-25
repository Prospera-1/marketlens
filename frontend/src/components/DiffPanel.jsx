import { useState } from 'react';
import { Activity, ChevronDown, ChevronUp } from 'lucide-react';

const CATEGORY_COLORS = {
  'Pricing':          'bg-amber-100  text-amber-800',
  'Messaging':        'bg-purple-100 text-purple-800',
  'CTAs':             'bg-blue-100   text-blue-800',
  'Hero Content':     'bg-indigo-100 text-indigo-800',
  'Positioning':      'bg-pink-100   text-pink-800',
  'Features':         'bg-teal-100   text-teal-800',
  'Social Proof':     'bg-emerald-100 text-emerald-800',
  'G2 Rating':        'bg-orange-100 text-orange-800',
  'Trustpilot Score': 'bg-green-100  text-green-800',
};

const PRIORITY_STYLES = {
  critical: { bar: 'bg-red-500',    badge: 'bg-red-100   text-red-700   border-red-200'   },
  high:     { bar: 'bg-orange-400', badge: 'bg-orange-100 text-orange-700 border-orange-200' },
  medium:   { bar: 'bg-amber-400',  badge: 'bg-amber-100  text-amber-700  border-amber-200'  },
  low:      { bar: 'bg-slate-300',  badge: 'bg-slate-100  text-slate-600  border-slate-200'  },
};

const PRIORITY_ORDER = { critical: 0, high: 1, medium: 2, low: 3 };
const FILTER_OPTIONS = ['all', 'critical', 'high', 'medium', 'low'];

function ScoreBar({ composite, priority }) {
  const style = PRIORITY_STYLES[priority] || PRIORITY_STYLES.low;
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1 bg-slate-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${style.bar}`}
             style={{ width: `${composite * 10}%` }} />
      </div>
      <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded border ${style.badge}`}>
        {priority}
      </span>
      <span className="text-[10px] text-slate-400">{composite}/10</span>
    </div>
  );
}

function ChangeCard({ change }) {
  const [expanded, setExpanded] = useState(false);
  const colorClass = CATEGORY_COLORS[change.category] || 'bg-slate-100 text-slate-700';
  const hasItems = (change.added?.length > 0) || (change.removed?.length > 0);

  return (
    <div className="rounded-lg border border-slate-100 bg-slate-50 overflow-hidden">
      {/* Header row */}
      <div className="p-4 pb-2">
        <div className="flex justify-between items-start mb-2 gap-2">
          <span className="font-semibold text-slate-900 text-sm">{change.brand || 'Unknown'}</span>
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium shrink-0 ${colorClass}`}>
            {change.category || change.type}
          </span>
        </div>
        <p className="text-sm text-slate-600 mb-2">{change.description}</p>
        {change.composite !== undefined && (
          <ScoreBar composite={change.composite} priority={change.priority} />
        )}
      </div>

      {/* Expand / collapse items */}
      {hasItems && (
        <>
          <button
            onClick={() => setExpanded(e => !e)}
            className="w-full flex items-center justify-between px-4 py-1.5 text-xs text-slate-500
                       hover:bg-slate-100 transition border-t border-slate-100"
          >
            <span>{expanded ? 'Hide' : 'Show'} details</span>
            {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>

          {expanded && (
            <div className="px-4 pb-4 space-y-2 pt-2">
              {change.added?.length > 0 && (
                <div className="text-sm text-emerald-700 bg-emerald-50 p-2 rounded border border-emerald-100">
                  <strong className="block mb-1">+ Added</strong>
                  <ul className="space-y-0.5 list-disc pl-4">
                    {change.added.map((a, i) => <li key={i}>{a}</li>)}
                  </ul>
                </div>
              )}
              {change.removed?.length > 0 && (
                <div className="text-sm text-rose-700 bg-rose-50 p-2 rounded border border-rose-100">
                  <strong className="block mb-1">− Removed</strong>
                  <ul className="space-y-0.5 list-disc pl-4">
                    {change.removed.map((r, i) => <li key={i}>{r}</li>)}
                  </ul>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default function DiffPanel({ changes, scoringSummary }) {
  const [filter, setFilter] = useState('all');

  const sorted = [...(changes || [])].sort(
    (a, b) => (PRIORITY_ORDER[a.priority] ?? 4) - (PRIORITY_ORDER[b.priority] ?? 4)
  );

  const filtered = filter === 'all' ? sorted : sorted.filter(c => c.priority === filter);

  return (
    <section className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-5">
        <div className="flex items-center gap-3">
          <Activity className="w-6 h-6 text-purple-600" />
          <div>
            <h2 className="text-xl font-bold">Recent Changes Detected</h2>
            {changes?.length > 0 && (
              <p className="text-xs text-slate-500 mt-0.5">
                {changes.length} change{changes.length !== 1 ? 's' : ''} — sorted by signal importance
              </p>
            )}
          </div>
        </div>

        {/* Priority filter pills */}
        {changes?.length > 0 && (
          <div className="flex gap-1.5 flex-wrap">
            {FILTER_OPTIONS.map(f => {
              const count = f === 'all' ? changes.length : (scoringSummary?.[f] ?? 0);
              const active = filter === f;
              return (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  className={`text-xs px-2.5 py-1 rounded-full border font-medium transition
                    ${active
                      ? 'bg-slate-800 text-white border-slate-800'
                      : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'}`}
                >
                  {f.charAt(0).toUpperCase() + f.slice(1)}
                  {count > 0 && <span className="ml-1 opacity-70">({count})</span>}
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Summary strip */}
      {scoringSummary && Object.values(scoringSummary).some(v => v > 0) && (
        <div className="grid grid-cols-4 gap-2 mb-5">
          {Object.entries(scoringSummary).map(([p, count]) => {
            const style = PRIORITY_STYLES[p];
            return (
              <div key={p} className={`rounded-lg p-2 text-center border ${style.badge}`}>
                <div className="text-xl font-extrabold">{count}</div>
                <div className="text-[10px] uppercase font-semibold opacity-80">{p}</div>
              </div>
            );
          })}
        </div>
      )}

      {/* Change cards */}
      {filtered.length === 0 ? (
        <p className="text-slate-500 text-sm">
          {changes?.length === 0
            ? 'No changes detected since the last snapshot.'
            : `No ${filter} priority changes.`}
        </p>
      ) : (
        <div className="space-y-3">
          {filtered.map((change, idx) => <ChangeCard key={idx} change={change} />)}
        </div>
      )}
    </section>
  );
}
