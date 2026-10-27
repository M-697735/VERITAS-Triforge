import React, { useState, useEffect } from 'react';
import { Upload, FileCode, Play, Sparkles, CheckCircle2, ShieldAlert, AlertTriangle, Lock, RefreshCw } from 'lucide-react';
import { fetchSamples, fetchSampleContent } from '../api/client';

export default function EmlUploader({ onAnalyze, isLoading, isOnline = true }) {
  const [activeTab, setActiveTab] = useState('upload'); // 'upload' | 'paste'
  const [dragActive, setDragActive] = useState(false);
  const [rawText, setRawText] = useState('');
  const [samples, setSamples] = useState([]);

  useEffect(() => {
    fetchSamples().then(setSamples).catch(err => console.error("Failed to fetch samples:", err));
  }, []);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!isOnline) return;
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (!isOnline) return;
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      onAnalyze(e.dataTransfer.files[0], false, false);
    }
  };

  const handleFileChange = (e) => {
    if (!isOnline) return;
    if (e.target.files && e.target.files[0]) {
      onAnalyze(e.target.files[0], false, false);
    }
  };

  const handleSampleClick = async (sample) => {
    if (!isOnline) return;
    try {
      const data = await fetchSampleContent(sample.id);
      const file = new File([data.raw_eml], sample.filename || `${sample.id}.eml`, {
        type: 'message/rfc822'
      });
      onAnalyze(file, false, false);
    } catch (err) {
      console.error("Failed to load sample content:", err);
    }
  };

  const handlePasteSubmit = (e) => {
    e.preventDefault();
    if (!isOnline) return;
    if (rawText.trim()) {
      onAnalyze(rawText, true, false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8 py-6">
      
      {/* Hero Intro Header */}
      <div className="text-center space-y-3">
        <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-cyan-950/70 border border-cyan-500/30 text-cyan-400 text-xs font-mono">
          <Sparkles className="w-3.5 h-3.5" />
          <span>Cross-Layer Contradiction Engine</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
          Submit Raw Email for <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-500">Forensic Evaluation</span>
        </h1>
        <p className="text-sm text-slate-400 max-w-2xl mx-auto">
          VERITAS evaluates submitted emails across 5 independent evidence layers and surfaces explicit cross-layer contradictions rather than relying on a single isolated fraud score.
        </p>
      </div>

      {/* Quick Demo Preset Selector */}
      <div className="bg-[#111827] border border-slate-800 rounded-2xl p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2 text-sm font-semibold text-slate-200">
            <Play className="w-4 h-4 text-cyan-400 fill-cyan-400" />
            <span>1-Click Hackathon Presets (Instant Demo)</span>
          </div>
          <span className="text-xs text-slate-400 font-mono">5 Bundled Samples</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-2.5">
          {samples.map((s, idx) => (
            <button
              key={s.id}
              disabled={!isOnline || isLoading}
              onClick={() => handleSampleClick(s)}
              className="group text-left p-3 rounded-xl bg-slate-900/90 border border-slate-800 hover:border-cyan-500/50 hover:bg-slate-850 transition-all flex flex-col justify-between space-y-2 relative overflow-hidden disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <div className="flex items-start justify-between">
                <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800">
                  SAMPLE #{idx + 1}
                </span>
                <span className={`text-[9px] font-mono font-bold px-1.5 py-0.5 rounded ${
                  s.expected_verdict === 'Likely Legitimate' ? 'bg-emerald-950 text-emerald-400' :
                  s.expected_verdict === 'Needs Review' ? 'bg-amber-950 text-amber-400' : 'bg-rose-950 text-rose-400'
                }`}>
                  {s.expected_rule_ids.length > 0 ? `${s.expected_rule_ids.length} Rules` : '0 Rules'}
                </span>
              </div>
              <div>
                <p className="text-xs font-semibold text-slate-200 group-hover:text-cyan-300 line-clamp-1">
                  {s.name.split(':')[1]?.trim() || s.name}
                </p>
                <p className="text-[10px] text-slate-400 line-clamp-2 mt-0.5">
                  {s.description}
                </p>
              </div>
            </button>
          ))}
        </div>
      </div>

      {!isOnline && (
        <div className="p-3 bg-amber-950/60 border border-amber-500/40 rounded-xl text-amber-300 text-xs text-center font-mono">
          Engine status: OFFLINE / CONNECTING. Sample presets and analysis are temporarily disabled.
        </div>
      )}

      {/* Main Upload / Paste Card */}
      <div className="bg-[#111827] border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
        
        {/* Card Tab Header */}
        <div className="flex items-center justify-between border-b border-slate-800 px-6 py-3 bg-slate-900/50">
          <div className="flex space-x-2">
            <button
              onClick={() => setActiveTab('upload')}
              className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
                activeTab === 'upload'
                  ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Upload className="w-3.5 h-3.5" />
              <span>Upload .EML File</span>
            </button>

            <button
              onClick={() => setActiveTab('paste')}
              className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
                activeTab === 'paste'
                  ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <FileCode className="w-3.5 h-3.5" />
              <span>Paste Raw Content</span>
            </button>
          </div>

          {/* Secondary Live DNS Toggle (strictly disabled in offline demo) */}
          <div
            className="flex items-center space-x-2 text-xs text-slate-500 cursor-not-allowed select-none"
            title="Offline mode -- all data resolved from bundled JSON registries"
          >
            <input
              type="checkbox"
              checked={false}
              disabled
              className="rounded bg-slate-900 border-slate-700 text-slate-600 cursor-not-allowed w-3.5 h-3.5"
            />
            <span>Offline Mode (Live DNS Disabled)</span>
          </div>
        </div>

        {/* Tab Body */}
        <div className="p-6">
          {activeTab === 'upload' ? (
            <div
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              className={`border-2 border-dashed rounded-xl p-10 text-center transition-all ${
                dragActive
                  ? 'border-cyan-500 bg-cyan-500/5'
                  : 'border-slate-700/80 hover:border-slate-600 bg-slate-900/40'
              }`}
            >
              <input
                type="file"
                accept=".eml,text/plain"
                onChange={handleFileChange}
                disabled={!isOnline || isLoading}
                id="eml-file-input"
                className="hidden"
              />
              <label htmlFor={isOnline && !isLoading ? "eml-file-input" : undefined} className={`space-y-4 inline-block ${!isOnline || isLoading ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'}`}>
                <div className="w-16 h-16 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center mx-auto text-cyan-400 group-hover:scale-105 transition-transform shadow-lg shadow-cyan-500/10">
                  <Upload className="w-8 h-8" />
                </div>
                <div>
                  <p className="text-base font-semibold text-slate-200">
                    Drag and drop your raw <span className="text-cyan-400">.eml</span> file here
                  </p>
                  <p className="text-xs text-slate-400 mt-1">
                    Supports RFC 822 email format from Outlook, Thunderbird, Apple Mail, or Gmail export
                  </p>
                </div>
                <button
                  type="button"
                  disabled={!isOnline || isLoading}
                  onClick={() => {
                    if (isOnline && !isLoading) {
                      document.getElementById('eml-file-input')?.click();
                    }
                  }}
                  className="px-5 py-2.5 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-xs shadow-lg shadow-cyan-500/25 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isLoading ? 'Processing Forensics...' : 'Browse Local File'}
                </button>
              </label>
            </div>
          ) : (
            <form onSubmit={handlePasteSubmit} className="space-y-4">
              <textarea
                value={rawText}
                onChange={(e) => setRawText(e.target.value)}
                placeholder="Paste raw email header and body content starting from Received / From headers..."
                rows={10}
                disabled={!isOnline || isLoading}
                className="w-full rounded-xl bg-slate-900 border border-slate-800 p-4 font-mono-code text-xs text-slate-200 focus:ring-1 focus:ring-cyan-500 focus:border-cyan-500 outline-none disabled:opacity-50"
              />
              <div className="flex justify-end">
                <button
                  type="submit"
                  disabled={!isOnline || isLoading || !rawText.trim()}
                  className="px-6 py-2.5 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-xs shadow-lg shadow-cyan-500/25 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isLoading ? 'Running Analysis...' : 'Run Forensic Engine'}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>

    </div>
  );
}
