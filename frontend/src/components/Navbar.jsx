import React, { useState, useEffect } from 'react';
import { ShieldAlert, History, Upload, Mail } from 'lucide-react';
import { checkHealth } from '../api/client';

export default function Navbar({ activeTab, setActiveTab, historyCount, inboxCount = 0, onHealthChange }) {
  // 'ONLINE' | 'STARTING' | 'OFFLINE'
  const [healthStatus, setHealthStatus] = useState('STARTING');

  useEffect(() => {
    let failCount = 0;
    let isMounted = true;

    const poll = async () => {
      try {
        const data = await checkHealth();
        if (data && data.status === 'ok') {
          failCount = 0;
          if (isMounted) {
            setHealthStatus('ONLINE');
            if (onHealthChange) onHealthChange('ONLINE');
          }
        } else {
          throw new Error('Not ok');
        }
      } catch (err) {
        failCount += 1;
        if (isMounted) {
          const nextStatus = failCount >= 2 ? 'OFFLINE' : 'STARTING';
          setHealthStatus(nextStatus);
          if (onHealthChange) onHealthChange(nextStatus);
        }
      }
    };

    poll();
    const interval = setInterval(poll, 3000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [onHealthChange]);

  return (
    <header className="border-b border-slate-800 bg-[#0E1424]/90 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        
        {/* Brand */}
        <div className="flex items-center space-x-3 cursor-pointer" onClick={() => setActiveTab('upload')}>
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20 ring-1 ring-white/20">
            <ShieldAlert className="w-6 h-6 text-white" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-extrabold text-xl tracking-wider text-white">VERITAS</span>
              <span className="text-[10px] uppercase font-mono font-bold px-2 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800/50">
                v1.0 Demo
              </span>
            </div>
            <p className="text-xs text-slate-400 font-medium">Cross-Layer Email Forensics Engine</p>
          </div>
        </div>

        {/* System Status Indicator */}
        <div className="hidden md:flex items-center space-x-2 px-3 py-1.5 rounded-full bg-slate-900/80 border border-slate-800 text-xs">
          {healthStatus === 'ONLINE' ? (
            <>
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              <span className="text-emerald-400 font-mono font-semibold">ENGINE ONLINE</span>
            </>
          ) : healthStatus === 'STARTING' ? (
            <>
              <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse"></span>
              <span className="text-amber-400 font-mono font-semibold">STARTING... retrying</span>
            </>
          ) : (
            <>
              <span className="w-2 h-2 rounded-full bg-rose-500"></span>
              <span className="text-rose-400 font-mono font-semibold">OFFLINE</span>
            </>
          )}
        </div>

        {/* Navigation Actions */}
        <div className="flex items-center space-x-3">
          <button
            onClick={() => setActiveTab('upload')}
            className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-lg text-sm font-medium transition-all ${
              activeTab === 'upload'
                ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30'
                : 'text-slate-300 hover:bg-slate-800'
            }`}
          >
            <Upload className="w-4 h-4" />
            <span>Analyze Email</span>
          </button>

          <button
            onClick={() => setActiveTab('inbox')}
            className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-lg text-sm font-medium transition-all relative ${
              activeTab === 'inbox'
                ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30'
                : 'text-slate-300 hover:bg-slate-800'
            }`}
          >
            <Mail className="w-4 h-4" />
            <span>Inbox</span>
            {inboxCount > 0 && (
              <span className="ml-1 px-1.5 py-0.2 rounded-full bg-amber-500 text-slate-950 font-mono font-bold text-[10px] animate-pulse">
                {inboxCount}
              </span>
            )}
          </button>

          <button
            onClick={() => setActiveTab('history')}
            className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-lg text-sm font-medium transition-all relative ${
              activeTab === 'history'
                ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30'
                : 'text-slate-300 hover:bg-slate-800'
            }`}
          >
            <History className="w-4 h-4" />
            <span>Case History</span>
            {historyCount > 0 && (
              <span className="ml-1 px-1.5 py-0.2 rounded-full bg-cyan-500 text-slate-950 font-mono font-bold text-[10px]">
                {historyCount}
              </span>
            )}
          </button>
        </div>

      </div>
    </header>
  );
}
