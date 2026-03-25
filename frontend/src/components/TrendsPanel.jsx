/**
 * TrendsPanel.jsx — Multi-snapshot trend visualisation.
 *
 * Shows four categories of signals detected across all saved snapshots:
 *   - Rising   : a competitor's field is consistently growing
 *   - Falling  : a competitor's field is consistently shrinking
 *   - Volatile : a field that changes on most scrape runs (being tested)
 *   - Converging: a keyword appearing across multiple competitors simultaneously
 *   - Stable   : a field that hasn't changed — deliberate locked-in strategy
 */

import { useState } from 'react';
import {
  TrendingUp, TrendingDown, Zap, GitMerge, Lock,
  BarChart2, ChevronDown, ChevronUp,
} from 'lucide-react';

// ── Type config ───────────────────────────────────────────────────────────────

const TYPE_CONFIG = {
  rising_signal:    { label: 'Rising',     icon: TrendingUp,  bg: 'bg-emerald-50', border: 'border-emerald-200', badge: 'bg-emerald-100 text-emerald-700', icon_color: 'text-emerald-500' },
  falling_signal:   { label: 'Falling',    icon: TrendingDown, bg: 'bg-rose-50',   border: 'border-rose-200',   badge: 'bg-rose-100 text-rose-700',        icon_color: 'text-rose-500'    },
  volatile:         { label: 'Volatile',   icon: Zap,         bg: 'bg-amber-50',  border: 'border-amber-200',  badge: 'bg-amber-100 text-amber-700',       icon_color: 'text-amber-500'   },
  converging_theme: { label: 'Converging', icon: GitMerge,    bg: 'bg-violet-50', border: 'border-violet-200', badge: 'bg-violet-100 text-violet-700',     icon_color: 'text-violet-500'  },
  stable:           { label: 'Stable',     icon: Lock,        bg: 'bg-slate-50',  border: 'border-slate-200',  badge: 'bg-slate-100 text-slate-600',       icon_color: 'text-slate-400'   },
};

const FILTER_OPTIONS = [
  { id: 'all',              label: 'All' },
  { id: 'rising_signal',    label: 'Rising' },
  { id: 'falling_signal',   label: 'Falling' },
  { id: 'volatile',         label: 'Volatile' },
  { id: 'converging_theme', label: 'Converging' },
  { id: 'stable',           label: 'Stable' },
];

// ── Significance bar ──────────────────────────────────────────────────────────

function SignificanceBar({ value }) {
  const clamped = Math.min(10, Math.max(0, value || 0));
  const pct = (clamped / 10) * 100;
  const color = clamped >= 7 ? 'bg-rose-400' : clamped >= 4 ? 'bg-amber-400' : 'bg-slate-300';
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color} transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-slate-400 w-4 text-right">{clamped}</span>
    </div>
  );
}

// ── Individual trend card ─────────────────────────────────────────────────────

