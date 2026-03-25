/**
 * ExportButton.jsx — Download the full intelligence report.
 *
 * Provides two format options:
 *   - JSON  : complete machine-readable report
 *   - CSV   : flat spreadsheet-friendly version
 *
 * Triggers a direct browser download via the /api/export endpoint.
 */

import { useState } from 'react';
import { Download, ChevronDown } from 'lucide-react';

const API_BASE = "http://localhost:8000/api";

export default function ExportButton() {
  const [open, setOpen] = useState(false);
  const [downloading, setDownloading] = useState(false);

  const download = async (format) => {
    setOpen(false);
    setDownloading(true);
    try {
      const res   = await fetch(`${API_BASE}/export?format=${format}`);
      const blob  = await res.blob();
      const url   = URL.createObjectURL(blob);
      const a     = document.createElement('a');
      a.href      = url;
      a.download  = `market_intelligence_report.${format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error('Export failed', e);
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(v => !v)}
        disabled={downloading}
        className="flex items-center gap-2 px-4 py-2 rounded-lg border border-slate-200 bg-white text-slate-700 text-sm font-medium hover:bg-slate-50 transition shadow-xs disabled:opacity-60"
      >
        <Download className={`w-4 h-4 ${downloading ? 'animate-bounce' : ''}`} />
        {downloading ? 'Exporting…' : 'Export'}
        <ChevronDown className={`w-3 h-3 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-1 w-40 bg-white border border-slate-200 rounded-lg shadow-lg z-50 overflow-hidden">
          <button
            onClick={() => download('json')}
            className="w-full text-left px-4 py-2.5 text-sm text-slate-700 hover:bg-slate-50 transition flex items-center gap-2"
          >
            <span className="text-xs font-bold text-slate-400 w-8">JSON</span>
            Full report
          </button>
          <button
            onClick={() => download('csv')}
            className="w-full text-left px-4 py-2.5 text-sm text-slate-700 hover:bg-slate-50 transition flex items-center gap-2 border-t border-slate-100"
          >
            <span className="text-xs font-bold text-slate-400 w-8">CSV</span>
            Spreadsheet
          </button>
        </div>
      )}
    </div>
  );
}
