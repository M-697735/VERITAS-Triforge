"""
VERITAS Status Taxonomy — Single Source of Truth for Evidence Layer Badges

Taxonomy Enum:
  - VERIFIED  : Highest confidence evidence; all layer checks pass and corroborate identity.
  - PROBABLE  : Mild uncertainty or unconfirmed optional attributes, but no explicit failure.
  - UNCERTAIN : Failed check, mismatched identity/infrastructure, high risk cue, or unresolved data.
"""

from typing import Dict, Any, Optional

class LayerStatus:
    VERIFIED = "VERIFIED"
    PROBABLE = "PROBABLE"
    UNCERTAIN = "UNCERTAIN"

def evaluate_layer1_status(
    from_domain: str,
    reply_to_domain: str,
    claimed_org: Optional[str],
    claimed_role: Optional[str]
) -> str:
    # Check domain mismatch or typosquatted brand
    if from_domain and reply_to_domain and (from_domain != reply_to_domain):
        return LayerStatus.UNCERTAIN
    if "micros0ft" in from_domain or "g00gle" in from_domain or "paypa1" in from_domain:
        return LayerStatus.UNCERTAIN
    if claimed_org or claimed_role:
        return LayerStatus.VERIFIED
    return LayerStatus.PROBABLE

def evaluate_layer2_status(
    spf_result: str,
    dkim_result: str,
    dmarc_result: str,
    domain_aligned: bool
) -> str:
    spf = (spf_result or "").lower()
    dkim = (dkim_result or "").lower()
    dmarc = (dmarc_result or "").lower()
    
    if spf == "fail" or dkim == "fail" or dmarc == "fail":
        return LayerStatus.UNCERTAIN
    if dkim == "pass" and spf == "pass" and dmarc == "pass" and domain_aligned:
        return LayerStatus.VERIFIED
    if dkim == "pass" or spf == "pass":
        # Passed technical auth but domain misaligned or partial dmarc/spf
        return LayerStatus.PROBABLE
    return LayerStatus.UNCERTAIN

def evaluate_layer3_status(classification: str) -> str:
    cls = (classification or "").lower()
    if cls == "legitimate":
        return LayerStatus.VERIFIED
    if cls == "suspicious":
        return LayerStatus.PROBABLE
    return LayerStatus.UNCERTAIN # phishing or bec_pattern

def evaluate_layer4_status(
    infra_category: str,
    is_datacenter: bool,
    domain_age_days: Optional[int],
    is_resolved: bool = True
) -> str:
    if not is_resolved or infra_category in ["unresolved_origin", "no_origin_ip"]:
        return LayerStatus.UNCERTAIN
    if infra_category == "major_mail_provider":
        if domain_age_days is not None and domain_age_days < 30:
            return LayerStatus.UNCERTAIN
        return LayerStatus.VERIFIED
    if infra_category in ["hosting_datacenter", "vpn_exit"] or is_datacenter:
        return LayerStatus.UNCERTAIN
    # A None age never counts as VERIFIED and never triggers or suppresses C3
    if domain_age_days is None:
        return LayerStatus.PROBABLE
    if domain_age_days < 30:
        return LayerStatus.UNCERTAIN
    if infra_category in ["residential_isp", "isp_network"] and domain_age_days >= 30 and not is_datacenter:
        return LayerStatus.VERIFIED
    return LayerStatus.PROBABLE

def evaluate_layer5_status(
    cluster_match: bool,
    has_fraud_match: bool,
    has_suspicious_match: bool = False
) -> str:
    if cluster_match and has_fraud_match:
        return LayerStatus.UNCERTAIN
    if cluster_match and has_suspicious_match:
        return LayerStatus.PROBABLE
    if cluster_match and not has_fraud_match and not has_suspicious_match:
        return LayerStatus.VERIFIED  # Every matched case is CLEARED (clean historical record)
    return LayerStatus.PROBABLE  # Isolated new indicator (no prior history)

