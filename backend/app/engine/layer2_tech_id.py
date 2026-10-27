import re
from typing import Dict, Any, Optional, Tuple

MULTI_PART_TLDS = {
    "co.uk", "org.uk", "gov.uk", "ac.uk",
    "co.in", "net.in", "org.in", "gen.in", "firm.in",
    "com.au", "net.au", "org.au", "edu.au",
    "co.nz", "net.nz", "org.nz", "com.br", "co.jp"
}

def get_organizational_domain(domain: str) -> str:
    if not domain:
        return ""
    parts = domain.lower().strip(".").split(".")
    if len(parts) <= 2:
        return domain.lower().strip(".")
    two_label = f"{parts[-2]}.{parts[-1]}"
    if two_label in MULTI_PART_TLDS and len(parts) >= 3:
        return f"{parts[-3]}.{two_label}"
    return f"{parts[-2]}.{parts[-1]}"

def is_relaxed_domain_aligned(d1: str, d2: str) -> bool:
    if not d1 or not d2:
        return False
    d1_clean = d1.lower().strip(".")
    d2_clean = d2.lower().strip(".")
    if d1_clean == d2_clean:
        return True
    return get_organizational_domain(d1_clean) == get_organizational_domain(d2_clean)

from app.engine.status_taxonomy import evaluate_layer2_status

def live_verify_dkim(raw_bytes: bytes) -> Tuple[Any, str]:
    """Safely verifies DKIM signature against live DNS public key with timeout."""
    try:
        import dkim
        verified = dkim.verify(raw_bytes)
        return verified, "Re-verified via live DNS DKIM key" if verified else "Live DKIM verification failed against DNS public key"
    except Exception as e:
        return None, f"Live DKIM lookup could not complete ({type(e).__name__})"

def live_verify_spf(from_domain: str, originating_ip: Optional[str]) -> Tuple[Any, str]:
    """Queries live SPF TXT record via dnspython with short timeout."""
    if not from_domain:
        return None, "No domain provided for live SPF lookup"
    try:
        import dns.resolver
        resolver = dns.resolver.Resolver()
        resolver.lifetime = 2.5
        resolver.timeout = 2.0
        answers = resolver.resolve(from_domain, "TXT")
        for rdata in answers:
            txt_str = "".join([part.decode("utf-8", errors="replace") if isinstance(part, bytes) else str(part) for part in rdata.strings])
            if txt_str.startswith("v=spf1"):
                return txt_str, f"Live SPF record found: {txt_str[:60]}..."
        return None, "No v=spf1 TXT record found on domain"
    except Exception as e:
        return None, f"Live SPF lookup failed ({type(e).__name__})"

