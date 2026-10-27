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
  UserCheck,
  Settings,
  Check,
  X,
  Loader2,
  RotateCw,
  Lock
} from 'lucide-react';
import { 
  fetchInbox, 
  fetchInboxItem, 
  reviewInboxItem, 
  saveInboxItem, 
  deleteInboxItem, 
  fetchIngestStatus,
  fetchImapConfig,
  testImapConnection,
  configureImap,
  disconnectImap,
  syncImapNow
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

  // IMAP Configuration Modal State
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [imapHost, setImapHost] = useState('imap.gmail.com');
  const [imapPort, setImapPort] = useState(993);
  const [imapUser, setImapUser] = useState('');
  const [imapPassword, setImapPassword] = useState('');
  const [imapFolder, setImapFolder] = useState('INBOX');
  const [imapSsl, setImapSsl] = useState(true);
  const [testResult, setTestResult] = useState(null);
  const [isTesting, setIsTesting] = useState(false);
  const [isSavingConfig, setIsSavingConfig] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncNotice, setSyncNotice] = useState(null);

  const loadData = async () => {
    try {
      setLoading(true);
      const [inboxData, statusData] = await Promise.all([
        fetchInbox(),
        fetchIngestStatus().catch(() => null)
      ]);
      setItems(inboxData || []);
      setIngestStatus(statusData);
      
      if (statusData?.imap?.user && !imapUser) {
        setImapUser(statusData.imap.user);
        if (statusData.imap.host) setImapHost(statusData.imap.host);
        if (statusData.imap.port) setImapPort(statusData.imap.port);
        if (statusData.imap.folder) setImapFolder(statusData.imap.folder);
      }

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
      fetchIngestStatus().then(status => {
        if (status) setIngestStatus(status);
      }).catch(() => {});
    }, 5000);
    return () => clearInterval(timer);
  }, []);

  const handleApplyPreset = (preset) => {
    if (preset === 'gmail') {
      setImapHost('imap.gmail.com');
      setImapPort(993);
      setImapSsl(true);
      setImapFolder('INBOX');
    } else if (preset === 'outlook') {
      setImapHost('outlook.office365.com');
      setImapPort(993);
      setImapSsl(true);
      setImapFolder('INBOX');
    }
    setTestResult(null);
  };

  const handleTestConnection = async () => {
    if (!imapHost || !imapUser || !imapPassword) {
      setTestResult({ success: false, error: 'Please enter Host, Username/Email, and App Password.' });
      return;
    }
    try {
      setIsTesting(true);
      setTestResult(null);
      const res = await testImapConnection({
        host: imapHost,
        port: parseInt(imapPort, 10),
        user: imapUser,
        password: imapPassword,
        folder: imapFolder,
        use_ssl: imapSsl
      });
      setTestResult(res);
    } catch (err) {
      setTestResult({
        success: false,
        error: err.response?.data?.detail || err.message || 'Connection test failed.'
      });
    } finally {
      setIsTesting(false);
    }
  };

  const handleSaveAndConnect = async () => {
    if (!imapHost || !imapUser || !imapPassword) {
      setTestResult({ success: false, error: 'Please fill in all required fields.' });
      return;
    }
    try {
      setIsSavingConfig(true);
      setTestResult(null);
      await configureImap({
        host: imapHost,
        port: parseInt(imapPort, 10),
        user: imapUser,
        password: imapPassword,
        folder: imapFolder,
        use_ssl: imapSsl,
        poll_interval: 10.0
      });
      setShowConfigModal(false);
      setSyncNotice('Mailbox connected! Monitoring active (10s polling interval).');
      setTimeout(() => setSyncNotice(null), 5000);
      await loadData();
    } catch (err) {
      setTestResult({
        success: false,
        error: err.response?.data?.detail || err.message || 'Failed to configure and connect.'
      });
    } finally {
      setIsSavingConfig(false);
    }
  };

  const handleDisconnect = async () => {
    if (!window.confirm('Disconnect this mailbox? Background monitoring will be stopped.')) return;
    try {
      setIsSavingConfig(true);
      await disconnectImap();
      setShowConfigModal(false);
      setSyncNotice('Mailbox disconnected. Background monitoring stopped.');
      setTimeout(() => setSyncNotice(null), 4000);
      await loadData();
    } catch (err) {
      alert('Failed to disconnect mailbox: ' + (err.response?.data?.detail || err.message));
    } finally {
      setIsSavingConfig(false);
    }
  };

  const handleSyncNow = async () => {
    try {
      setIsSyncing(true);
      setSyncNotice(null);
      const res = await syncImapNow();
      setSyncNotice(res.message || `Sync completed. Processed ${res.processed} new email(s).`);
      setTimeout(() => setSyncNotice(null), 4000);
      await loadData();
    } catch (err) {
      setSyncNotice(err.response?.data?.detail || err.message || 'Sync failed.');
      setTimeout(() => setSyncNotice(null), 4000);
    } finally {
      setIsSyncing(false);
    }
  };

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
    <div className='max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6'>
      <div className='flex flex-col md:flex-row md:items-center md:justify-between pb-6 border-b border-slate-800 gap-4'>
        <div>
          <div className='flex items-center space-x-3'>
            <div className='p-2.5 rounded-xl bg-gradient-to-tr from-cyan-500/20 to-blue-500/20 text-cyan-400 border border-cyan-500/30 shadow-lg shadow-cyan-950/40'>
              <Mail className='w-6 h-6' />
            </div>
            <div>
              <h1 className='text-2xl font-extrabold text-white tracking-tight flex items-center space-x-2'>
                <span>Automated Security Mailbox Ingestion</span>
              </h1>
              <p className='text-xs sm:text-sm text-slate-400'>
                VERITAS automatically monitors and analyzes new emails received in the connected security mailbox
              </p>
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
              <span className='text-rose-400 font-mono font-medium'>ERROR</span>
            ) : (
              <span className='text-slate-500 font-mono'>NOT CONFIGURED</span>
            )}
          </div>

          <button
            onClick={() => {
              setTestResult(null);
              setShowConfigModal(true);
            }}
            className='flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold transition-all shadow-md shadow-cyan-600/20'
          >
            <Settings className='w-3.5 h-3.5' />
            <span>{ingestStatus?.imap?.enabled ? 'Configure Mailbox' : 'Connect Mailbox'}</span>
          </button>

          <button
            onClick={handleSyncNow}
            disabled={isSyncing || !ingestStatus?.imap?.enabled}
            className='flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-cyan-300 text-xs font-semibold transition-colors disabled:opacity-40 disabled:cursor-not-allowed border border-slate-700'
            title='Poll the connected mailbox immediately'
          >
            <RotateCw className={`w-3.5 h-3.5 ${isSyncing ? 'animate-spin text-cyan-400' : ''}`} />
            <span>{isSyncing ? 'Syncing...' : 'Sync Now'}</span>
          </button>

          <button
            onClick={() => setShowGuide(!showGuide)}
            className='flex items-center space-x-1 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition-colors'
          >
            <HelpCircle className='w-4 h-4 text-amber-400' />
            <span>How it Works</span>
          </button>

          <button
            onClick={loadData}
            disabled={loading}
            className='p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors'
            title='Refresh Inbox List'
          >
            <RefreshCw className={'w-4 h-4 ' + (loading ? 'animate-spin text-cyan-400' : '')} />
          </button>
        </div>
      </div>

      {syncNotice && (
        <div className='p-3.5 rounded-xl bg-cyan-950/70 border border-cyan-500/40 text-cyan-200 text-xs font-mono flex items-center justify-between shadow-lg shadow-cyan-950/40 animate-fade-in'>
          <div className='flex items-center space-x-2'>
            <Check className='w-4 h-4 text-cyan-400' />
            <span>{syncNotice}</span>
          </div>
          <button onClick={() => setSyncNotice(null)} className='text-slate-400 hover:text-white'>✕</button>
        </div>
      )}

      {showGuide && (
        <div className='p-5 rounded-xl bg-slate-900/90 border border-cyan-800/40 text-sm text-slate-300 relative'>
          <h3 className='text-base font-semibold text-white mb-2 flex items-center space-x-2'>
            <HelpCircle className='w-5 h-5 text-cyan-400' />
            <span>How Security Mailbox Ingestion Works in VERITAS</span>
          </h3>
          <div className='grid md:grid-cols-3 gap-4 mt-3 text-xs'>
            <div className='p-3 rounded-lg bg-slate-950/60 border border-slate-800'>
              <div className='font-bold text-cyan-400 mb-1'>1. Automated IMAP Monitoring</div>
              <p className='text-slate-400 leading-relaxed'>
                VERITAS continuously monitors the connected Gmail or Outlook mailbox. Unseen messages are fetched, analyzed across all 5 forensic layers, and queued with verdicts automatically.
              </p>
            </div>
            <div className='p-3 rounded-lg bg-slate-950/60 border border-slate-800'>
              <div className='font-bold text-cyan-400 mb-1'>2. Forwarded Abuse Reports</div>
              <p className='text-slate-400 leading-relaxed'>
                If employees forward suspicious emails as attachments, VERITAS auto-unwraps the nested RFC 822 payload, isolates the original headers, and attributes the true source.
              </p>
            </div>
            <div className='p-3 rounded-lg bg-slate-950/60 border border-slate-800'>
              <div className='font-bold text-cyan-400 mb-1'>3. Drop-Folder Intake</div>
              <p className='text-slate-400 leading-relaxed'>
                As a backup demo option, drop any <code className='text-cyan-300 font-mono'>.eml</code> file directly into <code className='text-slate-200 font-mono'>backend/inbox/</code>. The background drop-folder engine ingests it within 3 seconds.
              </p>
            </div>
          </div>
        </div>
      )}

      <div className='flex flex-wrap items-center justify-between gap-4 pb-2'>
        <div className='flex items-center space-x-2'>
          <button
            onClick={() => setFilter('all')}
            className={'px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ' + (filter === 'all' ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40' : 'text-slate-400 hover:bg-slate-800')}
          >
            All Ingested ({items.length})
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
        <div className='text-center py-16 px-4 bg-slate-900/40 border border-slate-800/80 rounded-2xl'>
          <Mail className='w-12 h-12 text-slate-600 mx-auto mb-3' />
          <h3 className='text-base font-semibold text-slate-300'>No Emails in Ingestion Inbox</h3>
          <p className='text-sm text-slate-500 max-w-md mx-auto mt-1'>
            New emails received in the connected security mailbox are automatically analyzed by VERITAS. You can also drop raw <span className='font-mono text-cyan-400'>.eml</span> files into <span className='font-mono text-slate-400'>backend/inbox/</span>.
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

      {/* Connect Mailbox Modal */}
      {showConfigModal && (
        <div className='fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fade-in'>
          <div className='bg-[#111827] border border-slate-800 rounded-2xl max-w-lg w-full p-6 space-y-5 shadow-2xl relative'>
            
            {/* Modal Header */}
            <div className='flex items-center justify-between border-b border-slate-800 pb-4'>
              <div className='flex items-center space-x-3'>
                <div className='p-2 rounded-lg bg-purple-500/10 text-purple-400 border border-purple-500/30'>
                  <Server className='w-5 h-5' />
                </div>
                <div>
                  <h3 className='text-base font-bold text-white'>Connect Security Mailbox (IMAP)</h3>
                  <p className='text-xs text-slate-400'>Continuous background intake for automatic email analysis</p>
                </div>
              </div>
              <button
                onClick={() => setShowConfigModal(false)}
                className='text-slate-400 hover:text-white transition-colors p-1 rounded-lg hover:bg-slate-800'
              >
                <X className='w-5 h-5' />
              </button>
            </div>

            {/* Provider Quick Presets */}
            <div className='space-y-1.5'>
              <span className='text-[11px] font-mono text-slate-400 uppercase tracking-wider'>Quick Provider Presets:</span>
              <div className='flex items-center space-x-2'>
                <button
                  type='button'
                  onClick={() => handleApplyPreset('gmail')}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all ${
                    imapHost === 'imap.gmail.com'
                      ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/50'
                      : 'bg-slate-900 text-slate-300 border-slate-800 hover:bg-slate-800'
                  }`}
                >
                  Gmail (imap.gmail.com)
                </button>
                <button
                  type='button'
                  onClick={() => handleApplyPreset('outlook')}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all ${
                    imapHost === 'outlook.office365.com'
                      ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/50'
                      : 'bg-slate-900 text-slate-300 border-slate-800 hover:bg-slate-800'
                  }`}
                >
                  Outlook / Office 365
                </button>
              </div>
            </div>

            {/* Connection Form Fields */}
            <div className='space-y-3.5 text-xs'>
              <div className='grid grid-cols-3 gap-3'>
                <div className='col-span-2 space-y-1'>
                  <label className='font-semibold text-slate-300'>IMAP Host</label>
                  <input
                    type='text'
                    value={imapHost}
                    onChange={(e) => setImapHost(e.target.value)}
                    placeholder='imap.gmail.com'
                    className='w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-white font-mono focus:outline-none focus:border-cyan-500'
                  />
                </div>
                <div className='space-y-1'>
                  <label className='font-semibold text-slate-300'>Port</label>
                  <input
                    type='number'
                    value={imapPort}
                    onChange={(e) => setImapPort(e.target.value)}
                    placeholder='993'
                    className='w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-white font-mono focus:outline-none focus:border-cyan-500'
                  />
                </div>
              </div>

              <div className='space-y-1'>
                <label className='font-semibold text-slate-300'>Mailbox Email / Username</label>
                <input
                  type='text'
                  value={imapUser}
                  onChange={(e) => setImapUser(e.target.value)}
                  placeholder='veritas.forensics.demo@gmail.com'
                  className='w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-white font-mono focus:outline-none focus:border-cyan-500'
                />
              </div>

              <div className='space-y-1'>
                <div className='flex items-center justify-between'>
                  <label className='font-semibold text-slate-300'>App Password</label>
                  <span className='text-[10px] text-cyan-400 font-mono'>Kept in runtime memory only</span>
                </div>
                <div className='relative'>
                  <input
                    type='password'
                    value={imapPassword}
                    onChange={(e) => setImapPassword(e.target.value)}
                    placeholder='16-character Google App Password'
                    className='w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-white font-mono focus:outline-none focus:border-cyan-500'
                  />
                  <Lock className='w-4 h-4 text-slate-500 absolute right-3 top-2.5' />
                </div>
                <p className='text-[10px] text-slate-400 leading-normal'>
                  For Gmail: Generate a 16-character App Password at <span className='text-cyan-300 font-mono'>myaccount.google.com/apppasswords</span> (2-Step Verification must be enabled).
                </p>
              </div>

              <div className='grid grid-cols-2 gap-3 pt-1'>
                <div className='space-y-1'>
                  <label className='font-semibold text-slate-300'>Folder</label>
                  <input
                    type='text'
                    value={imapFolder}
                    onChange={(e) => setImapFolder(e.target.value)}
                    placeholder='INBOX'
                    className='w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-white font-mono focus:outline-none focus:border-cyan-500'
                  />
                </div>
                <div className='flex items-center space-x-2 pt-5'>
                  <input
                    type='checkbox'
                    id='sslCheck'
                    checked={imapSsl}
                    onChange={(e) => setImapSsl(e.target.checked)}
                    className='w-4 h-4 rounded bg-slate-900 border-slate-800 text-cyan-500 focus:ring-0 cursor-pointer'
                  />
                  <label htmlFor='sslCheck' className='text-xs font-semibold text-slate-300 cursor-pointer'>
                    Use SSL / TLS (Port 993)
                  </label>
                </div>
              </div>
            </div>

            {/* Connection Test Result Feedback */}
            {testResult && (
              <div className={`p-3 rounded-lg text-xs font-mono border ${
                testResult.success
                  ? 'bg-emerald-950/60 border-emerald-500/50 text-emerald-300'
                  : 'bg-rose-950/60 border-rose-500/50 text-rose-300'
              }`}>
                {testResult.success ? (
                  <div className='flex items-center space-x-2'>
                    <Check className='w-4 h-4 text-emerald-400 shrink-0' />
                    <span>{testResult.message}</span>
                  </div>
                ) : (
                  <div className='flex items-start space-x-2'>
                    <AlertTriangle className='w-4 h-4 text-rose-400 shrink-0 mt-0.5' />
                    <span>{testResult.error || 'Connection failed'}</span>
                  </div>
                )}
              </div>
            )}

            {/* Modal Actions */}
            <div className='flex items-center justify-between pt-2 border-t border-slate-800'>
              <div>
                {ingestStatus?.imap?.enabled && (
                  <button
                    type='button'
                    onClick={handleDisconnect}
                    disabled={isSavingConfig}
                    className='text-xs font-semibold text-rose-400 hover:text-rose-300 transition-colors'
                  >
                    Disconnect Mailbox
                  </button>
                )}
              </div>

              <div className='flex items-center space-x-2'>
                <button
                  type='button'
                  onClick={handleTestConnection}
                  disabled={isTesting || isSavingConfig}
                  className='px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition-colors flex items-center space-x-1.5'
                >
                  {isTesting && <Loader2 className='w-3.5 h-3.5 animate-spin text-cyan-400' />}
                  <span>{isTesting ? 'Testing...' : 'Test Connection'}</span>
                </button>

                <button
                  type='button'
                  onClick={handleSaveAndConnect}
                  disabled={isTesting || isSavingConfig}
                  className='px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-bold transition-all shadow-md shadow-cyan-600/30 flex items-center space-x-1.5'
                >
                  {isSavingConfig && <Loader2 className='w-3.5 h-3.5 animate-spin text-white' />}
                  <span>{isSavingConfig ? 'Connecting...' : 'Connect & Start Monitoring'}</span>
                </button>
              </div>
            </div>

          </div>
        </div>
      )}

    </div>
  );
}