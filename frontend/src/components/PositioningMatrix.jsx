import { useState } from 'react';
import { Map, AlertTriangle, ChevronDown, ChevronUp } from 'lucide-react';

// ── Colour palette for competitors ───────────────────────────────────────────
const COLORS = [
  { bg: 'bg-blue-500',   text: 'text-blue-700',   border: 'border-blue-400',   dot: '#3b82f6' },
  { bg: 'bg-rose-500',   text: 'text-rose-700',   border: 'border-rose-400',   dot: '#f43f5e' },
  { bg: 'bg-amber-500',  text: 'text-amber-700',  border: 'border-amber-400',  dot: '#f59e0b' },
  { bg: 'bg-emerald-500',text: 'text-emerald-700',border: 'border-emerald-400',dot: '#10b981' },
  { bg: 'bg-violet-500', text: 'text-violet-700', border: 'border-violet-400', dot: '#8b5cf6' },
  { bg: 'bg-cyan-500',   text: 'text-cyan-700',   border: 'border-cyan-400',   dot: '#06b6d4' },
];

// ── Axis label component ─────────────────────────────────────────────────────
function AxisLabel({ text, className }) {
  return (
    <span className={`text-xs font-semibold text-slate-500 uppercase tracking-wider ${className}`}>
      {text}
    </span>
  );
}

// ── Competitor dot on the matrix ─────────────────────────────────────────────
function CompetitorDot({ profile, color, isActive, onClick }) {
  // cost score 0–10: x=0% (left=cost-leader) to x=100% (right=premium)
  // sales score 0–10: y=0% (top=sales-led) to y=100% (bottom=self-serve)
  const x = (profile.scores.cost  / 10) * 100;
  const y = ((10 - profile.scores.sales) / 10) * 100;

  // Clamp to keep dots fully inside the plot area
  const cx = Math.max(4, Math.min(96, x));
  const cy = Math.max(4, Math.min(96, y));

  const shortName = profile.title.length > 14
    ? profile.title.slice(0, 13) + '…'
    : profile.title;

  return (
    <button
      onClick={onClick}
      style={{ left: `${cx}%`, top: `${cy}%` }}
      className={`
        absolute -translate-x-1/2 -translate-y-1/2 z-10
        flex flex-col items-center group transition-transform
        ${isActive ? 'scale-125' : 'hover:scale-110'}
      `}
      title={profile.title}
    >
      <div
        className={`
          w-4 h-4 rounded-full border-2 border-white shadow-md transition-all
          ${isActive ? 'ring-2 ring-offset-1 ring-slate-800' : ''}
        `}
        style={{ background: color.dot }}
      />
      <span
        className={`
          mt-1 text-[10px] font-semibold px-1 py-0.5 rounded whitespace-nowrap
          bg-white/90 shadow-sm border ${color.border} ${color.text}
        `}
      >
        {shortName}
      </span>
    </button>
  );
}