function TrendCard({ trend }) {
  const [expanded, setExpanded] = useState(false);
  const cfg = TYPE_CONFIG[trend.type] || TYPE_CONFIG.stable;
  const Icon = cfg.icon;

  const metaItems = [];
  if (trend.field)        metaItems.push({ label: 'Field',        value: trend.field });
  if (trend.competitor)   metaItems.push({ label: 'Competitor',   value: trend.competitor });
  if (trend.keyword)      metaItems.push({ label: 'Keyword',      value: `"${trend.keyword}"` });
  if (trend.change_count) metaItems.push({ label: 'Changes',      value: trend.change_count });
  if (trend.change_rate)  metaItems.push({ label: 'Change rate',  value: `${Math.round(trend.change_rate * 100)}%` });
  if (trend.net_delta)    metaItems.push({ label: 'Net delta',    value: trend.net_delta > 0 ? `+${trend.net_delta}` : trend.net_delta });
  if (trend.count)        metaItems.push({ label: 'Competitors',  value: trend.count });

  return (
    <div className={`rounded-lg border ${cfg.border} ${cfg.bg} p-4 space-y-2`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <Icon className={`w-4 h-4 mt-0.5 shrink-0 ${cfg.icon_color}`} />
          <p className="text-sm text-slate-700 leading-snug">{trend.description}</p>
        </div>
        <span className={`text-xs font-medium px-2 py-0.5 rounded-full shrink-0 ${cfg.badge}`}>
          {cfg.label}
        </span>
      </div>

      <SignificanceBar value={trend.significance} />

      {metaItems.length > 0 && (
        <button
          onClick={() => setExpanded(v => !v)}
          className="flex items-center gap-1 text-xs text-slate-400 hover:text-slate-600 transition pt-1"
        >
          {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          {expanded ? 'Hide details' : 'Details'}
        </button>
      )}

      {expanded && metaItems.length > 0 && (
        <div className="grid grid-cols-2 gap-x-4 gap-y-1 pt-1 border-t border-slate-200/60 mt-1">
          {metaItems.map(({ label, value }) => (
            <div key={label} className="text-xs">
              <span className="text-slate-400">{label}: </span>
              <span className="text-slate-600 font-medium">{String(value)}</span>
            </div>
          ))}
          {trend.competitors && (
            <div className="col-span-2 text-xs">
              <span className="text-slate-400">In: </span>
              <span className="text-slate-600 font-medium">{trend.competitors.join(', ')}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Summary pills row ─────────────────────────────────────────────────────────

function SummaryRow({ summary }) {
  if (!summary) return null;
  const stats = [
    { label: 'Snapshots',  value: summary.snapshots_analysed },
    { label: 'Competitors', value: summary.competitors_tracked },
    { label: 'Rising',     value: summary.rising_signals,     color: 'text-emerald-600' },
    { label: 'Falling',    value: summary.falling_signals,    color: 'text-rose-600' },
    { label: 'Volatile',   value: summary.volatile_fields,    color: 'text-amber-600' },
    { label: 'Converging', value: summary.converging_themes,  color: 'text-violet-600' },
    { label: 'Stable',     value: summary.stable_signals,     color: 'text-slate-500' },
  ];
  return (
    <div className="flex flex-wrap gap-3 text-xs">
      {stats.map(s => (
        <div key={s.label} className="bg-white border border-slate-200 rounded-lg px-3 py-1.5 flex items-center gap-1.5 shadow-xs">
          <span className={`font-bold text-sm ${s.color || 'text-slate-700'}`}>{s.value ?? '—'}</span>
          <span className="text-slate-400">{s.label}</span>
        </div>
      ))}
      {summary.date_range && (
        <div className="bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-slate-400 shadow-xs">
          {summary.date_range.earliest?.slice(0, 16).replace('T', ' ')}
          {' → '}
          {summary.date_range.latest?.slice(0, 16).replace('T', ' ')}
        </div>
      )}
    </div>
  );
}

// ── Main export ───────────────────────────────────────────────────────────────

export default function TrendsPanel({ trendsData }) {
  const [activeFilter, setActiveFilter] = useState('all');

  if (!trendsData) return null;

  if (trendsData.status === 'insufficient_data') {
    return (
      <section className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
        <div className="flex items-center gap-2 mb-2">
          <BarChart2 className="w-5 h-5 text-slate-400" />
          <h2 className="text-xl font-bold">Trend Analysis</h2>
        </div>
        <p className="text-sm text-slate-500 bg-slate-50 rounded-lg p-4 border border-dashed border-slate-300">
          {trendsData.message}
        </p>
      </section>
    );
  }

  const trends = trendsData.trends || [];
  const visible = activeFilter === 'all' ? trends : trends.filter(t => t.type === activeFilter);

  const counts = FILTER_OPTIONS.slice(1).reduce((acc, opt) => {
    acc[opt.id] = trends.filter(t => t.type === opt.id).length;
    return acc;
  }, {});

  return (
    <section className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <BarChart2 className="w-5 h-5 text-indigo-500" />
          <h2 className="text-xl font-bold">Trend Analysis</h2>
        </div>
        <span className="text-xs text-slate-400">{trends.length} signals detected</span>
      </div>

      <SummaryRow summary={trendsData.summary} />

      {/* Filter pills */}
      <div className="flex flex-wrap gap-2">
        {FILTER_OPTIONS.map(opt => {
          const count = opt.id === 'all' ? trends.length : (counts[opt.id] || 0);
          const active = activeFilter === opt.id;
          return (
            <button
              key={opt.id}
              onClick={() => setActiveFilter(opt.id)}
              className={`px-3 py-1 rounded-full text-xs font-medium border transition ${
                active
                  ? 'bg-indigo-600 text-white border-indigo-600'
                  : 'bg-white text-slate-600 border-slate-200 hover:border-slate-400'
              }`}
            >
              {opt.label} <span className={active ? 'text-indigo-200' : 'text-slate-400'}>{count}</span>
            </button>
          );
        })}
      </div>

      {/* Trend cards */}
      {visible.length === 0 ? (
        <p className="text-sm text-slate-400 text-center py-6 bg-slate-50 rounded-lg border border-dashed border-slate-200">
          No {activeFilter === 'all' ? '' : activeFilter.replace('_', ' ')} signals found in this filter.
        </p>
      ) : (
        <div className="space-y-3">
          {visible.map((trend, i) => (
            <TrendCard key={i} trend={trend} />
          ))}
        </div>
      )}
    </section>
  );
}
