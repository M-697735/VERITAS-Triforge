import os
import shutil
import time
import traceback
import threading
import datetime
from typing import Dict, Any, Optional

DEFAULT_WATCH_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'inbox'))

class DropfolderWatcher:
    def __init__(self, watch_dir: Optional[str] = None, poll_interval: float = 3.0):
        self.watch_dir = watch_dir or DEFAULT_WATCH_DIR
        self.processed_dir = os.path.join(self.watch_dir, 'processed')
        self.failed_dir = os.path.join(self.watch_dir, 'failed')
        self.poll_interval = poll_interval
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.processed_count = 0
        self.failed_count = 0
        self.last_scan_at: Optional[str] = None
        
        os.makedirs(self.watch_dir, exist_ok=True)
        os.makedirs(self.processed_dir, exist_ok=True)
        os.makedirs(self.failed_dir, exist_ok=True)

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, name='DropfolderWatcherThread', daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def is_alive(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def get_status(self) -> Dict[str, Any]:
        return {
            'status': 'WATCHING' if self.is_alive() else 'STOPPED',
            'watch_dir': self.watch_dir,
            'processed_count': self.processed_count,
            'failed_count': self.failed_count,
            'last_scan_at': self.last_scan_at
        }

    def process_file(self, file_path: str) -> bool:
        filename = os.path.basename(file_path)
        if not filename.lower().endswith('.eml'):
            return False
        if filename.startswith('.') or filename.startswith('~'):
            return False
            
        try:
            # Wait briefly if file is still being copied
            time.sleep(0.1)
            with open(file_path, 'rb') as f:
                raw_bytes = f.read()
                
            if not raw_bytes.strip():
                raise ValueError('Zero-byte empty EML file')
                
            from app.main import run_analysis_pipeline
            from app.ingest.inbox_store import add_inbox_item
            
            analysis = run_analysis_pipeline(raw_bytes, filename=filename, live_reverify=False)
            add_inbox_item(analysis, source='dropfolder', filename=filename)
            
            # Move to processed
            ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            dest = os.path.join(self.processed_dir, f'{ts}_{filename}')
            shutil.move(file_path, dest)
            self.processed_count += 1
            return True
        except Exception as e:
            # Move to failed with error file
            try:
                ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                dest = os.path.join(self.failed_dir, f'{ts}_{filename}')
                if os.path.exists(file_path):
                    shutil.move(file_path, dest)
                err_path = dest + '.error.txt'
                with open(err_path, 'w', encoding='utf-8') as ef:
                    ef.write(f'Processing Error for {filename}:\n{str(e)}\n\n{traceback.format_exc()}')
            except Exception:
                pass
            self.failed_count += 1
            return False

    def scan_once(self):
        self.last_scan_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        try:
            entries = os.listdir(self.watch_dir)
        except Exception:
            return
            
        for entry in entries:
            full_path = os.path.join(self.watch_dir, entry)
            # Only process files directly in watch_dir
            if os.path.isfile(full_path) and entry.lower().endswith('.eml'):
                self.process_file(full_path)

    def _run_loop(self):
        while not self._stop_event.is_set():
            try:
                self.scan_once()
            except Exception:
                pass
            self._stop_event.wait(self.poll_interval)
