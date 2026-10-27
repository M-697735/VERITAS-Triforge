import re
from typing import Dict, Any
from app.engine.status_taxonomy import evaluate_layer1_status

LOCATION_PATTERNS = [
    (r'\b(redmond|chicago|new york|washington|seattle|san francisco|austin|dallas|boston|miami|usa|united states)\b', 'United States'),
    (r'\b(mumbai|maharashtra|delhi|bangalore|bengaluru|pune|hyderabad|india)\b', 'India'),
    (r'\b(amsterdam|rotterdam|netherlands|holland)\b', 'Netherlands'),
    (r'\b(london|manchester|birmingham|united kingdom|england)\b', 'United Kingdom'),
    (r'\b(bucharest|romania)\b', 'Romania'),
    (r'\b(frankfurt|berlin|munich|germany)\b', 'Germany'),
]

ROLE_PATTERNS = [
    (r'\b(CEO|Chief Executive Officer)\b', 'Chief Executive Officer (CEO)'),
    (r'\b(CFO|Chief Financial Officer)\b', 'Chief Financial Officer (CFO)'),
    (r'\b(Accounts Payable|Finance Team|Billing)\b', 'Accounts Payable / Finance'),
    (r'\b(Financial Controller|Controller)\b', 'Financial Controller'),
    (r'\b(HR|Human Resources)\b', 'Human Resources'),
    (r'\b(Architect|Lead Architect)\b', 'Lead Architect'),
]

ORG_PATTERNS = [
    (r'\b(Microsoft|M365|Office 365)\b', 'Microsoft'),
    (r'\b(Acme Corporation|Acme Corp|Acme)\b', 'Acme Corporation'),
    (r'\b(Globex Corporation|Globex Corp|Globex)\b', 'Globex Corporation'),
    (r'\b(Trusted Vendor|Trusted Vendor Solutions)\b', 'Trusted Vendor Solutions'),
    (r'\b(TechFirm|TechFirm Systems)\b', 'TechFirm Systems'),
]

def analyze_layer1(parsed_eml: Dict[str, Any]) -> Dict[str, Any]:
    from_name = parsed_eml.get("from_name", "")
    from_addr = parsed_eml.get("from_addr", "")
    from_domain = parsed_eml.get("from_domain", "")
    reply_addr = parsed_eml.get("reply_addr", "")
    reply_to_domain = parsed_eml.get("reply_to_domain", "")
    sig_block = parsed_eml.get("signature_block", "")
    full_text = f"{from_name} {sig_block}"
    
    # Claimed Role
    claimed_role = None
    for pattern, role_name in ROLE_PATTERNS:
        if re.search(pattern, full_text, re.IGNORECASE):
            claimed_role = role_name
            break
            
    # Claimed Org
    claimed_org = None
    for pattern, org_name in ORG_PATTERNS:
        if re.search(pattern, full_text, re.IGNORECASE):
            claimed_org = org_name
            break
            
    if not claimed_org and from_domain:
        claimed_org = from_domain.split(".")[0].capitalize()
        
    # Claimed Location String & Country
    claimed_location_full = None
    claimed_location_country = None
    
    lines = sig_block.split("\n")
    for line in reversed(lines):
        line_clean = line.strip()
        if not line_clean:
            continue
        line_lower = line_clean.lower()
        for pattern, country_name in LOCATION_PATTERNS:
            if re.search(pattern, line_lower, re.IGNORECASE):
                claimed_location_full = line_clean
                claimed_location_country = country_name
                break
        if claimed_location_country:
            break
            
    # Debug log for signature block parsing
    print(f"[DEBUG Layer 1] From: '{from_addr}' | Sig Snippet: {repr(sig_block[:100])}")
    print(f"[DEBUG Layer 1] Location Full: '{claimed_location_full}' | Country: '{claimed_location_country}'")

            
    # Central Status Taxonomy Evaluation
    status = evaluate_layer1_status(from_domain, reply_to_domain, claimed_org, claimed_role)
    
    status_notes = []
    if from_domain != reply_to_domain:
        status_notes.append(f"From domain ({from_domain}) differs from Reply-To domain ({reply_to_domain}).")
    elif "micros0ft" in from_domain or "g00gle" in from_domain:
        status_notes.append("Display domain appears to be a typosquatted brand name.")
    elif not claimed_role and not claimed_org:
        status_notes.append("No explicit organizational role extracted from signature.")
    else:
        status_notes.append("Claimed identity structure is clear and self-consistent.")
        
    summary = f"Claimed Identity: {claimed_role or 'Individual'} at {claimed_org or from_domain} ({claimed_location_country or 'Unspecified Location'})."
    
    return {
        "claimed_org": claimed_org,
        "claimed_role": claimed_role,
        "claimed_location_country": claimed_location_country,
        "claimed_location_full": claimed_location_full,
        "from_display_name": from_name,
        "from_address": from_addr,
        "from_domain": from_domain,
        "reply_to_address": reply_addr,
        "reply_to_domain": reply_to_domain,
        "return_path_address": parsed_eml.get("return_addr", ""),
        "status": status,
        "summary": summary,
        "details": {
            "from_header": parsed_eml.get("from_header", ""),
            "reply_to_header": parsed_eml.get("reply_to_header", ""),
            "status_notes": status_notes,
            "signature_block_snippet": sig_block[:200]
        }
    }
