import os
import json
import secrets
import datetime
from collections import OrderedDict
from typing import List, Dict, Any, Optional, Tuple

HISTORY_FILE = os.path.join(os.path.dirname(__file__), 'data', 'history.json')

# In-memory temporary cache (max 50, oldest evicted, lost on restart)
_temp_cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
MAX_TEMP_CACHE = 50

def _get_history_file() -> str:
    """Reads HISTORY_FILE dynamically at call time so test monkeypatching works."""
    return HISTORY_FILE

def _load_persistent_data() -> Tuple[int, List[Dict[str, Any]]]:
    """
    Loads saved cases and next_id from history.json.
    Handles missing, empty, or corrupt files by backing up corrupt files to history.json.bak.
    """
    path = _get_history_file()
    if not os.path.exists(path):
        return 1, []
        
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
            if not content.strip():
                return 1, []
            data = json.loads(content)
            if isinstance(data, dict):
                next_id = int(data.get("next_id", 1))
                cases = list(data.get("cases", []))
                return next_id, cases
            elif isinstance(data, list):
                # Backwards compatibility fallback if previously a list
                return len(data) + 1, data
            else:
                raise ValueError("Invalid format: expected object with next_id and cases")
    except Exception as e:
        # Corrupt file: rename to history.json.bak and start fresh
        bak_path = path + ".bak"
        try:
            if os.path.exists(path):
                if os.path.exists(bak_path):
                    os.remove(bak_path)
                os.rename(path, bak_path)
        except Exception:
            pass
        return 1, []

