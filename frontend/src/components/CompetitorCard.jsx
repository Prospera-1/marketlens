import { useState } from 'react';
import { ExternalLink, Star, MessageSquare, Globe, ChevronDown, ChevronUp } from 'lucide-react';

function ReviewBadge({ platform, data }) {
  if (!data) return null;

  const score = platform === 'g2' ? data.rating : data.trust_score;
  const count = data.review_count;
  const label = platform === 'g2' ? 'G2' : 'Trustpilot';
  const color = platform === 'g2' ? 'bg-orange-50 text-orange-700 border-orange-200'
                                  : 'bg-green-50 text-green-700 border-green-200';

  if (!score && !count) return null;

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-semibold border ${color}`}>
      <Star className="w-3 h-3 fill-current" />
      {label} {score ? `${score}/5` : ''} {count ? `· ${count.toLocaleString()} reviews` : ''}
    </span>
  );
}

export default function CompetitorCard({ comp }) {
  const reviews = comp.reviews || {};
  const pagesCrawled = comp.pages_crawled || [];
  const [showPages, setShowPages] = useState(false);

  return (
    <div className="border border-slate-200 rounded-xl p-5 space-y-4 bg-white">

      {/* Header */}
      <div>
        <h3 className="font-bold text-lg leading-tight">{comp.title || comp.url}</h3>
        <div className="flex items-center gap-3 mt-0.5 flex-wrap">
          <a href={comp.url} target="_blank" rel="noreferrer"
             className="text-sm text-blue-600 hover:underline inline-flex items-center gap-1">
            <ExternalLink className="w-3 h-3" /> Visit Site
          </a>
          {pagesCrawled.length > 0 && (
            <button
              onClick={() => setShowPages(s => !s)}
              className="inline-flex items-center gap-1 text-xs text-slate-500 hover:text-slate-700 transition"
              title="Pages analysed in this snapshot"
            >
              <Globe className="w-3 h-3" />
              {pagesCrawled.length} page{pagesCrawled.length !== 1 ? 's' : ''} crawled
              {showPages ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            </button>
          )}
        </div>

        {/* Crawled pages list (expandable) */}
        {showPages && pagesCrawled.length > 0 && (
          <ul className="mt-2 space-y-0.5">
            {pagesCrawled.map((url, i) => (
              <li key={i}>
                <a href={url} target="_blank" rel="noreferrer"
                   className="text-xs text-slate-400 hover:text-blue-500 truncate block">
                  {url}
                </a>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Review badges */}
      {(reviews.g2 || reviews.trustpilot) && (
        <div className="flex flex-wrap gap-2">
          <ReviewBadge platform="g2" data={reviews.g2} />
          <ReviewBadge platform="trustpilot" data={reviews.trustpilot} />
        </div>
      )}

      {/* Positioning / meta description */}
      {comp.meta_description && (
        <div>
          <h4 className="text-xs uppercase tracking-wider text-slate-400 font-semibold mb-1">Positioning</h4>
          <p className="text-sm text-slate-600 italic leading-relaxed">"{comp.meta_description}"</p>
        </div>
      )}

      {/* Hero text */}
      {comp.hero_text?.length > 0 && (
        <div>
          <h4 className="text-xs uppercase tracking-wider text-slate-400 font-semibold mb-1">Above the Fold</h4>
          <p className="text-sm font-medium text-slate-800">{comp.hero_text[0]}</p>
        </div>
      )}

      {/* CTAs */}
      {comp.ctas?.length > 0 && (
        <div>
          <h4 className="text-xs uppercase tracking-wider text-slate-400 font-semibold mb-2">Calls to Action</h4>
          <div className="flex flex-wrap gap-1.5">
            {comp.ctas.slice(0, 5).map((cta, i) => (
              <span key={i} className="px-2 py-1 bg-blue-50 text-blue-700 border border-blue-200 rounded text-xs font-medium">
                {cta}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Pricing */}
      {comp.pricing?.length > 0 && (
        <div>
          <h4 className="text-xs uppercase tracking-wider text-slate-400 font-semibold mb-2">Pricing</h4>
          <ul className="list-disc pl-4 text-sm space-y-1 text-slate-700">
            {comp.pricing.slice(0, 4).map((p, i) => <li key={i}>{p}</li>)}
          </ul>
        </div>
      )}

      {/* Features */}
      {comp.features?.length > 0 && (
        <div>
          <h4 className="text-xs uppercase tracking-wider text-slate-400 font-semibold mb-2">Key Features</h4>
          <ul className="list-disc pl-4 text-sm space-y-1 text-slate-700">
            {comp.features.slice(0, 4).map((f, i) => <li key={i}>{f}</li>)}
          </ul>
        </div>
      )}

      {/* G2 Pros/Cons */}
      {reviews.g2?.pros?.length > 0 && (
        <div>
          <h4 className="text-xs uppercase tracking-wider text-slate-400 font-semibold mb-2 flex items-center gap-1">
            <MessageSquare className="w-3 h-3" /> Customer Feedback (G2)
          </h4>
          <div className="space-y-1">
            {reviews.g2.pros.slice(0, 2).map((pro, i) => (
              <p key={i} className="text-xs text-emerald-700 bg-emerald-50 rounded px-2 py-1">+ {pro}</p>
            ))}
            {reviews.g2.cons?.slice(0, 2).map((con, i) => (
              <p key={i} className="text-xs text-rose-700 bg-rose-50 rounded px-2 py-1">− {con}</p>
            ))}
          </div>
        </div>
      )}

      {/* Testimonials */}
      {comp.testimonials?.length > 0 && (
        <div>
          <h4 className="text-xs uppercase tracking-wider text-slate-400 font-semibold mb-2">Testimonial</h4>
          <blockquote className="text-sm text-slate-600 italic border-l-2 border-slate-300 pl-3 leading-relaxed">
            "{comp.testimonials[0].slice(0, 200)}{comp.testimonials[0].length > 200 ? '…' : ''}"
          </blockquote>
        </div>
      )}
    </div>
  );
}
