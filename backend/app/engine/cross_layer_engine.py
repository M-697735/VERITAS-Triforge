from typing import Dict, Any, List
from app.models.schemas import ContradictionItem, VerdictOutput

def evaluate_cross_layer_consistency(
    layer1: Dict[str, Any],
    layer2: Dict[str, Any],
    layer3: Dict[str, Any],
    layer4: Dict[str, Any],
    layer5: Dict[str, Any]
) -> Dict[str, Any]:
    contradictions: List[ContradictionItem] = []
    
    # Extract needed fields
    claimed_country = layer1.get("claimed_location_country")
    from_domain = layer1.get("from_domain", "")
    reply_to_domain = layer1.get("reply_to_domain", "")
    
    spf_result = layer2.get("spf_result", "none")
    dkim_result = layer2.get("dkim_result", "none")
    dkim_signing_domain = layer2.get("dkim_signing_domain")
    layer2_status = layer2.get("status", "UNCERTAIN")
    
    l3_classification = layer3.get("classification", "legitimate")
    
    geolocated_country = layer4.get("country", "")
    radius = layer4.get("accuracy_radius_km", 50)
    is_datacenter = layer4.get("is_datacenter", False)
    infra_category = layer4.get("infra_category", "residential_isp")
    domain_age_days = layer4.get("domain_age_days", 365)
    
    l5_cluster_match = layer5.get("cluster_match", False)
    l5_has_fraud_match = layer5.get("details", {}).get("has_fraud_match", False)
    matched_case_ids = layer5.get("matched_case_ids", [])
    
    # --- RULE C1: Geographic Identity Mismatch ---
    if claimed_country and geolocated_country and (claimed_country.lower() != geolocated_country.lower()):
        c1_norm = claimed_country.lower().replace("usa", "united states")
        g1_norm = geolocated_country.lower().replace("usa", "united states")
        if c1_norm != g1_norm:
            radius_str = f", ±{radius}km" if radius is not None else ""
            contradictions.append(ContradictionItem(
                rule_id="C1",
                title="Geographic Identity Mismatch",
                description=f"Claimed sender location ({claimed_country}) does not match the geolocated origin of the sending infrastructure ({geolocated_country}{radius_str}).",
                layers_compared=["Layer 1: Claimed Identity", "Layer 4: Infrastructure"],
                severity="HIGH"
            ))
            
    # --- RULE C2: Domain/Identity Spoofing ---
    domain_aligned = layer2.get("domain_aligned", False)
    sub_a = (dkim_result == "pass" and dkim_signing_domain and not domain_aligned)
    sub_b = (from_domain and reply_to_domain and from_domain != reply_to_domain)
    
    if sub_a or sub_b:
        sub_details = []
        if sub_a:
            sub_details.append(f"DKIM signing domain ({dkim_signing_domain}) does not align with visible From domain ({from_domain})")
        if sub_b:
            sub_details.append(f"From domain ({from_domain}) differs from Reply-To domain ({reply_to_domain})")
            
        contradictions.append(ContradictionItem(
            rule_id="C2",
            title="Domain & Identity Spoofing",
            description=f"The visible sender identity does not match its own supporting infrastructure ({'; '.join(sub_details)}).",
            layers_compared=["Layer 1: Claimed Identity", "Layer 2: Technical Identity"],
            severity="HIGH"
        ))
        
    # --- RULE C3: Legitimate-Looking Content from Throwaway Infrastructure ---
    # domain_age_days is None never triggers or suppresses C3
    if l3_classification == "legitimate" and domain_age_days is not None and domain_age_days < 30:
        contradictions.append(ContradictionItem(
            rule_id="C3",
            title="Throwaway Domain with Business Content",
            description=f"Content reads as ordinary business correspondence, but the sending domain was registered only {domain_age_days} days ago.",
            layers_compared=["Layer 3: Content & Intent", "Layer 4: Infrastructure"],
            severity="HIGH"
        ))
        
    # --- RULE C4: Authenticated Sender Matches Historical Fraud Cluster ---
    # Strictly requires l5_has_fraud_match == True (prior fraud case match)
    if layer2_status == "VERIFIED" and l5_has_fraud_match:
        cases_str = ", ".join(matched_case_ids) if matched_case_ids else "prior incident database"
        contradictions.append(ContradictionItem(
            rule_id="C4",
            title="Authenticated Sender Matches Historical Fraud Cluster",
            description=f"This sender passes full technical authentication, but its infrastructure is directly linked to prior case(s) {cases_str}.",
            layers_compared=["Layer 2: Technical Identity", "Layer 5: Historical Pattern"],
            severity="HIGH"
        ))
        
    # --- RULE C5: High-Risk Content from Anonymized/Datacenter Infrastructure ---
    if l3_classification in ["phishing", "bec_pattern"] and is_datacenter and infra_category != "major_mail_provider":
        contradictions.append(ContradictionItem(
            rule_id="C5",
            title="High-Risk Content from Datacenter Infrastructure",
            description="High-risk content (urgency/payment/credential request) originates from hosting/datacenter infrastructure rather than typical residential/corporate mail infrastructure.",
            layers_compared=["Layer 3: Content & Intent", "Layer 4: Infrastructure"],
            severity="HIGH"
        ))
        
    # --- RULE C6: Anonymized Origin Despite Otherwise-Clean Identity ---
    c1_c5_fired = any(c.rule_id in ["C1", "C2", "C3", "C4", "C5"] for c in contradictions)
    if infra_category == "vpn_exit" and layer2_status == "VERIFIED" and not c1_c5_fired:
        contradictions.append(ContradictionItem(
            rule_id="C6",
            title="Anonymized Origin (VPN Routing)",
            description="Sender identity and authentication check out, but the email was routed through an anonymizing VPN exit node, so the true origin cannot be confirmed.",
            layers_compared=["Layer 1 & 2: Identity & Auth", "Layer 4: Infrastructure"],
            severity="MEDIUM"
        ))

    # --- VERDICT DETERMINATION LOGIC ---
    driving_rule_ids = [c.rule_id for c in contradictions]
    c_count = len(contradictions)
    has_critical_rule = any(rid in ["C1", "C2", "C4", "C5"] for rid in driving_rule_ids)
    
    verdict_label = "Likely Legitimate"
    confidence = "HIGH"
    summary = "No cross-layer contradictions detected. All evidence layers corroborate sender identity."
    
    if c_count >= 2 or (has_critical_rule and layer2_status == "UNCERTAIN"):
        verdict_label = "Likely Fraudulent"
        confidence = "HIGH"
        summary = f"Flagged as Fraudulent due to {c_count} cross-layer contradictions ({', '.join(driving_rule_ids)})."
    elif c_count == 1:
        if "C6" in driving_rule_ids:
            verdict_label = "Needs Review"
            confidence = "MEDIUM"
            summary = "Flagged for manual review due to anonymized VPN exit node infrastructure."
        else:
            verdict_label = "Needs Review"
            confidence = "MEDIUM"
            summary = f"Flagged for manual review due to cross-layer contradiction {driving_rule_ids[0]}."
    elif layer2_status == "UNCERTAIN" or l3_classification in ["phishing", "bec_pattern"]:
        verdict_label = "Needs Review"
        confidence = "MEDIUM"
        summary = "Individual layer warnings detected (Technical authentication or Content risk)."

    verdict_out = VerdictOutput(
        verdict=verdict_label,
        confidence=confidence,
        driving_rule_ids=driving_rule_ids,
        summary=summary
    )
    
    return {
        "contradictions": contradictions,
        "verdict": verdict_out
    }