def analyze_layer2(parsed_eml: Dict[str, Any], live_reverify: bool = False) -> Dict[str, Any]:
    auth_header = parsed_eml.get("auth_results", "")
    from_domain = parsed_eml.get("from_domain", "")
    auth_details = parsed_eml.get("auth_details", {})
    authserv_id = auth_details.get("authserv_id")
    raw_bytes = parsed_eml.get("raw_bytes", b"")
    originating_ip = parsed_eml.get("originating_ip")
    
    spf_result = "none"
    dkim_result = "none"
    dmarc_result = "none"
    dkim_signing_domain = None
    
    if auth_header:
        # Parse SPF result
        spf_match = re.search(r'spf=(pass|fail|softfail|none|neutral)', auth_header, re.IGNORECASE)
        if spf_match:
            spf_result = spf_match.group(1).lower()
            
        # Parse DKIM result
        dkim_match = re.search(r'dkim=(pass|fail|none|neutral)', auth_header, re.IGNORECASE)
        if dkim_match:
            dkim_result = dkim_match.group(1).lower()
            
        # Parse DKIM signing domain header.d=... or d=...
        domain_match = re.search(r'header\.d=([a-zA-Z0-9.-]+)', auth_header, re.IGNORECASE)
        if not domain_match:
            domain_match = re.search(r'd=([a-zA-Z0-9.-]+)', auth_header, re.IGNORECASE)
        if domain_match:
            dkim_signing_domain = domain_match.group(1).lower()
            
        # Parse DMARC result
        dmarc_match = re.search(r'dmarc=(pass|fail|none)', auth_header, re.IGNORECASE)
        if dmarc_match:
            dmarc_result = dmarc_match.group(1).lower()

    # Fallback to direct DKIM-Signature header if not present in Authentication-Results
    dkim_sig = parsed_eml.get("dkim_signature", "")
    if not dkim_signing_domain and dkim_sig:
        sig_match = re.search(r'\bd=([a-zA-Z0-9.-]+)', dkim_sig, re.IGNORECASE)
        if sig_match:
            dkim_signing_domain = sig_match.group(1).lower()
        if dkim_result == "none":
            dkim_result = "pass"
            
    # Relaxed Domain Alignment check (organizational domain)
    domain_aligned = False
    if dkim_result == "pass" and dkim_signing_domain:
        domain_aligned = is_relaxed_domain_aligned(dkim_signing_domain, from_domain)
        
    # Central Status Taxonomy Evaluation
    status = evaluate_layer2_status(spf_result, dkim_result, dmarc_result, domain_aligned)
    
    summary_notes = []
    if status == "VERIFIED":
        summary_notes.append("Technical authentication verified with relaxed DKIM domain alignment.")
    elif status == "PROBABLE":
        if dkim_result == "pass" and not domain_aligned:
            summary_notes.append(f"DKIM passed, but signing domain ({dkim_signing_domain}) differs from visible From domain ({from_domain}).")
        else:
            summary_notes.append("SPF/DKIM partially passed, but complete alignment is unconfirmed.")
    else:
        summary_notes.append("Technical authentication failed or headers unverified.")

    # Gateway assertion label
    if authserv_id:
        gateway_assertion_note = f"Results are as asserted by {authserv_id}; not re-verified offline."
    else:
        gateway_assertion_note = "Results are as asserted by the receiving gateway's Authentication-Results header; not re-verified offline."

    # Live Mode Execution (Opt-In Only)
    live_dkim_res = None
    live_dkim_note = None
    live_spf_rec = None
    live_spf_note = None
    
    if live_reverify:
        live_reverify_used = True
        live_reverify_label = "LIVE: network lookups"
        
        # 1. Live DKIM Re-verification
        if raw_bytes and (dkim_sig or dkim_result == "pass"):
            live_dkim_res, live_dkim_note = live_verify_dkim(raw_bytes)
            if live_dkim_res is True:
                summary_notes.append("LIVE RE-VERIFY: DKIM signature cryptographic validation PASSED via live DNS.")
            elif live_dkim_res is False:
                summary_notes.append("LIVE DISAGREEMENT: Cryptographic DKIM verification FAILED against live DNS public key.")
                
        # 2. Live SPF Check
        live_spf_rec, live_spf_note = live_verify_spf(from_domain, originating_ip)
        if live_spf_rec:
            summary_notes.append(f"LIVE SPF: DNS record fetched for {from_domain}.")
    else:
        live_reverify_used = False
        live_reverify_label = "Live DNS verification is disabled in offline mode"
        
    summary = f"SPF: {spf_result.upper()} | DKIM: {dkim_result.upper()} ({dkim_signing_domain or 'none'}) | Alignment: {'ALIGNED' if domain_aligned else 'MISALIGNED'}"
    
    return {
        "spf_result": spf_result,
        "dkim_result": dkim_result,
        "dkim_signing_domain": dkim_signing_domain,
        "dmarc_result": dmarc_result,
        "domain_aligned": domain_aligned,
        "status": status,
        "summary": summary,
        "details": {
            "auth_header_raw": auth_header,
            "status_notes": summary_notes,
            "live_reverify_used": live_reverify_used,
            "live_reverify_note": live_reverify_label,
            "gateway_assertion_note": gateway_assertion_note,
            "live_dkim_verified": live_dkim_res,
            "live_dkim_note": live_dkim_note,
            "live_spf_record": live_spf_rec,
            "live_spf_note": live_spf_note
        }
    }
