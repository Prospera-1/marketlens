import { Activity } from 'lucide-react';

const CATEGORY_COLORS = {
  'Pricing':       'bg-amber-100 text-amber-800',
  'Messaging':     'bg-purple-100 text-purple-800',
  'CTAs':          'bg-blue-100 text-blue-800',
  'Hero Content':  'bg-indigo-100 text-indigo-800',
  'Positioning':   'bg-pink-100 text-pink-800',
  'Features':      'bg-teal-100 text-teal-800',
  'Social Proof':  'bg-emerald-100 text-emerald-800',
  'G2 Rating':     'bg-orange-100 text-orange-800',
  'Trustpilot Score': 'bg-green-100 text-green-800',
};

export default function DiffPanel({ changes }) {
  return (
    <section className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
      <div className="flex items-center mb-6">
        <Activity className="w-6 h-6 text-purple-600 mr-3" />
        <h2 className="text-xl font-bold">Recent Changes Detected</h2>
      </div>

      {changes.length === 0 ? (
        <p className="text-slate-500 text-sm">No changes detected since the last snapshot.</p>
      ) : (
        <div className="space-y-4">
          {changes.map((change, idx) => {
            const colorClass = CATEGORY_COLORS[change.category] || 'bg-slate-100 text-slate-700';
            return (
              <div key={idx} className="p-4 rounded-lg border border-slate-100 bg-slate-50">
                <div className="flex justify-between items-start mb-2">
                  <span className="font-medium text-slate-900">{change.brand || 'Unknown'}</span>
                  <span className={`text-xs px-2 py-1 rounded-full font-medium ${colorClass}`}>
                    {change.category || change.type}
                  </span>
                </div>
                <p className="text-sm text-slate-600 mb-3">{change.description}</p>

                {change.added?.length > 0 && (
                  <div className="text-sm text-emerald-700 bg-emerald-50 p-2 rounded border border-emerald-100">
                    <strong>+ Added:</strong> {change.added.join(' · ')}
                  </div>
                )}
                {change.removed?.length > 0 && (
                  <div className="mt-1 text-sm text-rose-700 bg-rose-50 p-2 rounded border border-rose-100">
                    <strong>− Removed:</strong> {change.removed.join(' · ')}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
