import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import EmlUploader from './components/EmlUploader';
import AnalysisDashboard from './components/AnalysisDashboard';
import CaseHistory from './components/CaseHistory';
import Inbox from './components/Inbox';
import { analyzeEmail, fetchHistory, fetchInbox } from './api/client';

export default function App() {
  const [activeTab, setActiveTab] = useState('upload'); // 'upload' | 'analysis' | 'history' | 'inbox'
  const [analysisData, setAnalysisData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [historyCount, setHistoryCount] = useState(0);
  const [inboxCount, setInboxCount] = useState(0);
  const [healthStatus, setHealthStatus] = useState('STARTING');
  const [errorMsg, setErrorMsg] = useState(null);

  const refreshCounts = async () => {
    try {
      const [history, inbox] = await Promise.all([
        fetchHistory().catch(() => []),
        fetchInbox().catch(() => [])
      ]);
      if (Array.isArray(history)) setHistoryCount(history.length);
      if (Array.isArray(inbox)) setInboxCount(inbox.filter(i => !i.reviewed).length);
    } catch (err) {
      console.warn("Failed to fetch counts:", err);
    }
  };

  useEffect(() => {
    refreshCounts();
  }, []);

  const refreshHistoryCount = refreshCounts;

  const handleAnalyze = async (fileOrContent, isRawText = false, liveReverify = false) => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const data = await analyzeEmail(fileOrContent, isRawText, liveReverify);
      setAnalysisData(data);
      await refreshCounts();
      setActiveTab('analysis');
    } catch (err) {
      console.error("Analysis failed:", err);
      setErrorMsg(err.response?.data?.detail || err.message || "Failed to analyze email. Please check server logs.");
    } finally {
      setIsLoading(false);
    }
  };

  const isOnline = healthStatus === 'ONLINE';

  return (
    <div className="min-h-screen flex flex-col bg-[#0B0F19]">
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        historyCount={historyCount}
        inboxCount={inboxCount}
        onHealthChange={setHealthStatus}
      />

      <main className="flex-1 px-4 sm:px-6 lg:px-8">
        {errorMsg && (
          <div className="max-w-4xl mx-auto mt-4 p-4 rounded-xl bg-rose-950/60 border border-rose-500/50 text-rose-300 text-xs font-mono flex items-center justify-between">
            <span>[ERROR] {errorMsg}</span>
            <button onClick={() => setErrorMsg(null)} className="text-slate-400 hover:text-white">✕</button>
          </div>
        )}

        {activeTab === 'upload' && (
          <EmlUploader onAnalyze={handleAnalyze} isLoading={isLoading} isOnline={isOnline} />
        )}

        {activeTab === 'analysis' && analysisData && (
          <AnalysisDashboard
            analysisData={analysisData}
            onNewAnalysis={() => setActiveTab('upload')}
            onCaseSaved={(savedAnalysis) => {
              setAnalysisData(savedAnalysis);
              refreshCounts();
            }}
          />
        )}

        {activeTab === 'history' && (
          <CaseHistory
            onSelectCase={(fullAnalysis) => {
              setAnalysisData(fullAnalysis);
              setActiveTab('analysis');
            }}
            onHistoryUpdated={refreshCounts}
          />
        )}

        {activeTab === 'inbox' && (
          <Inbox
            onSelectInboxItem={(fullAnalysis) => {
              setAnalysisData(fullAnalysis);
              setActiveTab('analysis');
            }}
            onInboxUpdated={(unreviewedCount) => {
              setInboxCount(unreviewedCount);
              refreshCounts();
            }}
          />
        )}
      </main>

      {/* Pitch Deck Footer Branding */}
      <footer className="border-t border-slate-900 bg-[#0A0D16] py-4 text-center text-xs text-slate-500 font-mono">
        VERITAS Email Forensics Platform — Multi-Layer Engine & Cross-Layer Contradiction Differentiator
      </footer>
    </div>
  );
}
