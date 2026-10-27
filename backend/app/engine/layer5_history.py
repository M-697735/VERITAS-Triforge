import json
import os
import networkx as nx
from typing import Dict, Any, List
from app.engine.status_taxonomy import evaluate_layer5_status

HISTORY_DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'seeded_history.json')

def get_history_cases() -> List[Dict[str, Any]]:
    """
    Returns historical cases combining static seeded history and 
    dynamically learned analyst-saved cases from persistent storage.
    """
    seeded = []
    if os.path.exists(HISTORY_DB_PATH):
        try:
            with open(HISTORY_DB_PATH, 'r', encoding='utf-8') as f:
                seeded = json.load(f)
        except Exception:
            seeded = []
            
    # Dynamically load saved analyst cases from persistent storage
    try:
        from app.storage import _load_persistent_data
        _, saved_cases = _load_persistent_data()
    except Exception:
        saved_cases = []
        
    combined = list(seeded)
    for c in saved_cases:
        cid = c.get("case_id")
        if not cid:
            continue
        if any(item.get("case_id") == cid for item in combined):
            continue
            
        ip = c.get("originating_ip") or c.get("ip") or c.get("layer4", {}).get("originating_ip")
        domain = c.get("from_domain") or c.get("domain") or c.get("layer1", {}).get("from_domain")
        reply_to = c.get("reply_to_domain") or c.get("layer1", {}).get("reply_to_domain")
        asn = c.get("asn") or c.get("layer4", {}).get("asn")
        status = c.get("analyst_label") or c.get("status") or c.get("label") or "CONFIRMED_FRAUD"
        title = c.get("title") or c.get("email_meta", {}).get("subject") or f"Saved Case {cid}"
        
        combined.append({
            "case_id": cid,
            "title": title,
            "ip": ip,
            "domain": domain,
            "reply_to_domain": reply_to,
            "asn": asn,
            "status": status,
            "is_saved_analyst_case": True
        })
        
    return combined

