import os
import imaplib
import threading
import datetime
import traceback
from typing import Dict, Any, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

class ImapWatcher:
    def __init__(self, poll_interval: float = 30.0):
        self.host = os.environ.get('IMAP_HOST', '').strip()
        self.port = int(os.environ.get('IMAP_PORT', '993'))
        self.user = os.environ.get('IMAP_USER', '').strip()
        self.password = os.environ.get('IMAP_PASSWORD', '').strip()
        self.folder = os.environ.get('IMAP_FOLDER', 'INBOX').strip()
        self.use_ssl = os.environ.get('IMAP_SSL', 'true').lower() in ('true', '1', 'yes')
        self.poll_interval = poll_interval
        
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.fetched_count = 0
        self.last_check_at: Optional[str] = None
        self.last_error: Optional[str] = None
        self.connection_status = 'NOT_CONFIGURED' if not (self.host and self.user) else 'CONFIGURED'

    def is_configured(self) -> bool:
        return bool(self.host and self.user and self.password)

    def start(self):
        if not self.is_configured():
            return
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, name='ImapWatcherThread', daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)

    def is_alive(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def get_status(self) -> Dict[str, Any]:
        if not (self.host and self.user):
            return {
                'enabled': False,
                'status': 'NOT_CONFIGURED',
                'message': 'IMAP mailbox ingestion not configured (set IMAP_HOST and IMAP_USER)'
            }
        return {
            'enabled': True,
            'status': self.connection_status,
            'host': self.host,
            'port': self.port,
            'user': self.user,
            'folder': self.folder,
            'use_ssl': self.use_ssl,
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
            from app.ingest.inbox_store import add_inbox_item
            
            for num in msg_nums:
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
                    
                fname = 'imap_msg_' + num.decode(errors='ignore') + '.eml'
                analysis = run_analysis_pipeline(raw_bytes, filename=fname, live_reverify=False)
                add_inbox_item(analysis, source='imap', filename=fname)
                client.store(num, '+FLAGS', '\\Seen')
                processed_this_run += 1
                self.fetched_count += 1
                
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
