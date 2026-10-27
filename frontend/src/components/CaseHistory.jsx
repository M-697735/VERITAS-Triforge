import React, { useEffect, useState } from 'react';
import { History, ShieldAlert, CheckCircle2, AlertTriangle, Clock, FileText, ArrowRight, Trash2, Loader2 } from 'lucide-react';
import { fetchHistory, fetchCaseDetail, deleteCase, clearHistory } from '../api/client';

export default function CaseHistory({ onSelectCase, onHistoryUpdated }) {
  const [historyItems, setHistoryItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState(null);
  const [clearing, setClearing] = useState(false);
  const [loadingCaseId, setLoadingCaseId] = useState(null);

  const loadHistory = async () => {
    setLoading(true);
    try {
      const data = await fetchHistory();
      setHistoryItems(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error("Failed to load history:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadHistory();
  }, []);

  const handleCardClick = async (item) => {
    const caseId = item.case_id || item.id;
    if (loadingCaseId) return;
    setLoadingCaseId(caseId);

    try {
      const fullAnalysis = await fetchCaseDetail(caseId);
      fullAnalysis.saved = true;
      if (onSelectCase) {
        onSelectCase(fullAnalysis);
      }
    } catch (err) {
      console.error("Failed to fetch case detail:", err);
      alert(err.response?.data?.detail || "Failed to load case analysis.");
    } finally {
      setLoadingCaseId(null);
    }
  };

  const handleDeleteCase = async (e, caseId) => {
    e.stopPropagation();
    if (!window.confirm(`Are you sure you want to delete ${caseId} from saved history?`)) {
      return;
    }

    setDeletingId(caseId);
    try {
      await deleteCase(caseId);
      await loadHistory();
      if (onHistoryUpdated) onHistoryUpdated();
    } catch (err) {
      console.error("Failed to delete case:", err);
      alert(err.response?.data?.detail || "Failed to delete case");
    } finally {
      setDeletingId(null);
    }
  };

  const handleClearAll = async () => {
    if (!window.confirm("Are you sure you want to permanently clear all saved cases?")) {
      return;
    }

    setClearing(true);
    try {
      await clearHistory();
      await loadHistory();
      if (onHistoryUpdated) onHistoryUpdated();
    } catch (err) {
      console.error("Failed to clear history:", err);
      alert(err.response?.data?.detail || "Failed to clear history");
    } finally {
      setClearing(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6 py-6">
      
      <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-slate-800 pb-4 gap-4">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
            <History className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white">Saved Forensic Case History</h2>
            <p className="text-xs text-slate-400">Permanently saved case records across sessions and restarts</p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          {historyItems.length > 0 && (
            <button
              onClick={handleClearAll}
              disabled={clearing}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-rose-400 bg-rose-950/60 border border-rose-800/60 hover:bg-rose-900/60 transition-all disabled:opacity-50"
            >
              {clearing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Trash2 className="w-3.5 h-3.5" />}
              <span>{clearing ? "Clearing..." : "Clear all saved cases"}</span>
            </button>
          )}

          <span className="text-xs font-mono font-bold px-3 py-1.5 rounded bg-slate-900 border border-slate-800 text-cyan-400">
            {historyItems.length} Saved Cases
          </span>
        </div>
      </div>

      {loading ? (
        <div className="p-12 text-center text-slate-400 font-mono text-xs">
          Loading saved case history...
        </div>
      ) : historyItems.length === 0 ? (
        <div className="bg-[#111827] border border-slate-800 rounded-2xl p-12 text-center space-y-3">
          <FileText className="w-10 h-10 text-slate-600 mx-auto" />
          <p className="text-sm font-semibold text-slate-300">No Saved Cases Yet</p>
          <p className="text-xs text-slate-500">
            Run an email analysis and click <span className="text-cyan-400 font-semibold">"Save to Case History"</span> to permanently store it here.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {historyItems.map((item) => {
            const isFraud = item.verdict === 'Likely Fraudulent';
            const isReview = item.verdict === 'Needs Review';
            const caseId = item.case_id || item.id;
            const isLoadingThis = loadingCaseId === caseId;
            
            return (
              <div
                key={caseId}
                onClick={() => handleCardClick(item)}
                className="group bg-[#111827] border border-slate-800 hover:border-cyan-500/50 hover:bg-slate-850 rounded-xl p-4 transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-4 cursor-pointer shadow-lg hover:shadow-cyan-500/5"
              >
                <div className="space-y-1.5 flex-1">
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-mono font-bold text-cyan-400 group-hover:text-cyan-300">
                      {caseId}
                    </span>
                    <span className="text-slate-600">•</span>
                    <span className="text-xs text-slate-400 font-mono flex items-center space-x-1">
                      <Clock className="w-3 h-3 text-slate-500" />
                      <span>{item.timestamp ? new Date(item.timestamp).toLocaleString() : 'N/A'}</span>
                    </span>
                    <span className="text-slate-600">•</span>
                    <span className="text-[10px] font-mono text-slate-500 truncate max-w-[150px]">
                      {item.filename}
                    </span>
                  </div>

                  <h3 className="text-sm font-bold text-white group-hover:text-cyan-200 line-clamp-1 transition-colors">
                    {item.subject}
                  </h3>

                  <p className="text-xs text-slate-400 font-mono line-clamp-1">
                    From: {item.from_address}
                  </p>
                </div>

                <div className="flex items-center space-x-4">
                  <div className="text-right">
                    <span className={`inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-mono font-bold ${
                      isFraud ? 'bg-rose-950 text-rose-400 border border-rose-800' :
                      isReview ? 'bg-amber-950 text-amber-400 border border-amber-800' : 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                    }`}>
                      <span>{(item.verdict || 'Needs Review').toUpperCase()}</span>
                    </span>

                    <p className="text-[10px] text-slate-400 font-mono mt-1">
                      {item.contradictions_count} Contradictions
                    </p>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center space-x-1 border-l border-slate-800 pl-3">
                    <button
                      type="button"
                      onClick={(e) => handleDeleteCase(e, caseId)}
                      disabled={deletingId === caseId}
                      title={`Delete ${caseId}`}
                      className="p-2 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-950/40 border border-transparent hover:border-rose-900/40 transition-all disabled:opacity-50"
                    >
                      {deletingId === caseId ? (
                        <Loader2 className="w-4 h-4 animate-spin text-rose-400" />
                      ) : (
                        <Trash2 className="w-4 h-4" />
                      )}
                    </button>

                    <div className="p-1 text-slate-600 group-hover:text-cyan-400 transition-colors">
                      {isLoadingThis ? (
                        <Loader2 className="w-4 h-4 animate-spin text-cyan-400" />
                      ) : (
                        <ArrowRight className="w-4 h-4" />
                      )}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

    </div>
  );
}