// ── Profile detail card ───────────────────────────────────────────────────────
function ProfileDetail({ profile, color }) {
  if (!profile) return null;
  const { title, url, labels, scores, evidence } = profile;

  return (
    <div className={`rounded-lg border-l-4 bg-slate-50 p-4 space-y-3`}
         style={{ borderLeftColor: color.dot }}>
      <div>
        <p className="font-bold text-slate-800 text-sm">{title}</p>
        <a href={url} target="_blank" rel="noreferrer"
           className="text-xs text-slate-400 hover:text-slate-600 truncate block">{url}</a>
      </div>

      {/* Score bars */}
      <div className="space-y-1.5">
        {[
          { key: 'cost',    low: 'Cost-Leader', high: 'Premium',       val: scores.cost    },
          { key: 'sales',   low: 'Self-Serve',  high: 'Sales-Led',     val: scores.sales   },
          { key: 'outcome', low: 'Feature-Rich',high: 'Outcome-Driven',val: scores.outcome },
        ].map(({ key, low, high, val }) => (
          <div key={key}>
            <div className="flex justify-between text-[10px] text-slate-500 mb-0.5">
              <span>{low}</span><span>{high}</span>
            </div>
            <div className="h-1.5 bg-slate-200 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all"
                style={{ width: `${val * 10}%`, background: color.dot }}
              />
            </div>
            <p className="text-[10px] text-right text-slate-400 mt-0.5 font-medium">
              {labels[key]}
            </p>
          </div>
        ))}
      </div>

      {/* Evidence snippets */}
      {(evidence?.ctas?.length > 0 || evidence?.pricing?.length > 0) && (
        <div className="border-t border-slate-200 pt-2 space-y-1">
          <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wide">Signal evidence</p>
          {[...(evidence.ctas || []), ...(evidence.pricing || [])].slice(0, 3).map((e, i) => (
            <p key={i} className="text-[11px] text-slate-600 italic">"{e}"</p>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Overused angles panel ─────────────────────────────────────────────────────
function OverusedAnglesPanel({ angles }) {
  const [expanded, setExpanded] = useState(false);
  if (!angles || angles.length === 0) return null;

  const visible = expanded ? angles : angles.slice(0, 3);

  return (
    <div className="mt-6 border-t border-slate-200 pt-5">
      <div className="flex items-center gap-2 mb-3">
        <AlertTriangle className="w-4 h-4 text-amber-500" />
        <h3 className="text-sm font-bold text-slate-800">Overused Positioning Angles</h3>
        <span className="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full font-medium">
          {angles.length} saturated
        </span>
      </div>
      <div className="space-y-3">
        {visible.map((item, i) => (
          <div key={i} className="bg-amber-50 border border-amber-200 rounded-lg p-3 space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold text-slate-800">{item.angle}</span>
              <span className="text-xs font-bold text-amber-700 bg-amber-100 px-2 py-0.5 rounded-full">
                {Math.round(item.saturation * 100)}% of competitors
              </span>
            </div>
            <p className="text-xs text-slate-600">{item.implication}</p>
            {item.whitespace_hint && (
              <p className="text-xs text-emerald-700 bg-emerald-50 rounded p-2 border border-emerald-200">
                <span className="font-semibold">Whitespace: </span>{item.whitespace_hint}
              </p>
            )}
            {item.competitors && (
              <p className="text-[10px] text-slate-400">
                Used by: {item.competitors.join(', ')}
              </p>
            )}
          </div>
        ))}
      </div>
      {angles.length > 3 && (
        <button
          onClick={() => setExpanded(v => !v)}
          className="flex items-center gap-1 text-xs text-slate-400 hover:text-slate-600 mt-2 transition"
        >
          {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          {expanded ? 'Show less' : `Show ${angles.length - 3} more`}
        </button>
      )}
    </div>
  );
}


// ── Main matrix component ─────────────────────────────────────────────────────
export default function PositioningMatrix({ positioningData }) {
  const [activeIdx, setActiveIdx] = useState(null);

  if (!positioningData?.profiles?.length) {
    return (
      <section className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
        <div className="flex items-center gap-3 mb-4">
          <Map className="w-6 h-6 text-slate-400" />
          <h2 className="text-xl font-bold text-slate-900">Competitive Positioning Matrix</h2>
        </div>
        <p className="text-slate-500 text-sm">Scrape competitors to generate the positioning map.</p>
      </section>
    );
  }

  const { profiles, axes, axis_leaders, overused_angles } = positioningData;
  const activeProfile = activeIdx !== null ? profiles[activeIdx] : null;
  const activeColor   = activeIdx !== null ? COLORS[activeIdx % COLORS.length] : null;

  return (
    <section className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
      <div className="flex items-center gap-3 mb-6">
        <Map className="w-6 h-6 text-indigo-500" />
        <div>
          <h2 className="text-xl font-bold text-slate-900">Competitive Positioning Matrix</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            X = {axes?.x?.label} &nbsp;·&nbsp; Y = {axes?.y?.label} &nbsp;·&nbsp;
            Bar = {axes?.z?.label}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* 2D scatter plot */}
        <div className="lg:col-span-2">
          {/* Y-axis top label */}
          <div className="flex justify-center mb-1">
            <AxisLabel text={axes?.y?.high ?? 'Sales-Led'} />
          </div>

          <div className="flex items-center gap-2">
            {/* Y-axis left label */}
            <div className="flex flex-col items-center" style={{ minWidth: '4rem' }}>
              <AxisLabel text={axes?.x?.low ?? 'Cost-Leader'} className="[writing-mode:vertical-rl] rotate-180" />
            </div>

            {/* Plot area */}
            <div className="relative flex-1 aspect-square bg-slate-50 rounded-xl border border-slate-200 overflow-hidden">
              {/* Quadrant shading */}
              <div className="absolute inset-0 grid grid-cols-2 grid-rows-2 opacity-30 pointer-events-none">
                <div className="bg-blue-100  rounded-tl-xl" title="Sales-Led + Cost-Leader" />
                <div className="bg-violet-100 rounded-tr-xl" title="Sales-Led + Premium" />
                <div className="bg-emerald-100 rounded-bl-xl" title="Self-Serve + Cost-Leader" />
                <div className="bg-amber-100  rounded-br-xl" title="Self-Serve + Premium" />
              </div>

              {/* Axis lines */}
              <div className="absolute inset-0 pointer-events-none">
                <div className="absolute left-1/2 top-0 bottom-0 w-px bg-slate-300 opacity-60" />
                <div className="absolute top-1/2 left-0 right-0 h-px bg-slate-300 opacity-60" />
              </div>

              {/* Quadrant labels */}
              <div className="absolute top-2 left-2 text-[9px] text-slate-400 font-medium">Sales-Led + Value</div>
              <div className="absolute top-2 right-2 text-[9px] text-slate-400 font-medium text-right">Sales-Led + Premium</div>
              <div className="absolute bottom-2 left-2 text-[9px] text-slate-400 font-medium">Self-Serve + Value</div>
              <div className="absolute bottom-2 right-2 text-[9px] text-slate-400 font-medium text-right">Self-Serve + Premium</div>

              {/* Competitor dots */}
              {profiles.map((profile, idx) => (
                <CompetitorDot
                  key={idx}
                  profile={profile}
                  color={COLORS[idx % COLORS.length]}
                  isActive={activeIdx === idx}
                  onClick={() => setActiveIdx(activeIdx === idx ? null : idx)}
                />
              ))}
            </div>

            {/* Y-axis right label */}
            <div style={{ minWidth: '4rem' }}>
              <AxisLabel text={axes?.x?.high ?? 'Premium'} className="[writing-mode:vertical-rl]" />
            </div>
          </div>

          {/* X-axis bottom label */}
          <div className="flex justify-center mt-1">
            <AxisLabel text={axes?.y?.low ?? 'Self-Serve'} />
          </div>

          {/* Legend */}
          <div className="flex flex-wrap gap-2 mt-3 justify-center">
            {profiles.map((p, idx) => (
              <button
                key={idx}
                onClick={() => setActiveIdx(activeIdx === idx ? null : idx)}
                className={`flex items-center gap-1.5 text-xs px-2 py-1 rounded-full border transition
                  ${activeIdx === idx ? 'bg-slate-100 border-slate-400' : 'border-slate-200 hover:bg-slate-50'}`}
              >
                <span className="w-2.5 h-2.5 rounded-full shrink-0"
                      style={{ background: COLORS[idx % COLORS.length].dot }} />
                {p.title.length > 20 ? p.title.slice(0, 19) + '…' : p.title}
              </button>
            ))}
          </div>
        </div>

        {/* Detail panel */}
        <div className="space-y-3">
          {activeProfile
            ? <ProfileDetail profile={activeProfile} color={activeColor} />
            : (
              <div className="space-y-2">
                <p className="text-xs text-slate-500 font-medium mb-2">Axis leaders</p>
                {axis_leaders && Object.entries({
                  'Most Premium':      axis_leaders.most_premium,
                  'Cost-Leader':       axis_leaders.most_cost_leader,
                  'Most Sales-Led':    axis_leaders.most_sales_led,
                  'Most Self-Serve':   axis_leaders.most_self_serve,
                  'Most Outcome':      axis_leaders.most_outcome,
                  'Most Feature-Rich': axis_leaders.most_feature_rich,
                }).map(([label, name]) => name && (
                  <div key={label} className="flex justify-between text-xs py-1 border-b border-slate-100">
                    <span className="text-slate-500">{label}</span>
                    <span className="font-semibold text-slate-700 text-right max-w-[55%] truncate">{name}</span>
                  </div>
                ))}
                <p className="text-[11px] text-slate-400 pt-1">Click a dot or name to see details.</p>
              </div>
            )
          }
        </div>
      </div>
      <OverusedAnglesPanel angles={overused_angles} />
    </section>
  );
}
