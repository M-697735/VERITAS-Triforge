from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class LayerStatusEnum:
    VERIFIED = "VERIFIED"
    PROBABLE = "PROBABLE"
    UNCERTAIN = "UNCERTAIN"

class Layer1Output(BaseModel):
    claimed_org: Optional[str] = None
    claimed_role: Optional[str] = None
    claimed_location_country: Optional[str] = None
    claimed_location_full: Optional[str] = None
    from_display_name: str
    from_address: str
    from_domain: str
    reply_to_address: str
    reply_to_domain: str
    return_path_address: str
    status: str  # VERIFIED | PROBABLE | UNCERTAIN
    summary: str
    details: Dict[str, Any]

class Layer2Output(BaseModel):
    spf_result: str  # pass | fail | softfail | none
    dkim_result: str  # pass | fail | none
    dkim_signing_domain: Optional[str] = None
    dmarc_result: str  # pass | fail | none
    domain_aligned: bool
    status: str  # VERIFIED | PROBABLE | UNCERTAIN
    summary: str
    details: Dict[str, Any]

class Layer3Output(BaseModel):
    classification: str  # legitimate | suspicious | phishing | bec_pattern
    triggering_phrases: List[str]
    model_type: str = "Baseline TF-IDF + logistic regression on synthetic template data (demo only)"
    status: str  # VERIFIED | PROBABLE | UNCERTAIN
    summary: str
    details: Dict[str, Any]

class Layer4Output(BaseModel):
    originating_ip: Optional[str] = None
    city: str
    country: str
    accuracy_radius_km: Optional[int] = None
    asn: str
    asn_org: str
    is_datacenter: bool
    infra_category: str  # residential_isp | hosting_datacenter | vpn_exit | no_origin_ip | unresolved_origin
    from_domain: str
    domain_age_days: Optional[int] = None
    registrar: str
    status: str  # VERIFIED | PROBABLE | UNCERTAIN
    summary: str
    details: Dict[str, Any]

class GraphNode(BaseModel):
    id: str
    label: str
    type: str  # current_email | historical_case | indicator_ip | indicator_domain | indicator_asn

class GraphEdge(BaseModel):
    source: str
    target: str
    relationship: str

class Layer5Output(BaseModel):
    cluster_match: bool
    matched_case_ids: List[str]
    subgraph_nodes: List[GraphNode]
    subgraph_edges: List[GraphEdge]
    status: str  # VERIFIED | PROBABLE | UNCERTAIN
    summary: str
    details: Dict[str, Any]

class ContradictionItem(BaseModel):
    rule_id: str  # C1, C2, C3, C4, C5, C6
    title: str
    description: str
    layers_compared: List[str]
    severity: str  # HIGH | MEDIUM | LOW

class VerdictOutput(BaseModel):
    verdict: str  # Likely Fraudulent | Needs Review | Likely Legitimate
    confidence: str  # HIGH | MEDIUM | LOW
    driving_rule_ids: List[str]
    summary: str

class EmailMeta(BaseModel):
    subject: str
    date: str
    from_header: str
    to_header: str
    reply_to_header: str
    message_id: str

class AnalysisResponse(BaseModel):
    sha256_hash: str
    email_meta: EmailMeta
    layer1: Layer1Output
    layer2: Layer2Output
    layer3: Layer3Output
    layer4: Layer4Output
    layer5: Layer5Output
    contradictions: List[ContradictionItem]
    verdict: VerdictOutput

class SampleItem(BaseModel):
    id: str
    name: str
    description: str
    expected_verdict: str
    expected_rule_ids: List[str]

class HistoryItem(BaseModel):
    id: str
    timestamp: str
    filename: str
    subject: str
    from_address: str
    verdict: str
    confidence: str
    contradictions_count: int
    sha256_hash: str
