import os
import re
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from app.engine.eml_parser import parse_eml
from app.engine.layer1_claimed_id import analyze_layer1
from app.engine.layer2_tech_id import analyze_layer2
from app.engine.layer3_content_intent import analyze_layer3
from app.engine.layer4_infrastructure import analyze_layer4
from app.engine.layer5_history import analyze_layer5
from app.engine.cross_layer_engine import evaluate_cross_layer_consistency
from app.engine.pdf_generator import generate_forensic_pdf
from app.storage import (
    store_transient_analysis,
    save_case,
    get_history_summaries,
    get_case_analysis,
    delete_saved_case,
    clear_all_saved_cases
)
from app.ingest.dropfolder import DropfolderWatcher
from app.ingest.imap_watcher import ImapWatcher
from app.ingest.inbox_store import (
    get_inbox_items,
    get_inbox_item,
    mark_reviewed,
    remove_inbox_item,
    save_inbox_item
)

dropfolder_watcher = DropfolderWatcher()
imap_watcher = ImapWatcher()

@asynccontextmanager
async def lifespan(app: FastAPI):
    if not os.environ.get("DISABLE_WATCHERS"):
        dropfolder_watcher.start()
        if imap_watcher.is_configured():
            imap_watcher.start()
    yield
    dropfolder_watcher.stop()
    imap_watcher.stop()

app = FastAPI(
    title="VERITAS Email Forensics API",
    description="Multi-Layer Email Forensics Platform with Cross-Layer Contradiction Engine",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), 'data', 'sample_emails')

SAMPLES_META = [
    {
        "id": "sample-1",
        "filename": "01_clean_legitimate.eml",
        "name": "Sample 1: Clean Legitimate Corporate Email",
        "description": "Routine Q3 audit report from Sarah Jenkins (Acme Corp). All 5 layers agree.",
        "expected_verdict": "Likely Legitimate",
        "expected_rule_ids": []
    },
    {
        "id": "sample-2",
        "filename": "02_classic_phishing.eml",
        "name": "Sample 2: Classic Credential Phishing Lure",
        "description": "Microsoft 365 account suspension lure sent from Bucharest bulletproof hosting node.",
        "expected_verdict": "Likely Fraudulent",
        "expected_rule_ids": ["C1", "C5"]
    },
    {
        "id": "sample-3",
        "filename": "03_spoofed_bec.eml",
        "name": "Sample 3: Spoofed Executive Wire Transfer (BEC)",
        "description": "Urgent acquisition wire transfer claiming to be CEO, signed by misaligned domain.",
        "expected_verdict": "Likely Fraudulent",
        "expected_rule_ids": ["C1", "C2", "C5"]
    },
    {
        "id": "sample-4",
        "filename": "04_compromised_account.eml",
        "name": "Sample 4: Compromised Vendor Mailbox Account",
        "description": "Authentic DKIM-signed vendor email asking to update banking details, linked to historical fraud cluster.",
        "expected_verdict": "Likely Fraudulent",
        "expected_rule_ids": ["C4", "C5"]
    },
    {
        "id": "sample-5",
        "filename": "05_vpn_obscured.eml",
        "name": "Sample 5: VPN Obscured Origin Inquiry",
        "description": "Legitimate technical proposal routed through an anonymizing Mullvad VPN exit node.",
        "expected_verdict": "Needs Review",
        "expected_rule_ids": ["C6"]
    }
]

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

def run_analysis_pipeline(raw_bytes: bytes, filename: str = "uploaded_email.eml", live_reverify: bool = False) -> Dict[str, Any]:
    # 1. EML Parsing
    parsed = parse_eml(raw_bytes)
    
    # 2. 5 Evidence Layers Execution
    layer1 = analyze_layer1(parsed)
    layer2 = analyze_layer2(parsed, live_reverify=live_reverify)
    layer3 = analyze_layer3(parsed)
    layer4 = analyze_layer4(parsed, live_reverify=live_reverify)
    layer5 = analyze_layer5(parsed, layer1, layer4)
    
    # 3. Cross-Layer Contradiction Engine Execution
    cross_layer_res = evaluate_cross_layer_consistency(layer1, layer2, layer3, layer4, layer5)
    
    response_payload = {
        "sha256_hash": parsed["sha256_hash"],
        "is_forwarded_report": parsed.get("is_forwarded_report", False),
        "reported_by": parsed.get("reported_by"),
        "outer_report_meta": parsed.get("outer_report_meta"),
        "hops": parsed.get("hops", []),
        "email_meta": {
            "subject": parsed["subject"],
            "date": parsed["date"],
            "from_header": parsed["from_header"],
            "to_header": parsed.get("to_header", ""),
            "reply_to_header": parsed["reply_to_header"],
            "message_id": parsed["message_id"]
        },
        "layer1": layer1,
        "layer2": layer2,
        "layer3": layer3,
        "layer4": layer4,
        "layer5": layer5,
        "contradictions": [c.model_dump() for c in cross_layer_res["contradictions"]],
        "verdict": cross_layer_res["verdict"].model_dump()
    }
    
    # Store in transient session cache (does NOT persist to history.json)
    return store_transient_analysis(response_payload, filename=filename)

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}