def _save_persistent_data(next_id: int, cases: List[Dict[str, Any]]):
    """
    Atomically writes {"next_id": N, "cases": [...]} using a temporary file and rename.
    """
    path = _get_history_file()
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp_path = path + f".tmp.{secrets.token_hex(4)}"
    
    payload = {
        "next_id": next_id,
        "cases": cases
    }
    
    with open(tmp_path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
        
    os.replace(tmp_path, path)

def store_transient_analysis(analysis_response: Dict[str, Any], filename: str = "uploaded_email.eml") -> Dict[str, Any]:
    """
    Stores an analysis in the transient in-memory cache with a random TMP-xxxxxxxx ID.
    Does NOT touch persistent history.
    """
    # 8 random uppercase hex characters
    tmp_id = f"TMP-{secrets.token_hex(4).upper()}"
    now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    analysis_response["case_id"] = tmp_id
    analysis_response["duplicate"] = False
    analysis_response["timestamp"] = now_utc
    analysis_response["filename"] = filename
    analysis_response["saved"] = False
    
    # Store in memory with eviction beyond 50
    if len(_temp_cache) >= MAX_TEMP_CACHE:
        _temp_cache.popitem(last=False)
        
    _temp_cache[tmp_id] = analysis_response
    return analysis_response

def save_analysis_record(source_analysis: Dict[str, Any], analyst_label: Optional[str] = None) -> Tuple[Dict[str, Any], bool]:
    """
    Saves an analysis payload into permanent history storage.
    Deduplicates by SHA-256. Returns (saved_record, is_duplicate).
    """
    next_id, saved_cases = _load_persistent_data()
    sha256 = source_analysis.get("sha256_hash", "")
    
    # Deduplication check against persistent storage
    if sha256:
        for c in saved_cases:
            if c.get("sha256_hash") == sha256:
                if analyst_label:
                    norm = _normalize_analyst_label(analyst_label, source_analysis)
                    c["analyst_label"] = norm
                    c["label"] = norm
                    _save_persistent_data(next_id, saved_cases)
                return c, True
                
    # Assign next persistent ID
    saved_id = f"CASE-{next_id:04d}"
    next_id += 1
    
    # Normalize analyst label
    norm_label = _normalize_analyst_label(analyst_label, source_analysis)

    # Create permanent copy of the full analysis
    full_copy = dict(source_analysis)
    full_copy["case_id"] = saved_id
    full_copy["saved"] = True
    full_copy["duplicate"] = False
    now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    full_copy["saved_at"] = now_utc
    full_copy["analyst_label"] = norm_label
    full_copy["label"] = norm_label
    
    # Store explicit indicators for Layer 5 NetworkX learning
    l4 = source_analysis.get("layer4", {})
    l1 = source_analysis.get("layer1", {})
    meta = source_analysis.get("email_meta", {})
    
    orig_ip = l4.get("originating_ip")
    from_dom = l1.get("from_domain")
    reply_dom = l1.get("reply_to_domain")
    asn = l4.get("asn")
    msg_id = meta.get("message_id", "")
    msg_id_domain = msg_id.split("@")[-1].rstrip(">") if "@" in msg_id else ""
    
    full_copy["originating_ip"] = orig_ip
    full_copy["from_domain"] = from_dom
    full_copy["reply_to_domain"] = reply_dom
    full_copy["asn"] = asn
    full_copy["message_id_domain"] = msg_id_domain
    full_copy["relevant_indicators"] = [
        ind for ind in [orig_ip, from_dom, reply_dom, asn, msg_id_domain] if ind
    ]
    
    # Insert newest at top
    saved_cases.insert(0, full_copy)
    _save_persistent_data(next_id, saved_cases)
    
    return full_copy, False

def save_case(case_id: str, analyst_label: Optional[str] = None) -> Tuple[Dict[str, Any], bool]:
    """
    Copies an analysis from the temporary cache into permanent storage.
    Deduplicates by SHA-256: if already saved, returns the existing saved case with duplicate=True.
    Returns (saved_full_analysis, is_duplicate).
    """
    next_id, saved_cases = _load_persistent_data()
    
    # If case_id is already a saved case, return it
    if case_id.startswith("CASE-"):
        existing = next((c for c in saved_cases if c.get("case_id") == case_id), None)
        if existing:
            if analyst_label:
                norm = _normalize_analyst_label(analyst_label)
                existing["analyst_label"] = norm
                existing["label"] = norm
                _save_persistent_data(next_id, saved_cases)
            return existing, True
            
    # Lookup in temporary cache
    if case_id not in _temp_cache:
        raise KeyError(f"Case ID '{case_id}' not found in active session cache.")
        
    source_analysis = _temp_cache[case_id]
    saved_copy, is_dup = save_analysis_record(source_analysis, analyst_label)
    
    # Update temporary cache entry to point to saved ID
    source_analysis["case_id"] = saved_copy["case_id"]
    source_analysis["saved"] = True
    source_analysis["analyst_label"] = saved_copy.get("analyst_label")
    source_analysis["label"] = saved_copy.get("label")
    
    return saved_copy, is_dup

def _normalize_analyst_label(analyst_label: Optional[str] = None, analysis_data: Optional[Dict[str, Any]] = None) -> str:
    if analyst_label:
        raw = analyst_label.strip().upper().replace(" ", "_")
        if "FRAUD" in raw:
            return "CONFIRMED_FRAUD"
        if "CLEAR" in raw or "LEGIT" in raw:
            return "CLEARED"
        if "SUSPICIOUS" in raw or "REVIEW" in raw:
            return "SUSPICIOUS"
        return raw
    if analysis_data:
        verdict = analysis_data.get("verdict", {}).get("verdict", "")
        if verdict == "Likely Fraudulent":
            return "CONFIRMED_FRAUD"
        if verdict == "Needs Review":
            return "SUSPICIOUS"
        if verdict == "Likely Legitimate":
            return "CLEARED"
    return "CONFIRMED_FRAUD"

def get_history_summaries() -> List[Dict[str, Any]]:
    """
    Returns summaries of only saved cases, newest first.
    """
    _, saved_cases = _load_persistent_data()
    summaries = []
    for c in saved_cases:
        cid = c.get("case_id", "")
        email_meta = c.get("email_meta", {})
        verdict = c.get("verdict", {})
        contradictions = c.get("contradictions", [])
        
        summaries.append({
            "id": cid,
            "case_id": cid,
            "timestamp": c.get("saved_at") or c.get("timestamp") or "",
            "filename": c.get("filename", "uploaded_email.eml"),
            "subject": email_meta.get("subject", "(No Subject)"),
            "from_address": email_meta.get("from_header", ""),
            "verdict": verdict.get("verdict", "Needs Review"),
            "confidence": verdict.get("confidence", "HIGH"),
            "contradictions_count": len(contradictions),
            "sha256_hash": c.get("sha256_hash", "")
        })
    return summaries

def get_case_analysis(case_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves full analysis for a given case_id.
    - If case_id starts with 'TMP-', checks ONLY the temporary in-memory cache.
    - If case_id starts with 'CASE-', checks ONLY persistent saved storage.
    Never cross-matches.
    """
    if not case_id:
        return None
        
    if case_id.startswith("TMP-"):
        return _temp_cache.get(case_id)
        
    if case_id.startswith("CASE-"):
        _, saved_cases = _load_persistent_data()
        for c in saved_cases:
            if c.get("case_id") == case_id:
                return c
        return None
        
    return None

def delete_saved_case(case_id: str) -> bool:
    """
    Deletes a single saved case from persistent storage.
    next_id is preserved so deleted IDs are never reused.
    """
    next_id, saved_cases = _load_persistent_data()
    original_len = len(saved_cases)
    saved_cases = [c for c in saved_cases if c.get("case_id") != case_id]
    
    if len(saved_cases) < original_len:
        _save_persistent_data(next_id, saved_cases)
        return True
    return False

def clear_all_saved_cases() -> bool:
    """
    Clears all saved cases from persistent storage.
    Preserves next_id.
    """
    next_id, _ = _load_persistent_data()
    _save_persistent_data(next_id, [])
    return True

def reset_history_file():
    """
    CLI / reset action: resets history.json to {"next_id": 1, "cases": []} and clears temp cache.
    """
    global _temp_cache
    _temp_cache.clear()
    _save_persistent_data(1, [])

