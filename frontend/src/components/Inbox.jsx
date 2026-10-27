import React, { useState, useEffect } from 'react';
import { 
  Mail, 
  RefreshCw, 
  FolderDown, 
  Server, 
  CheckCircle, 
  AlertTriangle, 
  ShieldAlert, 
  Trash2, 
  ExternalLink, 
  HelpCircle,
  Bookmark,
  ChevronDown,
  UserCheck
} from 'lucide-react';
import { 
  fetchInbox, 
  fetchInboxItem, 
  reviewInboxItem, 
  saveInboxItem, 
  deleteInboxItem, 
  fetchIngestStatus 
} from '../api/client';

export default function Inbox({ onSelectInboxItem, onInboxUpdated }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [ingestStatus, setIngestStatus] = useState(null);
  const [filter, setFilter] = useState('all');
  const [sortBy, setSortBy] = useState('newest');
  const [showGuide, setShowGuide] = useState(false);
  const [selectedLabels, setSelectedLabels] = useState({});
  const [actionLoading, setActionLoading] = useState({});

  const loadData = async () => {
    try {
      setLoading(true);
      const [inboxData, statusData] = await Promise.all([
        fetchInbox(),
        fetchIngestStatus().catch(() => null)
      ]);
      setItems(inboxData || []);
      setIngestStatus(statusData);
      if (onInboxUpdated) {
        const unreviewed = (inboxData || []).filter(i => !i.reviewed).length;
        onInboxUpdated(unreviewed);
      }
    } catch (err) {
      console.error('Failed to load inbox data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const timer = setInterval(() => {
      fetchInbox().then(data => {
        if (data) {
          setItems(data);
          if (onInboxUpdated) {
            onInboxUpdated(data.filter(i => !i.reviewed).length);
          }
        }
      }).catch(() => {});
    }, 5000);
    return () => clearInterval(timer);
  }, []);

  const handleReviewToggle = async (item) => {
    try {
      setActionLoading(prev => ({ ...prev, [item.id]: true }));
      await reviewInboxItem(item.id);
      await loadData();
    } catch (err) {
      alert('Failed to update review status');
    } finally {
      setActionLoading(prev => ({ ...prev, [item.id]: false }));
    }
  };

  const handleSaveToHistory = async (item) => {
    try {
      setActionLoading(prev => ({ ...prev, ['save_' + item.id]: true }));
      const chosenLabel = selectedLabels[item.id] || 
        (item.summary?.verdict === 'Likely Fraudulent' ? 'Confirmed fraud' : 
         item.summary?.verdict === 'Needs Review' ? 'Suspicious' : 'Cleared');
         
      const res = await saveInboxItem(item.id, chosenLabel);
      await loadData();
      alert('Saved as ' + (res.saved_case?.case_id || 'case') + ' with label: ' + chosenLabel);
    } catch (err) {
      alert('Failed to save to case history: ' + (err.response?.data?.detail || err.message));
    } finally {
      setActionLoading(prev => ({ ...prev, ['save_' + item.id]: false }));
    }
  };

  const handleDelete = async (item) => {
    if (!window.confirm('Delete inbox item ' + item.id + '?')) return;
    try {
      setActionLoading(prev => ({ ...prev, [item.id]: true }));
      await deleteInboxItem(item.id);
      await loadData();
    } catch (err) {
      alert('Failed to delete inbox item');
    } finally {
      setActionLoading(prev => ({ ...prev, [item.id]: false }));
    }
  };

  const handleInspect = async (item) => {
    try {
      setActionLoading(prev => ({ ...prev, ['inspect_' + item.id]: true }));
      const fullItem = await fetchInboxItem(item.id);
      if (fullItem && fullItem.analysis && onSelectInboxItem) {
        onSelectInboxItem(fullItem.analysis);
      }
    } catch (err) {
      alert('Failed to load item analysis');
    } finally {
      setActionLoading(prev => ({ ...prev, ['inspect_' + item.id]: false }));
    }
  };

  let displayedItems = [...items];
  if (filter === 'unreviewed') {
    displayedItems = displayedItems.filter(i => !i.reviewed);
  } else if (filter === 'reviewed') {
    displayedItems = displayedItems.filter(i => i.reviewed);
  }

  if (sortBy === 'severity') {
    const scoreMap = { 'Likely Fraudulent': 3, 'Needs Review': 2, 'Likely Legitimate': 1 };
    displayedItems.sort((a, b) => {
      const sA = scoreMap[a.summary?.verdict] || 0;
      const sB = scoreMap[b.summary?.verdict] || 0;
      return sB - sA;
    });
  } else {
    displayedItems.sort((a, b) => new Date(b.received_at) - new Date(a.received_at));
  }

  const unreviewedCount = items.filter(i => !i.reviewed).length;
  const reviewedCount = items.filter(i => i.reviewed).length;

  return (
    <div className='max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8'>
      <div className='flex flex-col md:flex-row md:items-center md:justify-between pb-6 border-b border-slate-800 gap-4'>
        <div>
          <div className='flex items-center space-x-3'>
            <div className='p-2 rounded-lg bg-cyan-500/10 text-cyan-400 border border-cyan-500/20'>
              <Mail className='w-6 h-6' />
            </div>
            <div>
              <h1 className='text-2xl font-bold text-white tracking-tight'>Report-a-Phish Mailbox Ingestion</h1>
              <p className='text-sm text-slate-400'>Automated background intake from Drop-Folder and IMAP monitoring</p>
            </div>
          </div>
        </div>

        <div className='flex items-center space-x-3 flex-wrap gap-y-2'>
          <div className='flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs'>
            <FolderDown className='w-4 h-4 text-cyan-400' />
            <span className='text-slate-400'>Drop-Folder:</span>
            {ingestStatus?.dropfolder?.status === 'WATCHING' ? (
              <span className='flex items-center text-emerald-400 font-mono font-medium'>
                <span className='w-2 h-2 rounded-full bg-emerald-400 animate-pulse mr-1.5'></span>
                WATCHING
              </span>
            ) : (
              <span className='text-slate-500 font-mono'>STOPPED</span>
            )}
          </div>

          <div className='flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs'>
            <Server className='w-4 h-4 text-purple-400' />
            <span className='text-slate-400'>IMAP:</span>
            {ingestStatus?.imap?.status === 'CONNECTED' ? (
              <span className='flex items-center text-emerald-400 font-mono font-medium'>
                <span className='w-2 h-2 rounded-full bg-emerald-400 animate-pulse mr-1.5'></span>
                CONNECTED
              </span>
            ) : ingestStatus?.imap?.status === 'ERROR' ? (
              <span className='text-rose-400 font-mono'>ERROR</span>
            ) : (
              <span className='text-slate-500 font-mono'>NOT CONFIGURED</span>
            )}
          </div>

          <button
            onClick={() => setShowGuide(!showGuide)}
            className='flex items-center space-x-1 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition-colors'
          >
            <HelpCircle className='w-4 h-4 text-amber-400' />
            <span>How to Report</span>
          </button>

          <button
            onClick={loadData}
            disabled={loading}
            className='p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors'
            title='Refresh Inbox'
          >
            <RefreshCw className={'w-4 h-4 ' + (loading ? 'animate-spin text-cyan-400' : '')} />
          </button>
        </div>
      </div>

      {showGuide && (
        <div className='mt-6 p-5 rounded-xl bg-slate-900/90 border border-cyan-800/40 text-sm text-slate-300 relative'>
          <h3 className='text-base font-semibold text-white mb-2 flex items-center space-x-2'>
            <HelpCircle className='w-5 h-5 text-cyan-400' />
            <span>How to Submit Phishing Reports to VERITAS</span>
          </h3>
          <div className='grid md:grid-cols-3 gap-4 mt-3 text-xs'>
            <div className='p-3 rounded-lg bg-slate-950/60 border border-slate-800'>
              <div className='font-bold text-cyan-400 mb-1'>1. Forward as Attachment</div>
              <p className='text-slate-400 leading-relaxed'>
                In Outlook press <code className='text-amber-300 font-mono'>Ctrl+Alt+F</code> or More &gt; Forward as Attachment. In Gmail click &quot;Download message&quot;. VERITAS unpacks forwarded reports and maps the original sender and reporter.
              </p>
            </div>
            <div className='p-3 rounded-lg bg-slate-950/60 border border-slate-800'>
              <div className='font-bold text-cyan-400 mb-1'>2. Drop Folder Watcher</div>
              <p className='text-slate-400 leading-relaxed'>
                Drop any raw <code className='text-cyan-300 font-mono'>.eml</code> file directly into <code className='text-slate-200 font-mono'>backend/inbox/</code>. The engine processes it within 3 seconds, runs the 5-layer analysis, and queues it here.
              </p>
            </div>
            <div className='p-3 rounded-lg bg-slate-950/60 border border-slate-800'>
              <div className='font-bold text-cyan-400 mb-1'>3. Dedicated IMAP Mailbox</div>
              <p className='text-slate-400 leading-relaxed'>
                Set <code className='text-purple-300 font-mono'>IMAP_HOST</code> and <code className='text-purple-300 font-mono'>IMAP_USER</code> in <code className='text-slate-200 font-mono'>.env</code>. VERITAS securely polls your abuse mailbox over SSL and marks seen items.
              </p>
            </div>
          </div>
        </div>
      )}

      <div className='mt-6 flex flex-wrap items-center justify-between gap-4 pb-4'>
        <div className='flex items-center space-x-2'>
          <button
            onClick={() => setFilter('all')}
            className={'px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ' + (filter === 'all' ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40' : 'text-slate-400 hover:bg-slate-800')}
          >
            All Reports ({items.length})
          </button>
          <button
            onClick={() => setFilter('unreviewed')}
            className={'px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ' + (filter === 'unreviewed' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40' : 'text-slate-400 hover:bg-slate-800')}
          >
            Unreviewed ({unreviewedCount})
          </button>
          <button
            onClick={() => setFilter('reviewed')}
            className={'px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ' + (filter === 'reviewed' ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40' : 'text-slate-400 hover:bg-slate-800')}
          >
            Reviewed ({reviewedCount})
          </button>
        </div>

        <div className='flex items-center space-x-2 text-xs text-slate-400'>
          <span>Sort:</span>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className='bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1 text-slate-300 text-xs focus:outline-none focus:border-cyan-500'
          >
            <option value='newest'>Newest Received</option>
            <option value='severity'>Severity (Fraud First)</option>
          </select>
        </div>
      </div>

      {displayedItems.length === 0 ? (
        <div className='text-center py-16 px-4 bg-slate-900/40 border border-slate-800/80 rounded-2xl mt-4'>
          <Mail className='w-12 h-12 text-slate-600 mx-auto mb-3' />
          <h3 className='text-base font-semibold text-slate-300'>No Reported Emails in Ingestion Inbox</h3>
          <p className='text-sm text-slate-500 max-w-md mx-auto mt-1'>
            Drop any suspicious <span className='font-mono text-cyan-400'>.eml</span> file into <span className='font-mono text-slate-400'>backend/inbox/</span> or configure IMAP credentials in <span className='font-mono text-slate-400'>.env</span> to auto-ingest user reports.
          </p>
        </div>
      ) : (
        <div className='grid gap-4 mt-2'>
          {displayedItems.map((item) => {
            const verdict = item.summary?.verdict || 'Unknown';
            const isFraud = verdict === 'Likely Fraudulent';
            const isReview = verdict === 'Needs Review';
            const defaultLabel = isFraud ? 'Confirmed fraud' : isReview ? 'Suspicious' : 'Cleared';
            const currentLabel = selectedLabels[item.id] || defaultLabel;

            return (
              <div
                key={item.id}
                className={'p-5 rounded-xl border transition-all ' + (!item.reviewed ? 'bg-slate-900/90 border-slate-700/80 hover:border-cyan-500/50 shadow-md' : 'bg-slate-900/40 border-slate-800/60 opacity-85 hover:opacity-100')}
              >
                <div className='flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4'>
                  <div className='flex-1 min-w-0'>
                    <div className='flex items-center space-x-2 flex-wrap gap-y-1 mb-2'>
                      <span className='font-mono font-bold text-xs text-slate-300 bg-slate-800 px-2 py-0.5 rounded'>
                        {item.id}
                      </span>

                      <span className='text-[11px] font-mono uppercase px-2 py-0.5 rounded bg-slate-800/60 text-slate-400 border border-slate-700/50'>
                        {item.source}
                      </span>

                      {item.summary?.is_forwarded_report && (
                        <span className='inline-flex items-center space-x-1 text-[11px] font-medium px-2 py-0.5 rounded bg-cyan-950/80 text-cyan-300 border border-cyan-800/60'>
                          <UserCheck className='w-3 h-3 text-cyan-400' />
                          <span>Reported by: {item.reporter}</span>
                        </span>
                      )}

                      {item.reviewed ? (
                        <span className='text-[11px] font-semibold text-emerald-400 bg-emerald-950/50 border border-emerald-800/50 px-2 py-0.5 rounded'>
                          Reviewed ✓
                        </span>
                      ) : (
                        <span className='text-[11px] font-semibold text-amber-400 bg-amber-950/50 border border-amber-800/50 px-2 py-0.5 rounded'>
                          Unreviewed
                        </span>
                      )}

                      {item.saved_case_id && (
                        <span className='text-[11px] font-mono text-cyan-400 bg-cyan-950/50 border border-cyan-800/50 px-2 py-0.5 rounded'>
                          Saved ({item.saved_case_id})
                        </span>
                      )}
                    </div>

                    <h2 className='text-base font-bold text-white truncate'>
                      {item.summary?.subject || '(No Subject)'}
                    </h2>

                    <div className='mt-1 text-xs text-slate-400 flex flex-wrap gap-x-4 gap-y-1'>
                      <span><strong className='text-slate-300'>From:</strong> {item.summary?.from || 'Unknown'}</span>
                      {item.summary?.to && <span><strong className='text-slate-300'>To:</strong> {item.summary?.to}</span>}
                      <span><strong className='text-slate-300'>Received:</strong> {new Date(item.received_at).toLocaleString()}</span>
                    </div>

                    {item.summary?.contradictions?.length > 0 && (
                      <div className='mt-2 flex items-center space-x-1.5 flex-wrap gap-y-1'>
                        <span className='text-xs text-rose-400 font-medium'>Contradictions:</span>
                        {item.summary.contradictions.map((c, idx) => (
                          <span
                            key={idx}
                            className='text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-rose-950/70 text-rose-300 border border-rose-800/60'
                          >
                            {typeof c === 'string' ? c : c.rule_id}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className='flex items-center space-x-3 shrink-0'>
                    <div className={'px-3 py-1.5 rounded-lg border text-xs font-bold text-center ' + (isFraud ? 'bg-rose-950/60 text-rose-400 border-rose-800/60' : isReview ? 'bg-amber-950/60 text-amber-400 border-amber-800/60' : 'bg-emerald-950/60 text-emerald-400 border-emerald-800/60')}>
                      <div className='text-[10px] uppercase font-mono tracking-wider opacity-80'>Verdict</div>
                      <div>{verdict}</div>
                    </div>
                  </div>

                  <div className='flex items-center space-x-2 shrink-0 flex-wrap gap-y-2'>
                    <button
                      onClick={() => handleInspect(item)}
                      disabled={actionLoading['inspect_' + item.id]}
                      className='flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold transition-all shadow-sm shadow-cyan-600/30'
                    >
                      <ExternalLink className='w-3.5 h-3.5' />
                      <span>Inspect</span>
                    </button>

                    <button
                      onClick={() => handleReviewToggle(item)}
                      disabled={actionLoading[item.id]}
                      className='px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition-colors'
                      title={item.reviewed ? 'Mark as Unreviewed' : 'Mark as Reviewed'}
                    >
                      {item.reviewed ? 'Mark Unreviewed' : 'Mark Reviewed'}
                    </button>

                    <div className='flex items-center rounded-lg bg-slate-800/80 border border-slate-700 p-0.5'>
                      <select
                        value={currentLabel}
                        onChange={(e) => setSelectedLabels(prev => ({ ...prev, [item.id]: e.target.value }))}
                        className='bg-transparent text-slate-300 text-xs px-2 py-1 rounded focus:outline-none'
                      >
                        <option value='Confirmed fraud' className='bg-slate-900 text-rose-400'>Confirmed fraud</option>
                        <option value='Suspicious' className='bg-slate-900 text-amber-400'>Suspicious</option>
                        <option value='Cleared' className='bg-slate-900 text-emerald-400'>Cleared</option>
                      </select>

                      <button
                        onClick={() => handleSaveToHistory(item)}
                        disabled={actionLoading['save_' + item.id]}
                        className='flex items-center space-x-1 px-2.5 py-1 rounded bg-slate-700 hover:bg-slate-600 text-white text-xs font-semibold transition-all ml-1'
                        title='Save into persistent Case History with chosen label'
                      >
                        <Bookmark className='w-3 h-3 text-cyan-400' />
                        <span>Save</span>
                      </button>
                    </div>

                    <button
                      onClick={() => handleDelete(item)}
                      disabled={actionLoading[item.id]}
                      className='p-1.5 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-950/30 transition-colors'
                      title='Delete inbox item'
                    >
                      <Trash2 className='w-4 h-4' />
                    </button>
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