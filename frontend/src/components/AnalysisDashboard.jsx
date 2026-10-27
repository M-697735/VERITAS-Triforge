import React, { useState, useEffect } from 'react';
import VerdictBanner from './VerdictBanner';
import ContradictionPanel from './ContradictionPanel';
import LayerGrid from './LayerGrid';
import GeoLocationMap from './GeoLocationMap';
import CaseNetworkGraph from './CaseNetworkGraph';
import PdfDownloadButton from './PdfDownloadButton';
import { ArrowLeft, Bookmark, Check, Loader2, Link2, Paperclip, AlertTriangle, UserCheck, ShieldAlert } from 'lucide-react';
import { saveCase } from '../api/client';

export default function AnalysisDashboard({ analysisData, onNewAnalysis, onCaseSaved }) {
  if (!analysisData) return null;

  const { sha256_hash, email_meta, layer1, layer2, layer3, layer4, layer5, contradictions, verdict } = analysisData;

  const isSavedInitial = Boolean(analysisData?.saved || analysisData?.case_id?.startsWith('CASE-'));
  const [saved, setSaved] = useState(isSavedInitial);
  const [saving, setSaving] = useState(false);
  const [saveNotice, setSaveNotice] = useState(null);

  const defaultLabel = verdict?.verdict === 'Likely Fraudulent' 
    ? 'Confirmed fraud' 
    : verdict?.verdict === 'Needs Review' 
    ? 'Suspicious' 
    : 'Cleared';

  const [selectedLabel, setSelectedLabel] = useState(analysisData?.analyst_label || defaultLabel);

  useEffect(() => {
    setSaved(Boolean(analysisData?.saved || analysisData?.case_id?.startsWith('CASE-')));
    if (analysisData?.analyst_label) {
      setSelectedLabel(analysisData.analyst_label);
    }
  }, [analysisData?.case_id, analysisData?.saved, analysisData?.analyst_label]);

  const handleSave = async () => {
    if (!analysisData || saving || saved) return;
    setSaving(true);
    setSaveNotice(null);

    try {
      const res = await saveCase(analysisData.case_id, selectedLabel);
      setSaved(true);
      analysisData.case_id = res.case_id;
      analysisData.saved = true;
      analysisData.analyst_label = selectedLabel;

      if (res.duplicate) {
        setSaveNotice(`Already saved as ${res.case_id}`);
      } else {
        setSaveNotice(`Saved as ${res.case_id} (${selectedLabel})`);
      }

      if (onCaseSaved) {
        onCaseSaved(res.analysis || analysisData);
      }
      setTimeout(() => setSaveNotice(null), 4000);
    } catch (err) {
      console.error("Save failed:", err);
      setSaveNotice(err.response?.data?.detail || "Failed to save case");
      setTimeout(() => setSaveNotice(null), 4000);
    } finally {
      setSaving(false);
    }
  };

  const links = layer3?.details?.links || [];
  const attachments = layer3?.details?.attachments || [];

  return (
    <div className="max-w-7xl mx-auto space-y-8 py-6">
      
      {/* Top Action Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <button
          onClick={onNewAnalysis}
          className="inline-flex items-center space-x-2 text-xs font-semibold text-slate-400 hover:text-cyan-400 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Analyze Another Email / Select Preset</span>
        </button>

        <div className="flex flex-wrap items-center gap-3">
          {saveNotice && (
            <span className="text-[11px] font-mono text-cyan-400 bg-cyan-950/80 px-2.5 py-1 rounded border border-cyan-800 animate-fade-in">
              {saveNotice}
            </span>
          )}

          {/* Label Selector & Save Button */}
          <div className="flex items-center rounded-xl bg-slate-900 border border-slate-700/80 p-0.5">
            {!saved ? (
              <select
                value={selectedLabel}
                onChange={(e) => setSelectedLabel(e.target.value)}
                className="bg-transparent text-slate-300 text-xs px-2.5 py-1.5 rounded focus:outline-none cursor-pointer"
              >
                <option value="Confirmed fraud" className="bg-slate-900 text-rose-400">Label: Confirmed fraud</option>
                <option value="Suspicious" className="bg-slate-900 text-amber-400">Label: Suspicious</option>
                <option value="Cleared" className="bg-slate-900 text-emerald-400">Label: Cleared</option>
              </select>
            ) : (
              <span className="text-[11px] font-semibold text-slate-300 px-3 py-1">
                Label: <strong className="text-cyan-300">{selectedLabel}</strong>
              </span>
            )}

            <button
              onClick={handleSave}
              disabled={saved || saving}
              className={`flex items-center space-x-1.5 px-3.5 py-1.5 rounded-lg font-bold text-xs transition-all ${
                saved
                  ? 'bg-slate-800 text-emerald-400 border border-emerald-500/30 cursor-not-allowed opacity-90'
                  : 'bg-cyan-600 hover:bg-cyan-500 text-white shadow-md shadow-cyan-600/20'
              }`}
            >
              {saving ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-white" />
                  <span>Saving...</span>
                </>
              ) : saved ? (
                <>
                  <Check className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Saved ✓</span>
                </>
              ) : (
                <>
                  <Bookmark className="w-3.5 h-3.5" />
                  <span>Save to History</span>
                </>
              )}
            </button>
          </div>

          <PdfDownloadButton analysisData={analysisData} />
        </div>
      </div>

      {/* Forwarded Abuse Report Banner */}
      {analysisData?.is_forwarded_report && (
        <div className="p-4 rounded-xl bg-gradient-to-r from-cyan-950/70 to-blue-950/70 border border-cyan-500/40 text-xs flex items-center justify-between gap-4 shadow-lg shadow-cyan-950/30">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-lg bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
              <UserCheck className="w-5 h-5 text-cyan-400" />
            </div>
            <div>
              <div className="font-bold text-white text-sm flex items-center space-x-2">
                <span>Forwarded Abuse Report Unwrapped</span>
                <span className="px-2 py-0.5 rounded-full bg-cyan-900/60 text-cyan-300 font-mono text-[10px] border border-cyan-700">
                  AUTO-UNWRAPPED
                </span>
              </div>
              <div className="text-cyan-200 mt-0.5">
                Reported by: <strong className="text-white font-mono">{analysisData.reported_by || 'Unknown Reporter'}</strong>
                {analysisData.outer_report_meta?.date && (
                  <span className="text-slate-400 ml-2">
                    (Forwarded on: {analysisData.outer_report_meta.date})
                  </span>
                )}
              </div>
              <p className="text-slate-400 text-[11px] mt-0.5">
                VERITAS isolated the forwarded attachment, extracted the original recipient headers, and evaluated the true originating infrastructure.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* 1. Verdict Banner */}
      <VerdictBanner verdict={verdict} sha256Hash={sha256_hash} emailMeta={email_meta} />

      {/* 2. Contradiction Panel */}
      <ContradictionPanel contradictions={contradictions} />

      {/* 3. 5-Layer Evidence Grid */}
      <LayerGrid layer1={layer1} layer2={layer2} layer3={layer3} layer4={layer4} layer5={layer5} />

      {/* 4. Forensic Links & Safe Attachments Inspector (if present) */}
      {(links.length > 0 || attachments.length > 0) && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Extracted Hyperlinks */}
          <div className="bg-[#111827] border border-slate-800 rounded-xl p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center space-x-2">
                <Link2 className="w-5 h-5 text-cyan-400" />
                <h3 className="text-sm font-bold text-white">Extracted Links Forensics</h3>
              </div>
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                {links.length} Link{links.length !== 1 ? 's' : ''}
              </span>
            </div>

            {links.length === 0 ? (
              <p className="text-xs text-slate-500 italic">No links extracted from email body.</p>
            ) : (
              <div className="space-y-3 max-h-64 overflow-y-auto pr-1">
                {links.map((lnk, idx) => (
                  <div key={idx} className="p-2.5 rounded-lg bg-slate-900/90 border border-slate-800 text-xs space-y-1">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-slate-400 font-medium truncate max-w-[200px]" title={lnk.display_text}>
                        Label: &quot;{lnk.display_text || lnk.display_domain || 'link'}&quot;
                      </span>
                      {lnk.mismatch && (
                        <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-rose-950 text-rose-400 border border-rose-800 shrink-0">
                          Domain Mismatch
                        </span>
                      )}
                    </div>
                    <div className="font-mono text-[11px] text-cyan-300 break-all select-all">
                      Target: {lnk.defanged_destination || lnk.href}
                    </div>
                    {lnk.reasons && lnk.reasons.length > 0 && (
                      <div className="text-[10px] text-rose-400 pt-0.5 flex flex-wrap gap-1">
                        {lnk.reasons.map((r, ridx) => (
                          <span key={ridx} className="bg-rose-950/50 px-1.5 py-0.5 rounded border border-rose-900/60">
                            ⚠ {r}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Safe Attachment Metadata Inspection */}
          <div className="bg-[#111827] border border-slate-800 rounded-xl p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center space-x-2">
                <Paperclip className="w-5 h-5 text-purple-400" />
                <h3 className="text-sm font-bold text-white">Safe Attachment Inspection</h3>
              </div>
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                {attachments.length} File{attachments.length !== 1 ? 's' : ''} (Never Executed)
              </span>
            </div>

            {attachments.length === 0 ? (
              <p className="text-xs text-slate-500 italic">No attachments detected in message.</p>
            ) : (
              <div className="space-y-3 max-h-64 overflow-y-auto pr-1">
                {attachments.map((att, idx) => (
                  <div key={idx} className="p-2.5 rounded-lg bg-slate-900/90 border border-slate-800 text-xs space-y-1">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-mono font-bold text-white truncate max-w-[220px]" title={att.filename}>
                        📎 {att.filename}
                      </span>
                      {att.is_risky ? (
                        <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-rose-950 text-rose-400 border border-rose-800 shrink-0">
                          High Risk
                        </span>
                      ) : (
                        <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 shrink-0">
                          {att.content_type || 'binary'}
                        </span>
                      )}
                    </div>
                    <div className="text-[11px] text-slate-400 flex items-center justify-between">
                      <span>Size: {att.size ? (att.size > 1024 ? `${Math.round(att.size / 1024)} KB` : `${att.size} B`) : 'Unknown'}</span>
                      <span className="font-mono text-[10px] text-slate-500">SHA-256: {att.sha256 ? `${att.sha256.substring(0, 10)}...` : 'N/A'}</span>
                    </div>
                    {att.risk_reason && (
                      <div className="text-[10px] text-rose-400 bg-rose-950/50 p-1 rounded border border-rose-900/60">
                        ⚠ {att.risk_reason}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* 5. Infrastructure & Network Graphs Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <GeoLocationMap layer4={layer4} />
        <CaseNetworkGraph layer5={layer5} />
      </div>

    </div>
  );
}

