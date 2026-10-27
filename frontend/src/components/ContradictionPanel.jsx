import React from 'react';
import { AlertCircle, Layers, ShieldCheck, ArrowRightLeft } from 'lucide-react';

export default function ContradictionPanel({ contradictions = [] }) {
  return (
    <div className="bg-[#111827] border border-slate-800 rounded-2xl p-6 space-y-5 shadow-xl">
      
      {/* Panel Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div className="flex items-center space-x-3">
          <div className="w-9 h-9 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-center justify-center text-rose-400">
            <AlertCircle className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-bold text-white flex items-center space-x-2">
              <span>Cross-Layer Contradictions Panel</span>
              <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-rose-950 text-rose-400 border border-rose-800">
                {contradictions.length} Detected
              </span>
            </h3>
            <p className="text-xs text-slate-400">
              Evaluates evidence mismatches between independent analysis layers (Core Engine Differentiator)
            </p>
          </div>
        </div>
      </div>

      {/* Contradictions List */}
      {contradictions.length === 0 ? (
        <div className="bg-emerald-950/20 border border-emerald-500/30 rounded-xl p-6 text-center space-y-2">
          <div className="w-10 h-10 rounded-full bg-emerald-500/10 text-emerald-400 flex items-center justify-center mx-auto">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <p className="text-sm font-semibold text-emerald-300">
            Zero Cross-Layer Contradictions Detected
          </p>
          <p className="text-xs text-slate-400 max-w-lg mx-auto">
            All 5 independent evidence layers (Claimed Identity, Technical Authentication, Content Intent, Infrastructure, and Historical Pattern) corroborate each other without contradiction.
          </p>
        </div>
      ) : (
        <div className="space-y-3.5">
          {contradictions.map((c, idx) => (
            <div
              key={idx}
              className="bg-rose-950/20 border border-rose-500/40 hover:border-rose-500/70 rounded-xl p-4 transition-all space-y-3"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center space-x-2.5">
                  <span className="font-mono text-xs font-extrabold px-2.5 py-1 rounded bg-rose-500 text-slate-950 shadow">
                    RULE {c.rule_id}
                  </span>
                  <h4 className="text-sm font-bold text-white">
                    {c.title}
                  </h4>
                </div>

                <span className={`text-[10px] font-mono font-bold uppercase px-2 py-0.5 rounded ${
                  c.severity === 'HIGH' ? 'bg-rose-900 text-rose-300 border border-rose-700' : 'bg-amber-900 text-amber-300 border border-amber-700'
                }`}>
                  {c.severity} SEVERITY
                </span>
              </div>

              {/* Description */}
              <p className="text-xs text-slate-200 leading-relaxed font-medium bg-slate-900/60 p-3 rounded-lg border border-slate-800/80">
                "{c.description}"
              </p>

              {/* Layers Compared */}
              <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1">
                <div className="flex items-center space-x-2 font-mono">
                  <Layers className="w-3.5 h-3.5 text-cyan-400" />
                  <span>Layers Compared:</span>
                  <div className="flex items-center space-x-1.5 text-cyan-300 font-semibold">
                    {c.layers_compared.map((l, lIdx) => (
                      <React.Fragment key={lIdx}>
                        <span>{l}</span>
                        {lIdx < c.layers_compared.length - 1 && (
                          <ArrowRightLeft className="w-3 h-3 text-slate-500 mx-1" />
                        )}
                      </React.Fragment>
                    ))}
                  </div>
                </div>
              </div>

            </div>
          ))}
        </div>
      )}

    </div>
  );
}
