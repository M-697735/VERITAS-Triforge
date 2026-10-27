import React from 'react';
import { ShieldAlert, AlertTriangle, CheckCircle2, Hash, Layers } from 'lucide-react';

export default function VerdictBanner({ verdict, sha256Hash, emailMeta }) {
  if (!verdict) return null;

  const { verdict: label, confidence, driving_rule_ids = [], summary } = verdict;

  const isFraud = label === 'Likely Fraudulent';
  const isReview = label === 'Needs Review';
  const isLegit = label === 'Likely Legitimate';

  const bannerTheme = isFraud
    ? {
        bg: 'bg-rose-950/40 border-rose-500/40',
        glow: 'glow-rose',
        badge: 'bg-rose-500 text-slate-950',
        icon: <ShieldAlert className="w-8 h-8 text-rose-400" />,
        accentText: 'text-rose-400'
      }
    : isReview
    ? {
        bg: 'bg-amber-950/40 border-amber-500/40',
        glow: 'glow-amber',
        badge: 'bg-amber-500 text-slate-950',
        icon: <AlertTriangle className="w-8 h-8 text-amber-400" />,
        accentText: 'text-amber-400'
      }
    : {
        bg: 'bg-emerald-950/40 border-emerald-500/40',
        glow: 'glow-emerald',
        badge: 'bg-emerald-500 text-slate-950',
        icon: <CheckCircle2 className="w-8 h-8 text-emerald-400" />,
        accentText: 'text-emerald-400'
      };

  return (
    <div className={`border rounded-2xl p-6 backdrop-blur-md transition-all ${bannerTheme.bg} ${bannerTheme.glow}`}>
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
        
        {/* Left: Status Icon & Title */}
        <div className="flex items-start space-x-4">
          <div className="p-3 rounded-2xl bg-slate-900/80 border border-slate-800 shadow-lg">
            {bannerTheme.icon}
          </div>

          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className={`px-3 py-1 rounded-lg font-extrabold text-sm uppercase tracking-wider ${bannerTheme.badge}`}>
                {label}
              </span>
              <span className="text-xs font-mono font-semibold px-2.5 py-1 rounded bg-slate-900 border border-slate-800 text-slate-300">
                Confidence: <span className={bannerTheme.accentText}>{confidence}</span>
              </span>
            </div>

            <h2 className="text-lg font-bold text-white line-clamp-1 pt-1">
              Subject: {emailMeta?.subject || '(No Subject)'}
            </h2>
            <p className="text-xs text-slate-300 max-w-3xl leading-relaxed">
              {summary}
            </p>
          </div>
        </div>

        {/* Right: Driving Rules & SHA-256 */}
        <div className="flex flex-col sm:flex-row lg:flex-col items-start lg:items-end justify-between gap-3 border-t lg:border-t-0 border-slate-800/80 pt-4 lg:pt-0">
          
          {/* Driving Rules List */}
          <div className="flex items-center space-x-2">
            <span className="text-xs font-medium text-slate-400 flex items-center space-x-1">
              <Layers className="w-3.5 h-3.5 text-cyan-400" />
              <span>Driving Rules:</span>
            </span>
            <div className="flex flex-wrap gap-1">
              {driving_rule_ids.length > 0 ? (
                driving_rule_ids.map((id) => (
                  <span key={id} className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-slate-900 border border-slate-700 text-cyan-400">
                    {id}
                  </span>
                ))
              ) : (
                <span className="text-xs font-mono text-emerald-400 px-2 py-0.5 rounded bg-emerald-950 border border-emerald-800">
                  None (0 Hits)
                </span>
              )}
            </div>
          </div>

          {/* SHA-256 Hash */}
          <div className="flex items-center space-x-1.5 text-[11px] font-mono text-slate-400 bg-slate-900/90 px-3 py-1.5 rounded-lg border border-slate-800">
            <Hash className="w-3.5 h-3.5 text-cyan-500" />
            <span className="text-slate-500">SHA-256:</span>
            <span className="text-slate-300 font-bold tracking-wider">
              {sha256Hash ? `${sha256Hash.substring(0, 16)}...` : 'N/A'}
            </span>
          </div>

        </div>

      </div>
    </div>
  );
}
