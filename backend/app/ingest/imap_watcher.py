import os
import imaplib
import hashlib
import threading
import datetime
import traceback
from typing import Dict, Any, Optional, Tuple

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

class ImapWatcher:
    def __init__(self, poll_interval: float = 10.0):
        self.host = os.environ.get('IMAP_HOST', '').strip()
        self.port = int(os.environ.get('IMAP_PORT', '993'))
        self.user = os.environ.get('IMAP_USER', '').strip()
        self.password = os.environ.get('IMAP_PASSWORD', '').strip()
        self.folder = os.environ.get('IMAP_FOLDER', 'INBOX').strip()
        self.use_ssl = os.environ.get('IMAP_SSL', 'true').lower() in ('true', '1', 'yes')
        self.poll_interval = poll_interval
        
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self.fetched_count = 0
        self.last_check_at: Optional[str] = None
        self.last_error: Optional[str] = None
        self.connection_status = 'NOT_CONFIGURED' if not (self.host and self.user) else 'CONFIGURED'

    def is_configured(self) -> bool:
        return bool(self.host and self.user and self.password)

    def start(self):
        if not self.is_configured():
            return
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run_loop, name='ImapWatcherThread', daemon=True)
            self._thread.start()

    def stop(self):
        self._stop_event.set()
        with self._lock:
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=3.0)

    def is_alive(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def test_connection(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        folder: str = 'INBOX',
        use_ssl: bool = True
    ) -> Dict[str, Any]:
        """Tests IMAP credentials and folder access without storing credentials."""
        client = None
        try:
            if use_ssl:
                client = imaplib.IMAP4_SSL(host, port)
            else:
                client = imaplib.IMAP4(host, port)
                
            client.login(user, password)
            status, _ = client.select(folder, readonly=True)
            if status != 'OK':
                raise ValueError(f"Could not open folder '{folder}' (status: {status})")
                
            typ, data = client.search(None, 'UNSEEN')
            unseen_count = 0
            if typ == 'OK' and data and data[0]:
                unseen_count = len(data[0].split())
                
            client.close()
            client.logout()
            return {
                "success": True,
                "message": f"Successfully connected to {host} as {user}. Found {unseen_count} unread emails in '{folder}'.",
                "unseen_count": unseen_count
            }
        except Exception as e:
            err_msg = str(e)
            if password and password in err_msg:
                err_msg = err_msg.replace(password, '***')
            if client:
                try:
                    client.logout()
                except Exception:
                    pass
            return {
                "success": False,
                "error": f"IMAP connection failed: {err_msg}",
                "unseen_count": 0
            }

    def configure(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        folder: str = 'INBOX',
        use_ssl: bool = True,
        poll_interval: float = 10.0,
        auto_start: bool = True
    ):
        """Updates runtime configuration and starts the background monitoring thread if auto_start=True."""
        self.stop()
        with self._lock:
            self.host = (host or '').strip()
            self.port = int(port or 993)
            self.user = (user or '').strip()
            self.password = (password or '').strip()
            self.folder = (folder or 'INBOX').strip()
            self.use_ssl = bool(use_ssl)
            self.poll_interval = float(poll_interval or 10.0)
            self.connection_status = 'CONFIGURED'
            self.last_error = None
        if auto_start and self.is_configured():
            self.start()

    def disconnect(self):
        """Stops the watcher and marks the connection stopped."""
        self.stop()
        with self._lock:
            self.connection_status = 'STOPPED'
            self.last_error = None

    def get_status(self) -> Dict[str, Any]:
        if not (self.host and self.user):
            return {
                'enabled': False,
                'status': 'NOT_CONFIGURED',
                'message': 'IMAP mailbox ingestion not configured (set host and user)'
            }
        return {
            'enabled': True,
            'status': self.connection_status,
            'host': self.host,
            'port': self.port,
            'user': self.user,
            'folder': self.folder,
            'use_ssl': self.use_ssl,
            'poll_interval': self.poll_interval,
            'fetched_count': self.fetched_count,
            'last_check_at': self.last_check_at,
            'last_error': self.last_error
        }

    def check_once(self) -> int:
        if not self.is_configured():
            return 0
        self.last_check_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        processed_this_run = 0
        client = None
        try:
            if self.use_ssl:
                client = imaplib.IMAP4_SSL(self.host, self.port)
            else:
                client = imaplib.IMAP4(self.host, self.port)
                
            client.login(self.user, self.password)
            self.connection_status = 'CONNECTED'
            self.last_error = None
            
            client.select(self.folder)
            typ, data = client.search(None, 'UNSEEN')
            if typ != 'OK' or not data or not data[0]:
                client.logout()
                return 0
                
            msg_nums = data[0].split()
            from app.main import run_analysis_pipeline
            from app.ingest.inbox_store import has_inbox_sha256, add_inbox_item
            
            for num in msg_nums:
                try:
                    # 1. Fetch RFC 822 bytes
                    typ, msg_data = client.fetch(num, '(RFC822)')
                    if typ != 'OK' or not msg_data:
                        continue
                    raw_bytes = None
                    for part in msg_data:
                        if isinstance(part, tuple) and len(part) >= 2:
                            raw_bytes = part[1]
                            break
                    if not raw_bytes:
                        continue
                        
                    # 2. Duplicate SHA-256 check before analysis
                    raw_sha256 = hashlib.sha256(raw_bytes).hexdigest()
                    if has_inbox_sha256(raw_sha256):
                        # Message is already in the Inbox store; mark \Seen and move to next
                        client.store(num, '+FLAGS', '\\Seen')
                        continue
                        
                    # 3. Run existing 5-layer analysis pipeline
                    fname = 'imap_msg_' + num.decode(errors='ignore') + '.eml'
                    analysis = run_analysis_pipeline(raw_bytes, filename=fname, live_reverify=False)
                    
                    # 4. Successfully add to Inbox store
                    add_inbox_item(analysis, source='imap', filename=fname)
                    
                    # 5. Then mark \Seen
                    client.store(num, '+FLAGS', '\\Seen')
                    processed_this_run += 1
                    self.fetched_count += 1
                except Exception as item_err:
                    # If analysis fails, leave the message unseen so it can be retried!
                    item_err_msg = str(item_err)
                    if self.password and self.password in item_err_msg:
                        item_err_msg = item_err_msg.replace(self.password, '***')
                    print(f"[IMAP Watcher] Error processing message {num}: {item_err_msg}")
                    continue
                
            client.close()
            client.logout()
            return processed_this_run
        except Exception as e:
            err_msg = str(e)
            if self.password and self.password in err_msg:
                err_msg = err_msg.replace(self.password, '***')
            self.connection_status = 'ERROR'
            self.last_error = err_msg
            if client:
                try:
                    client.logout()
                except Exception:
                    pass
            return 0

    def _run_loop(self):
        while not self._stop_event.is_set():
            try:
                self.check_once()
            except Exception:
                pass
            self._stop_event.wait(self.poll_interval)

