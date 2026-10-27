import os
import json
import secrets
import datetime
import threading
from typing import List, Dict, Any, Optional, Tuple

INBOX_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'inbox.json')
MAX_INBOX_ITEMS = 200

_lock = threading.Lock()

def _get_inbox_file() -> str:
    return INBOX_FILE

def _load_inbox() -> List[Dict[str, Any]]:
    path = _get_inbox_file()
    if not os.path.exists(path):
        return []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            return []
    except Exception:
        bak_path = path + '.bak'
        try:
            if os.path.exists(path):
                if os.path.exists(bak_path):
                    os.remove(bak_path)
                os.rename(path, bak_path)
        except Exception:
            pass
        return []

def _save_inbox(items: List[Dict[str, Any]]):
    path = _get_inbox_file()
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp_path = path + f'.tmp.{secrets.token_hex(4)}'
    with open(tmp_path, 'w', encoding='utf-8') as f:
        json.dump(items, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, path)

def add_inbox_item(analysis_payload: Dict[str, Any], source: str = 'dropfolder', reporter: Optional[str] = None, filename: str = 'reported.eml') -> Dict[str, Any]:
    with _lock:
        items = _load_inbox()
        inbox_id = f'INBOX-{secrets.token_hex(4).upper()}'
        now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        rep = reporter
        if not rep:
            if analysis_payload.get('is_forwarded_report'):
                rep = analysis_payload.get('reported_by') or 'Unknown Reporter'
            else:
                rep = analysis_payload.get('email_meta', {}).get('from') or 'Direct Ingestion'
                
        summary = {
            'subject': analysis_payload.get('email_meta', {}).get('subject', '(No Subject)'),
            'from': analysis_payload.get('email_meta', {}).get('from', ''),
            'to': analysis_payload.get('email_meta', {}).get('to', ''),
            'verdict': analysis_payload.get('verdict', {}).get('verdict', 'Unknown'),
            'risk_score': analysis_payload.get('verdict', {}).get('risk_score', 0),
            'contradictions': analysis_payload.get('contradictions', []),
            'is_forwarded_report': analysis_payload.get('is_forwarded_report', False),
        }
        
        item = {
            'id': inbox_id,
            'source': source,
            'received_at': now_utc,
            'reviewed': False,
            'reporter': rep,
            'filename': filename,
            'sha256_hash': analysis_payload.get('sha256_hash', ''),
            'saved_case_id': None,
            'summary': summary,
            'analysis': analysis_payload
        }
        
        items.insert(0, item)
        if len(items) > MAX_INBOX_ITEMS:
            items = items[:MAX_INBOX_ITEMS]
            
        _save_inbox(items)
        return item

def get_inbox_items() -> List[Dict[str, Any]]:
    with _lock:
        items = _load_inbox()
        summaries = []
        for it in items:
            c = dict(it)
            if 'analysis' in c:
                del c['analysis']
            summaries.append(c)
        return summaries

def get_inbox_item(inbox_id: str) -> Optional[Dict[str, Any]]:
    with _lock:
        items = _load_inbox()
        for it in items:
            if it.get('id') == inbox_id:
                return it
        return None

def mark_reviewed(inbox_id: str, reviewed: bool = True) -> bool:
    with _lock:
        items = _load_inbox()
        found = False
        for it in items:
            if it.get('id') == inbox_id:
                it['reviewed'] = reviewed
                found = True
                break
        if found:
            _save_inbox(items)
        return found

def remove_inbox_item(inbox_id: str) -> bool:
    with _lock:
        items = _load_inbox()
        original_len = len(items)
        items = [it for it in items if it.get('id') != inbox_id]
        if len(items) != original_len:
            _save_inbox(items)
            return True
        return False

def save_inbox_item(inbox_id: str, analyst_label: Optional[str] = None) -> Tuple[Optional[Dict[str, Any]], bool]:
    with _lock:
        items = _load_inbox()
        target = None
        for it in items:
            if it.get('id') == inbox_id:
                target = it
                break
        if not target:
            return None, False
            
        from app.storage import save_analysis_record
        saved_copy, is_dup = save_analysis_record(target.get('analysis', {}), analyst_label)
        
        target['saved_case_id'] = saved_copy.get('case_id')
        target['reviewed'] = True
        _save_inbox(items)
        return saved_copy, is_dup

def reset_inbox():
    with _lock:
        _save_inbox([])
