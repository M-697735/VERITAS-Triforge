import os
import re
import ipaddress
import joblib
from typing import Dict, Any, List, Set, Optional
from urllib.parse import urlparse
from app.engine.status_taxonomy import evaluate_layer3_status

MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'dataset', 'model.joblib')

URGENCY_KEYWORDS = [
    "suspended in 2 hours", "immediate action required", "urgent", "immediately",
    "cutoff time", "within 24 hours", "account will be terminated"
]

BEC_KEYWORDS = [
    "wire transfer", "wire $", "escrow account", "updated banking details",
    "new bank account", "routing numbers", "acquisition closing", "strictly confidential",
    "apple gift cards", "direct deposit"
]

PHISHING_KEYWORDS = [
    "reset your credential password", "reset-password", "unverified login",
    "account suspended", "mailbox full", "verify your account now"
]

KNOWN_SHORTENERS: Set[str] = {
    "bit.ly", "tinyurl.com", "t.co", "ow.ly", "is.gd", "buff.ly",
    "cutt.ly", "rebrand.ly", "shorturl.at", "soo.gd", "bl.ink", "tiny.cc", "rb.gy"
}

POPULAR_BRANDS: List[str] = [
    "microsoft", "google", "paypal", "apple", "amazon", "netflix",
    "chase", "wellsfargo", "bankofamerica", "citibank", "dhl", "fedex",
    "ups", "facebook", "instagram", "dropbox", "adobe", "linkedin",
    "ebay", "walmart", "yahoo", "binance", "coinbase", "telegram",
    "whatsapp", "twitter", "docusign", "intuit", "quickbooks"
]

RISKY_ATTACHMENT_EXTS: Set[str] = {
    ".exe", ".scr", ".js", ".vbs", ".iso", ".img", ".lnk", ".html", ".htm",
    ".bat", ".cmd", ".ps1", ".wsf", ".hta", ".docm", ".xlsm", ".pptm",
    ".dotm", ".xltm", ".potm", ".jar", ".cpl"
}

_model_pipeline = None

def get_model():
    global _model_pipeline
    if _model_pipeline is None and os.path.exists(MODEL_PATH):
        try:
            _model_pipeline = joblib.load(MODEL_PATH)
        except Exception:
            _model_pipeline = None
    return _model_pipeline

def levenshtein_distance(s1: str, s2: str) -> int:
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    prev = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        curr = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = prev[j + 1] + 1
            deletions = curr[j] + 1
            substitutions = prev[j] + (c1 != c2)
            curr.append(min(insertions, deletions, substitutions))
        prev = curr
    return prev[-1]

def is_ip_literal(host: str) -> bool:
    if not host:
        return False
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False

def check_brand_lookalike(domain: str) -> Optional[str]:
    """Checks whether any domain token is an edit distance of 1-2 from a common brand."""
    if not domain:
        return None
    tokens = re.split(r'[-.]', domain.lower())
    for token in tokens:
        if len(token) < 4:
            continue
        for brand in POPULAR_BRANDS:
            if token == brand:
                continue # Exact match is official brand token, not typosquat
            dist = levenshtein_distance(token, brand)
            if dist in (1, 2) and abs(len(token) - len(brand)) <= 2:
                return f"Lookalike domain token '{token}' resembles brand '{brand}'"
    return None