@app.post("/api/analyze")
async def analyze_email(
    file: UploadFile = File(None),
    raw_content: str = Form(None),
    live_reverify: bool = Form(False)
):
    if file:
        content = await file.read()
        filename = file.filename or "uploaded_email.eml"
    elif raw_content:
        content = raw_content.encode('utf-8')
        filename = "pasted_email.eml"
    else:
        raise HTTPException(status_code=400, detail="No email file or raw content provided.")
        
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File size exceeds 5 MB limit")
        
    if not content or not content.strip():
        raise HTTPException(status_code=400, detail="Not a valid RFC 822 email")
        
    # Check for From header in the email RFC 822 headers
    header_chunk = content[:10000].decode('utf-8', errors='replace')
    if not re.search(r'(?im)^From:\s*\S+', header_chunk):
        raise HTTPException(status_code=400, detail="Not a valid RFC 822 email")
        
    try:
        return run_analysis_pipeline(content, filename=filename, live_reverify=live_reverify)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Email analysis pipeline failed: {str(e)}")

@app.get("/api/samples")
async def list_samples():
    return SAMPLES_META

@app.get("/api/samples/{sample_id}")
async def get_sample_content(sample_id: str):
    sample = next((s for s in SAMPLES_META if s["id"] == sample_id), None)
    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found.")
        
    file_path = os.path.join(SAMPLE_DIR, sample["filename"])
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"File {sample['filename']} missing on server.")
        
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    return {
        "meta": sample,
        "raw_eml": content
    }

@app.post("/api/history/save")
async def save_case_to_history(payload: Dict[str, Any]):
    case_id = payload.get("case_id")
    label = payload.get("label") or payload.get("analyst_label")
    if not case_id:
        raise HTTPException(status_code=400, detail="Missing case_id in request body.")
    try:
        saved_case, is_dup = save_case(case_id, analyst_label=label)
        return {
            "status": "saved",
            "case_id": saved_case["case_id"],
            "duplicate": is_dup,
            "analysis": saved_case
        }
    except KeyError:
        raise HTTPException(status_code=404, detail="Analysis expired, please re-run it")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save case: {str(e)}")

@app.get("/api/history/{case_id}")
async def get_history_case_detail(case_id: str):
    analysis = get_case_analysis(case_id)
    if not analysis or not case_id.startswith("CASE-"):
        raise HTTPException(status_code=404, detail=f"Saved case '{case_id}' not found.")
    return analysis

@app.delete("/api/history/{case_id}")
async def delete_history_case(case_id: str):
    deleted = delete_saved_case(case_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found in saved history.")
    return {"status": "deleted", "case_id": case_id}

@app.delete("/api/history")
async def clear_all_history():
    clear_all_saved_cases()
    return {"status": "cleared"}

@app.get("/api/history")
async def list_history():
    return get_history_summaries()

# -------------------------------------------------------------
# Stage 2: Report-a-Phish Mailbox & Ingestion API Endpoints
# -------------------------------------------------------------

@app.get("/api/inbox")
async def list_inbox_items():
    return get_inbox_items()

@app.get("/api/inbox/{inbox_id}")
async def get_inbox_detail(inbox_id: str):
    item = get_inbox_item(inbox_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Inbox item '{inbox_id}' not found.")
    return item

@app.post("/api/inbox/{inbox_id}/review")
async def mark_inbox_item_reviewed(inbox_id: str):
    ok = mark_reviewed(inbox_id, True)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Inbox item '{inbox_id}' not found.")
    return {"status": "reviewed", "id": inbox_id}

@app.post("/api/inbox/{inbox_id}/save")
async def save_inbox_item_endpoint(inbox_id: str, payload: Optional[Dict[str, Any]] = None):
    label = (payload or {}).get("label") or (payload or {}).get("analyst_label")
    saved_record, is_dup = save_inbox_item(inbox_id, analyst_label=label)
    if not saved_record:
        raise HTTPException(status_code=404, detail=f"Inbox item '{inbox_id}' not found.")
    return {
        "status": "saved",
        "saved_case": saved_record,
        "duplicate": is_dup
    }

@app.delete("/api/inbox/{inbox_id}")
async def delete_inbox_item_endpoint(inbox_id: str):
    ok = remove_inbox_item(inbox_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Inbox item '{inbox_id}' not found.")
    return {"status": "deleted", "id": inbox_id}

@app.get("/api/ingest/status")
async def get_ingestion_status():
    return {
        "dropfolder": dropfolder_watcher.get_status(),
        "imap": imap_watcher.get_status()
    }

@app.post("/api/report/pdf")
async def download_pdf_report(payload: Dict[str, Any]):
    case_id = payload.get("case_id")
    analysis = None
    if case_id:
        analysis = get_case_analysis(case_id)
    if not analysis:
        # Fallback to direct analysis payload if supplied and complete
        if "verdict" in payload and "sha256_hash" in payload:
            analysis = payload
        else:
            raise HTTPException(status_code=404, detail="Analysis expired, please re-run it")
            
    try:
        pdf_bytes = generate_forensic_pdf(analysis)
        sha256 = analysis.get("sha256_hash", "forensic_report")[:10]
        cid = analysis.get("case_id", "case")
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=VERITAS_{cid}_{sha256}.pdf"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF report: {str(e)}")

# Serve built frontend from ../frontend/dist if available
FRONTEND_DIST = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'frontend', 'dist'))
if os.path.exists(FRONTEND_DIST):
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)

