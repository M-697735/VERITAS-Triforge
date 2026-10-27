import React, { useState } from 'react';
import { FileDown, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';
import { downloadPdfReport } from '../api/client';

export default function PdfDownloadButton({ analysisData }) {
  const [downloading, setDownloading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState(null);

  const handleDownload = async () => {
    if (!analysisData) return;
    setDownloading(true);
    setSuccess(false);
    setError(null);

    try {
      await downloadPdfReport(analysisData);
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      console.error("PDF Download failed:", err);
      let msg = "Failed to generate PDF";
      if (err.response?.status === 404) {
        msg = "Analysis expired, re-run it";
      } else if (err.response?.data?.detail) {
        msg = err.response.data.detail;
      } else if (err.message) {
        msg = err.message;
      }
      setError(msg);
      setTimeout(() => setError(null), 4000);
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="flex flex-col items-end">
      <button
        onClick={handleDownload}
        disabled={downloading || !analysisData}
        className={`flex items-center space-x-2 px-5 py-2.5 rounded-xl font-bold text-xs shadow-lg transition-all ${
          error
            ? 'bg-rose-950 text-rose-300 border border-rose-500/50'
            : success
            ? 'bg-emerald-500 text-slate-950 shadow-emerald-500/20'
            : 'bg-cyan-500 hover:bg-cyan-400 text-slate-950 shadow-cyan-500/20 hover:scale-[1.02]'
        } disabled:opacity-50 disabled:cursor-not-allowed`}
      >
        {downloading ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>Generating Report...</span>
          </>
        ) : error ? (
          <>
            <AlertCircle className="w-4 h-4 text-rose-400" />
            <span>{error}</span>
          </>
        ) : success ? (
          <>
            <CheckCircle2 className="w-4 h-4" />
            <span>PDF Downloaded!</span>
          </>
        ) : (
          <>
            <FileDown className="w-4 h-4" />
            <span>Generate Forensic Report (PDF)</span>
          </>
        )}
      </button>
    </div>
  );
}