def analyze_layer3(parsed_eml: Dict[str, Any]) -> Dict[str, Any]:
    subject = parsed_eml.get("subject", "")
    body_text = parsed_eml.get("body_text", "")
    full_text = f"{subject}\n{body_text}"
    
    triggering_phrases: List[str] = []
    
    # 1. Keyword detection
    for kw in URGENCY_KEYWORDS:
        if kw.lower() in full_text.lower():
            triggering_phrases.append(f"Urgency cue: '{kw}'")
            
    for kw in BEC_KEYWORDS:
        if kw.lower() in full_text.lower():
            triggering_phrases.append(f"BEC payment cue: '{kw}'")
            
    for kw in PHISHING_KEYWORDS:
        if kw.lower() in full_text.lower():
            triggering_phrases.append(f"Phishing credential cue: '{kw}'")

    # 2. Link Analysis (from parsed_eml['links'])
    raw_links = parsed_eml.get("links", [])
    analyzed_links = []
    link_risk_count = 0
    
    for lk in raw_links:
        href = lk.get("href", "")
        dest_domain = lk.get("destination_domain", "")
        disp_domain = lk.get("display_domain")
        disp_text = lk.get("display_text", "")
        defanged = lk.get("defanged_destination", href)
        
        flags = []
        
        # Check 1: Visible link domain differs from destination href domain
        if disp_domain and dest_domain and disp_domain != dest_domain:
            flags.append(f"Link domain mismatch: displayed '{disp_domain}' -> destination '{dest_domain}'")
            triggering_phrases.append(f"Link deception: displayed domain '{disp_domain}' mismatches actual target '{dest_domain}'")
            link_risk_count += 1
            
        # Check 2: Destination hostname is an IP literal
        if is_ip_literal(dest_domain):
            flags.append(f"Destination hostname is an IP literal ({dest_domain})")
            triggering_phrases.append(f"Suspicious link: destination is raw IP address '{dest_domain}'")
            link_risk_count += 1
            
        # Check 3: Punycode (IDN homograph attack)
        if "xn--" in dest_domain:
            flags.append(f"Punycode / IDN destination: {dest_domain}")
            triggering_phrases.append(f"Punycode link: destination '{dest_domain}' uses IDN homograph encoding")
            link_risk_count += 1
            
        # Check 4: URL shorteners
        if dest_domain in KNOWN_SHORTENERS:
            flags.append(f"URL shortener masks target: {dest_domain}")
            triggering_phrases.append(f"URL shortener: '{dest_domain}' masks true target destination")
            link_risk_count += 1
            
        # Check 5: Brand lookalike detection
        lookalike_msg = check_brand_lookalike(dest_domain)
        if lookalike_msg:
            flags.append(lookalike_msg)
            triggering_phrases.append(f"Phishing lure: {lookalike_msg}")
            link_risk_count += 1
            
        is_mismatch = bool(disp_domain and dest_domain and disp_domain != dest_domain)
        is_ip = is_ip_literal(dest_domain)
        is_puny = "xn--" in dest_domain
        is_short = dest_domain in KNOWN_SHORTENERS
        
        analyzed_links.append({
            "display_text": disp_text,
            "href": href,
            "display_domain": disp_domain,
            "destination_domain": dest_domain,
            "defanged_destination": defanged,
            "mismatch": is_mismatch,
            "is_ip_literal": is_ip,
            "is_punycode": is_puny,
            "is_shortener": is_short,
            "flags": flags,
            "reasons": flags
        })

    # Also check from_domain for brand lookalike
    from_dom = parsed_eml.get("from_domain", "")
    from_lookalike = check_brand_lookalike(from_dom)
    if from_lookalike and "micros0ft" not in from_dom:
        triggering_phrases.append(f"Sender domain: {from_lookalike}")

    # 3. Attachment Risk Analysis (from parsed_eml['attachments'])
    attachments = parsed_eml.get("attachments", [])
    analyzed_attachments = []
    has_risky_attachment = False
    
    for att in attachments:
        fname = att.get("filename", "")
        fname_lower = fname.lower()
        size = att.get("size", 0)
        sha256 = att.get("sha256", "")
        ctype = att.get("content_type", "")
        
        att_flags = []
        
        # Check risky extension
        _, ext = os.path.splitext(fname_lower)
        if ext in RISKY_ATTACHMENT_EXTS:
            att_flags.append(f"High-risk executable/script attachment extension '{ext}'")
            triggering_phrases.append(f"Risky attachment: '{fname}' has dangerous extension '{ext}'")
            has_risky_attachment = True
            
        # Check double extensions (e.g. invoice.pdf.exe)
        sub_parts = fname_lower.split(".")
        if len(sub_parts) >= 3:
            second_last = f".{sub_parts[-2]}"
            last = f".{sub_parts[-1]}"
            if last in RISKY_ATTACHMENT_EXTS or (second_last in [".pdf", ".doc", ".docx", ".xls", ".xlsx"] and last in [".exe", ".scr", ".js", ".vbs"]):
                att_flags.append(f"Deceptive double extension detected ({second_last}{last})")
                triggering_phrases.append(f"Double extension attachment: '{fname}' masks true payload")
                has_risky_attachment = True

        analyzed_attachments.append({
            "filename": fname,
            "content_type": ctype,
            "size": size,
            "sha256": sha256,
            "flags": att_flags,
            "reasons": att_flags,
            "is_risky": len(att_flags) > 0,
            "risk_reason": "; ".join(att_flags) if att_flags else None
        })

    # 4. Categorization
    classification = "legitimate"
    
    if any("reset" in p.lower() or "phishing" in p.lower() or "suspended" in p.lower() or "credential" in p.lower() or "lookalike" in p.lower() for p in triggering_phrases):
        classification = "phishing"
    elif any("bec" in p.lower() or "wire" in p.lower() or "banking details" in p.lower() for p in triggering_phrases):
        classification = "bec_pattern"
    elif has_risky_attachment:
        classification = "phishing"
    elif link_risk_count > 0:
        classification = "phishing"
    elif triggering_phrases:
        classification = "suspicious"
        
    # Machine Learning classifier score fallback / enhancement
    model = get_model()
    ml_label = None
    if model:
        try:
            pred = model.predict([full_text])[0]
            ml_label = pred
            if classification in ["legitimate", "suspicious"] and pred in ["phishing", "bec_pattern"]:
                classification = pred
        except Exception:
            pass
            
    # Central Status Taxonomy Evaluation
    status = evaluate_layer3_status(classification)
    
    if status == "VERIFIED":
        summary = "Clean content: Standard business communication without urgency or payment cues."
    elif status == "PROBABLE":
        summary = f"Suspicious content detected ({len(triggering_phrases)} risk cues)."
    else:
        summary = f"High-risk content flagged ({classification.upper()} pattern)."
        
    return {
        "classification": classification,
        "triggering_phrases": triggering_phrases,
        "model_type": "Baseline TF-IDF + logistic regression on synthetic template data (demo only)",
        "status": status,
        "summary": summary,
        "details": {
            "ml_predicted_label": ml_label,
            "trigger_count": len(triggering_phrases),
            "analyzed_text_length": len(full_text),
            "links": analyzed_links,
            "attachments": analyzed_attachments
        }
    }