def analyze_layer5(parsed_eml: Dict[str, Any], layer1_out: Dict[str, Any], layer4_out: Dict[str, Any]) -> Dict[str, Any]:
    cases = get_history_cases()
    
    current_ip = layer4_out.get("originating_ip", "")
    current_domain = layer1_out.get("from_domain", "")
    current_reply_domain = layer1_out.get("reply_to_domain", "")
    current_asn = layer4_out.get("asn", "")
    
    # Build NetworkX Graph
    G = nx.Graph()
    
    # Always add current email node at center
    current_node_id = "CURRENT_EMAIL"
    
    matched_case_ids = []
    has_fraud_match = False
    has_suspicious_match = False
    
    # Match against historical cases
    matched_cases_list = []
    for case in cases:
        case_id = case.get("case_id")
        case_ip = case.get("ip")
        case_domain = case.get("domain")
        case_reply_domain = case.get("reply_to_domain")
        case_status = case.get("status")
        
        is_ip_match = bool(current_ip and case_ip and case_ip == current_ip)
        is_dom_match = bool(current_domain and case_domain and case_domain == current_domain)
        is_reply_dom_match = bool(
            (current_reply_domain and case_reply_domain and case_reply_domain == current_reply_domain) or
            (current_reply_domain and case_domain and case_domain == current_reply_domain) or
            (current_domain and case_reply_domain and case_reply_domain == current_domain)
        )
        
        if is_ip_match or is_dom_match or is_reply_dom_match:
            matched_case_ids.append(case_id)
            matched_cases_list.append((case, is_ip_match, is_dom_match, is_reply_dom_match))
            if case_status == "CONFIRMED_FRAUD":
                has_fraud_match = True
            elif case_status == "SUSPICIOUS":
                has_suspicious_match = True

    cluster_match = (len(matched_case_ids) > 0)

    if not cluster_match:
        # Honest Isolated Node (No Cluster Match) — Zero fake nodes fabricated!
        G.add_node(current_node_id, label="Submitted Email (Isolated — No Historical Cluster Match)", type="current_email", status="ISOLATED")
    else:
        G.add_node(current_node_id, label="Submitted Email (Cluster Connected)", type="current_email", status="CONNECTED")
        
        if current_ip:
            G.add_node(f"IP:{current_ip}", label=f"IP: {current_ip}", type="indicator_ip")
            G.add_edge(current_node_id, f"IP:{current_ip}", relationship="sent_from_ip")
            
        if current_domain:
            G.add_node(f"DOM:{current_domain}", label=f"Domain: {current_domain}", type="indicator_domain")
            G.add_edge(current_node_id, f"DOM:{current_domain}", relationship="uses_domain")
            
        if current_reply_domain and current_reply_domain != current_domain:
            G.add_node(f"DOM:{current_reply_domain}", label=f"Reply Domain: {current_reply_domain}", type="indicator_domain")
            G.add_edge(current_node_id, f"DOM:{current_reply_domain}", relationship="reply_to_domain")

        for case, is_ip_match, is_dom_match, is_reply_dom_match in matched_cases_list:
            case_id = case.get("case_id")
            case_title = case.get("title")
            case_status = case.get("status")
            case_ip = case.get("ip")
            case_domain = case.get("domain")
            case_reply_dom = case.get("reply_to_domain")
            
            G.add_node(case_id, label=f"{case_id}: {case_title}", type="historical_case", status=case_status)
            
            if is_ip_match:
                G.add_node(f"IP:{case_ip}", label=f"IP: {case_ip}", type="indicator_ip")
                G.add_edge(case_id, f"IP:{case_ip}", relationship="Shared IP")
            if is_dom_match:
                G.add_node(f"DOM:{case_domain}", label=f"Domain: {case_domain}", type="indicator_domain")
                G.add_edge(case_id, f"DOM:{case_domain}", relationship="Shared Domain")
            if is_reply_dom_match:
                match_dom = case_reply_dom if (case_reply_dom and case_reply_dom in (current_domain, current_reply_domain)) else case_domain
                if match_dom:
                    G.add_node(f"DOM:{match_dom}", label=f"Domain: {match_dom}", type="indicator_domain")
                    G.add_edge(case_id, f"DOM:{match_dom}", relationship="Shared Reply Domain")
                
    # Format Subgraph Nodes & Edges for Frontend
    nodes_list = []
    for n, attr in G.nodes(data=True):
        nodes_list.append({
            "id": n,
            "label": attr.get("label", n),
            "type": attr.get("type", "node"),
            "status": attr.get("status", "NORMAL")
        })
        
    edges_list = []
    for u, v, attr in G.edges(data=True):
        edges_list.append({
            "source": u,
            "target": v,
            "relationship": attr.get("relationship", "connected")
        })
        
    # Central Status Taxonomy Evaluation
    status = evaluate_layer5_status(cluster_match, has_fraud_match, has_suspicious_match)
    
    if has_fraud_match:
        summary = f"Historical Correlation Warning: Matched prior fraud case cluster ({', '.join(matched_case_ids)})."
    elif has_suspicious_match:
        summary = f"Historical Correlation: Matched a SUSPICIOUS prior case ({', '.join(matched_case_ids)})."
    elif cluster_match:
        summary = f"Historical Correlation: Matched clean historical business record ({', '.join(matched_case_ids)})."
    else:
        summary = "No prior historical case cluster match detected (Isolated new email)."
        
    return {
        "cluster_match": cluster_match,
        "matched_case_ids": matched_case_ids,
        "subgraph_nodes": nodes_list,
        "subgraph_edges": edges_list,
        "status": status,
        "summary": summary,
        "details": {
            "has_fraud_match": has_fraud_match,
            "has_suspicious_match": has_suspicious_match,
            "total_nodes_in_subgraph": len(nodes_list)
        }
    }
