"""
VERITAS Forensic Platform - Comprehensive Regression & Integration Test Suite
Validates:
1. All 5 bundled samples against POST /api/analyze (Verdict, Rules, Layer statuses)
2. Input validation (Empty file, No-From file, No-Received hop, Multi-hop bottom-most selection, Unknown domain)
3. Layer 5 behavior on Sample 5 (PROBABLE + SUSPICIOUS mention, not 'clean')
4. DKIM relaxed subdomain alignment (no C2 contradiction)
5. PDF generation and parsing with pypdf (verdict, rule IDs, SHA-256 hash, sender email)
6. Temporary in-memory analysis lifecycle:
   - POST /api/analyze returns transient random 'TMP-XXXXXXXX' ID, duplicate: False, saved: False
   - GET /api/history remains empty until explicitly saved
7. Explicit save and SHA-256 deduplication:
   - POST /api/history/save persists case as 'CASE-xxxx'
   - Deduplication on save returns duplicate: True, same CASE-xxxx ID
   - GET /api/history returns summaries only
   - GET /api/history/{case_id} returns full analysis
8. Server restart simulation:
   - Evicting temp cache causes unsaved TMP- IDs to return 404 'Analysis expired, please re-run it' on PDF download
   - Saved CASE-xxxx IDs remain retrievable and can generate PDFs after restart
9. Case deletion and monotonic counter preservation:
   - DELETE /api/history/{case_id} deletes case but preserves next_id (no ID reuse)
   - DELETE /api/history clears all cases but preserves next_id
10. Corrupt file handling and recovery:
   - Malformed history.json is backed up to history.json.bak and started fresh
11. CLI reset action (--reset-history):
   - storage.reset_history_file() resets next_id to 1 and empties cases and cache
12. Health check (GET /api/health -> {"status": "ok"})
"""

import os
import sys
import io
import json
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient
import pypdf

# Ensure backend root is on sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app.main import app, SAMPLES_META, SAMPLE_DIR
import app.storage as storage

client = TestClient(app)

EXPECTED_LAYER_STATUSES = {
    "sample-1": {
        "layer1": "VERIFIED",
        "layer2": "VERIFIED",
        "layer3": "VERIFIED",
        "layer4": "VERIFIED",
        "layer5": "VERIFIED"
    },
    "sample-2": {
        "layer1": "UNCERTAIN",
        "layer2": "UNCERTAIN",
        "layer3": "UNCERTAIN",
        "layer4": "UNCERTAIN",
        "layer5": "UNCERTAIN"
    },
    "sample-3": {
        "layer1": "UNCERTAIN",
        "layer2": "UNCERTAIN",
        "layer3": "UNCERTAIN",
        "layer4": "UNCERTAIN",
        "layer5": "PROBABLE"
    },
    "sample-4": {
        "layer1": "VERIFIED",
        "layer2": "VERIFIED",
        "layer3": "UNCERTAIN",
        "layer4": "UNCERTAIN",
        "layer5": "UNCERTAIN"
    },
    "sample-5": {
        "layer1": "VERIFIED",
        "layer2": "VERIFIED",
        "layer3": "VERIFIED",
        "layer4": "UNCERTAIN",
        "layer5": "PROBABLE"
    }
}

def run_tests():
    all_passed = True
    summary_rows = []

    print("\n" + "="*80)
    print(" VERITAS FORENSICS PLATFORM - REGRESSION & INTEGRATION TEST SUITE ")
    print("="*80 + "\n")

    # Isolate test history by monkeypatching storage.HISTORY_FILE to a temporary file
    temp_dir = tempfile.TemporaryDirectory()
    test_history_path = os.path.join(temp_dir.name, "test_history.json")
    storage.HISTORY_FILE = test_history_path
    storage.reset_history_file()

    try:
        # -------------------------------------------------------------
        # 1. Test Health Check
        # -------------------------------------------------------------
        print("[TEST 1] Checking GET /api/health...")
        res = client.get("/api/health")
        assert res.status_code == 200, f"Health check failed with {res.status_code}"
        assert res.json() == {"status": "ok"}, f"Unexpected health check response: {res.json()}"
        print("  [PASS] /api/health returned 200 {'status': 'ok'}")

        # -------------------------------------------------------------
        # 2. Test All 5 Bundled Samples (Transient Analysis)
        # -------------------------------------------------------------
        sample_analyses = {}
        print("\n[TEST 2] Testing 5 Bundled EML Samples against POST /api/analyze...")

        for sample in SAMPLES_META:
            sid = sample["id"]
            fname = sample["filename"]
            exp_verdict = sample["expected_verdict"]
            exp_rules = sorted(sample["expected_rule_ids"])
            fpath = os.path.join(SAMPLE_DIR, fname)

            with open(fpath, "rb") as f:
                eml_bytes = f.read()

            res = client.post(
                "/api/analyze",
                files={"file": (fname, eml_bytes, "message/rfc822")}
            )
            assert res.status_code == 200, f"Sample {sid} analysis failed: {res.status_code} {res.text}"
            data = res.json()
            sample_analyses[sid] = data

            # Verify transient case ID structure
            cid = data.get("case_id", "")
            assert cid.startswith("TMP-"), f"Expected transient ID starting with TMP-, got {cid}"
            assert len(cid) == 12, f"Expected 12-char ID (TMP-XXXXXXXX), got {cid}"
            assert data.get("duplicate") is False, f"Expected duplicate: False on initial analyze, got {data.get('duplicate')}"
            assert data.get("saved") is False, f"Expected saved: False on initial analyze, got {data.get('saved')}"

            act_verdict = data["verdict"]["verdict"]
            act_rules = sorted([c["rule_id"] for c in data["contradictions"]])

            verdict_ok = (act_verdict == exp_verdict)
            rules_ok = (act_rules == exp_rules)

            # Check expected layer statuses
            expected_layers = EXPECTED_LAYER_STATUSES.get(sid, {})
            layers_ok = True
            layer_failures = []
            for l_key, exp_st in expected_layers.items():
                act_st = data[l_key]["status"]
                if act_st != exp_st:
                    layers_ok = False
                    layer_failures.append(f"{l_key}: expected {exp_st}, got {act_st}")

            sample_pass = verdict_ok and rules_ok and layers_ok
            if not sample_pass:
                all_passed = False

            summary_rows.append({
                "sample": sample["name"].split(":")[0].strip(),
                "verdict": act_verdict,
                "expected_verdict": exp_verdict,
                "rules": ",".join(act_rules) or "None",
                "expected_rules": ",".join(exp_rules) or "None",
                "match": "PASS" if sample_pass else "FAIL"
            })

            if not sample_pass:
                print(f"  [FAIL] {fname}: Verdict match={verdict_ok}, Rules match={rules_ok}, Layer match={layers_ok} ({', '.join(layer_failures)})")
            else:
                print(f"  [PASS] {fname}: Transient ID '{cid}', Verdict '{act_verdict}', Rules {act_rules}, Layers match.")

        # Confirm case history is STILL empty after analyzing all 5 samples
        hist_check = client.get("/api/history")
        assert hist_check.status_code == 200
        assert len(hist_check.json()) == 0, f"History should be empty before saving, found {len(hist_check.json())} entries"
        print("  [PASS] GET /api/history is strictly empty (0 saved cases) following all analyses.")

        # -------------------------------------------------------------
        # 3. Test Layer 5 Specifics for Sample 5
        # -------------------------------------------------------------
        print("\n[TEST 3] Testing Sample 5 Layer 5 status & summary text...")
        s5_data = sample_analyses["sample-5"]
        s5_l5 = s5_data["layer5"]
        assert s5_l5["status"] == "PROBABLE", f"Sample 5 Layer 5 status is {s5_l5['status']}, expected PROBABLE"
        assert "SUSPICIOUS" in s5_l5["summary"], f"Sample 5 Layer 5 summary does not mention SUSPICIOUS: {s5_l5['summary']}"
        assert "clean" not in s5_l5["summary"].lower(), f"Sample 5 Layer 5 summary claims 'clean': {s5_l5['summary']}"
        print(f"  [PASS] Sample 5 Layer 5: status={s5_l5['status']}, summary mentions SUSPICIOUS and not 'clean'.")

        # -------------------------------------------------------------
        # 4. Test Input Validations & Edge Cases
        # -------------------------------------------------------------
        print("\n[TEST 4] Testing Input Validation & Edge Cases...")

        # 4a. Empty file upload -> 400 "Not a valid RFC 822 email"
        res = client.post("/api/analyze", files={"file": ("empty.eml", b"", "message/rfc822")})
        assert res.status_code == 400, f"Expected 400 for empty file, got {res.status_code}"
        assert "Not a valid RFC 822 email" in res.json().get("detail", ""), f"Unexpected detail: {res.json()}"
        print("  [PASS] Empty file upload returned 400 'Not a valid RFC 822 email'")

        # 4b. Plain text with no headers -> 400 "Not a valid RFC 822 email"
        res = client.post("/api/analyze", files={"file": ("plain.eml", b"Just some plain text without any from header", "message/rfc822")})
        assert res.status_code == 400, f"Expected 400 for no-From file, got {res.status_code}"
        assert "Not a valid RFC 822 email" in res.json().get("detail", ""), f"Unexpected detail: {res.json()}"
        print("  [PASS] Plain text without From header returned 400 'Not a valid RFC 822 email'")

        # 4c. File with no Received header -> returns 200, originating_ip is None, Layer 4 UNCERTAIN, summary "No originating IP found in Received headers"
        no_recv_eml = b"""From: test@example.com\r\nTo: recipient@example.com\r\nSubject: Test No Received\r\nDate: Tue, 27 Oct 2026 10:00:00 +0000\r\nMessage-ID: <norecv-123@example.com>\r\n\r\nHello world without received header.\r\n"""
        res = client.post("/api/analyze", files={"file": ("norecv.eml", no_recv_eml, "message/rfc822")})
        assert res.status_code == 200, f"Expected 200 for email without received header, got {res.status_code}: {res.text}"
        norecv_data = res.json()
        assert norecv_data["layer4"]["originating_ip"] is None, f"Expected None originating_ip, got {norecv_data['layer4']['originating_ip']}"
        assert norecv_data["layer4"]["status"] == "UNCERTAIN", f"Expected UNCERTAIN Layer 4 status, got {norecv_data['layer4']['status']}"
        assert norecv_data["layer4"]["summary"] == "No originating IP found in Received headers", f"Unexpected summary: {norecv_data['layer4']['summary']}"
        print("  [PASS] Email with no Received header returned 200, originating_ip=None, UNCERTAIN status, and exact summary message.")

        # 4d. Multi-hop Received headers -> bottom-most public IP picked, ignoring private hops
        multihop_eml = b"""From: sender@corp.com\r\nTo: dest@corp.com\r\nSubject: Multi Hop\r\nDate: Tue, 27 Oct 2026 10:00:00 +0000\r\nMessage-ID: <multi-123@corp.com>\r\nReceived: from edge.receiver.com ([10.0.0.1]) by mx.google.com with SMTP; Tue, 27 Oct 2026 10:02:00 +0000\r\nReceived: from relay.relay.com ([198.51.100.22]) by edge.receiver.com with ESMTP; Tue, 27 Oct 2026 10:01:00 +0000\r\nReceived: from client.internal ([192.168.1.50]) by relay.relay.com with SMTP; Tue, 27 Oct 2026 10:00:30 +0000\r\nReceived: from origin.customer.com ([203.0.113.88]) by relay.relay.com with ESMTP; Tue, 27 Oct 2026 10:00:00 +0000\r\nReceived: from localhost ([127.0.0.1]) by origin.customer.com with SMTP; Tue, 27 Oct 2026 09:59:00 +0000\r\n\r\nMulti hop email test body.\r\n"""
        res = client.post("/api/analyze", files={"file": ("multihop.eml", multihop_eml, "message/rfc822")})
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        multihop_data = res.json()
        assert multihop_data["layer4"]["originating_ip"] == "203.0.113.88", f"Expected bottom-most public IP 203.0.113.88, got {multihop_data['layer4']['originating_ip']}"
        print("  [PASS] Multi-hop email correctly selected bottom-most public IP (203.0.113.88) ignoring private/loopback hops.")

        # 4e. Domain not in domain_registry.json -> domain_age_days is None, Layer 4 is not VERIFIED
        unknown_domain_eml = b"""From: User <user@unregistered-nonexistent-domain-404.org>\r\nTo: dest@corp.com\r\nSubject: Unknown Domain\r\nDate: Tue, 27 Oct 2026 10:00:00 +0000\r\nMessage-ID: <unk-123@unregistered.org>\r\nReceived: from mail.isp.net ([203.0.113.45]) by mx.corp.com with ESMTP; Tue, 27 Oct 2026 10:00:00 +0000\r\n\r\nTesting unknown domain.\r\n"""
        res = client.post("/api/analyze", files={"file": ("unknown_domain.eml", unknown_domain_eml, "message/rfc822")})
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        unk_data = res.json()
        assert unk_data["layer4"]["domain_age_days"] is None, f"Expected None domain_age_days, got {unk_data['layer4']['domain_age_days']}"
        assert unk_data["layer4"]["status"] != "VERIFIED", f"Layer 4 should not be VERIFIED when domain age is None, got {unk_data['layer4']['status']}"
        print("  [PASS] Unknown domain yielded domain_age_days=None and Layer 4 status is not VERIFIED.")

        # -------------------------------------------------------------
        # 5. Test DKIM Alignment with Subdomain
        # -------------------------------------------------------------
        print("\n[TEST 5] Testing DKIM Subdomain Alignment...")
        dkim_subdomain_eml = b"""From: Alice <alice@sub.acme-corp.com>\r\nTo: bob@example.com\r\nSubject: Subdomain Alignment\r\nDate: Tue, 27 Oct 2026 10:00:00 +0000\r\nMessage-ID: <dkim-sub-123@sub.acme-corp.com>\r\nDKIM-Signature: v=1; a=rsa-sha256; c=relaxed/relaxed; d=acme-corp.com; s=s1; h=from:to:subject:date; b=abcdef123456\r\nReceived: from mail.sub.acme-corp.com ([203.0.113.45]) by mx.example.com with ESMTP; Tue, 27 Oct 2026 10:00:00 +0000\r\n\r\nHello from subdomain.\r\n"""
        res = client.post("/api/analyze", files={"file": ("dkim_sub.eml", dkim_subdomain_eml, "message/rfc822")})
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        sub_data = res.json()
        assert sub_data["layer2"]["domain_aligned"] is True, f"Expected domain_aligned=True for sub.acme-corp.com signed by acme-corp.com, got {sub_data['layer2']['domain_aligned']}"
        c_rules = [c["rule_id"] for c in sub_data["contradictions"]]
        assert "C2" not in c_rules, f"Rule C2 should not fire on relaxed subdomain alignment, fired rules: {c_rules}"
        print("  [PASS] DKIM subdomain alignment passes; Rule C2 did not fire.")

        # -------------------------------------------------------------
        # 6. Test PDF Generation for Transient Analysis (Cached)
        # -------------------------------------------------------------
        print("\n[TEST 6] Testing PDF Generation from Transient In-Memory Cache...")
        for sid, data in sample_analyses.items():
            case_id = data["case_id"]
            verdict_str = data["verdict"]["verdict"]
            rules = [c["rule_id"] for c in data["contradictions"]]
            sha256 = data["sha256_hash"]
            sender = data["email_meta"]["from_header"]
            sender_addr = data["layer1"]["from_address"]

            pdf_res = client.post("/api/report/pdf", json={"case_id": case_id})
            assert pdf_res.status_code == 200, f"PDF report download failed for transient {sid} ({case_id}): {pdf_res.status_code}"
            assert pdf_res.headers.get("content-type") == "application/pdf"

            pdf_bytes = pdf_res.content
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
            extracted_text = ""
            for page in reader.pages:
                extracted_text += page.extract_text() or ""

            assert verdict_str.upper() in extracted_text.upper(), f"PDF missing verdict '{verdict_str}' for {sid}"
            for r in rules:
                assert r in extracted_text, f"PDF missing rule '{r}' for {sid}"
            assert sha256[:16] in extracted_text, f"PDF missing SHA-256 hash prefix for {sid}"
            assert sender_addr.lower() in extracted_text.lower() or sender.lower() in extracted_text.lower(), f"PDF missing sender for {sid}"

            print(f"  [PASS] Transient {sid} ({case_id}): Valid PDF generated ({len(pdf_bytes)} bytes) verified via pypdf.")

        # -------------------------------------------------------------
        # 7. Test Explicit Save, Deduplication & Storage Endpoints
        # -------------------------------------------------------------
        print("\n[TEST 7] Testing Explicit Case Saving, Persistent Storage & Deduplication...")
        s1_tmp_id = sample_analyses["sample-1"]["case_id"]

        # 7a. Save Sample 1 to history
        save_res = client.post("/api/history/save", json={"case_id": s1_tmp_id})
        assert save_res.status_code == 200, f"Failed to save case: {save_res.text}"
        saved_info = save_res.json()
        assert saved_info["status"] == "saved"
        assert saved_info["case_id"] == "CASE-0001", f"Expected CASE-0001, got {saved_info['case_id']}"
        assert saved_info["duplicate"] is False
        assert saved_info["analysis"]["saved"] is True
        print(f"  [PASS] Successfully saved {s1_tmp_id} as CASE-0001.")

        # 7b. Verify GET /api/history returns 1 summary
        hist_res = client.get("/api/history")
        assert hist_res.status_code == 200
        summaries = hist_res.json()
        assert len(summaries) == 1, f"Expected 1 saved case, got {len(summaries)}"
        assert summaries[0]["case_id"] == "CASE-0001"
        assert summaries[0]["verdict"] == "Likely Legitimate"
        print("  [PASS] GET /api/history returns 1 summary matching CASE-0001.")

        # 7c. Verify GET /api/history/CASE-0001 returns full analysis
        detail_res = client.get("/api/history/CASE-0001")
        assert detail_res.status_code == 200
        detail_data = detail_res.json()
        assert detail_data["case_id"] == "CASE-0001"
        assert detail_data["saved"] is True
        assert "layer1" in detail_data and "contradictions" in detail_data
        print("  [PASS] GET /api/history/CASE-0001 returns full analysis.")

        # 7d. Verify GET /api/history/{tmp_id} returns 404 (strict separation)
        detail_tmp_res = client.get(f"/api/history/{s1_tmp_id}")
        assert detail_tmp_res.status_code == 404
        print("  [PASS] GET /api/history/{TMP-id} correctly returns 404 (only CASE- IDs accepted).")

        # 7e. Deduplication on save: Re-upload sample 1, get new TMP- ID, then save
        fpath1 = os.path.join(SAMPLE_DIR, "01_clean_legitimate.eml")
        with open(fpath1, "rb") as f:
            s1_bytes = f.read()

        reupload_res = client.post("/api/analyze", files={"file": ("01_clean_legitimate_copy.eml", s1_bytes, "message/rfc822")})
        assert reupload_res.status_code == 200
        reupload_data = reupload_res.json()
        reupload_tmp_id = reupload_data["case_id"]
        assert reupload_tmp_id != s1_tmp_id, "New upload should receive a distinct transient TMP- ID"

        save_dup_res = client.post("/api/history/save", json={"case_id": reupload_tmp_id})
        assert save_dup_res.status_code == 200
        save_dup_info = save_dup_res.json()
        assert save_dup_info["duplicate"] is True, f"Expected duplicate: True, got {save_dup_info['duplicate']}"
        assert save_dup_info["case_id"] == "CASE-0001", f"Expected duplicate to match CASE-0001, got {save_dup_info['case_id']}"

        # Confirm history count still 1
        hist_res2 = client.get("/api/history")
        assert len(hist_res2.json()) == 1, "History count increased despite duplicate SHA-256 save"
        print("  [PASS] Duplicate SHA-256 save correctly detected: duplicate=True, case_id='CASE-0001', history length=1.")

        # -------------------------------------------------------------
        # 8. Test Server Restart Simulation (Temp Cache Eviction)
        # -------------------------------------------------------------
        print("\n[TEST 8] Testing Server Restart Simulation (Temp Cache Evicted)...")
        # Clear in-memory cache
        storage._temp_cache.clear()

        # Unsaved transient ID should now fail with 404 "Analysis expired, please re-run it"
        unsaved_tmp_id = sample_analyses["sample-2"]["case_id"]
        exp_pdf_res = client.post("/api/report/pdf", json={"case_id": unsaved_tmp_id})
        assert exp_pdf_res.status_code == 404, f"Expected 404 for expired transient analysis, got {exp_pdf_res.status_code}"
        assert "Analysis expired, please re-run it" in exp_pdf_res.json().get("detail", "")
        print("  [PASS] Unsaved transient ID returned 404 'Analysis expired, please re-run it' after server restart.")

        # Attempting to save expired transient ID should also return 404
        exp_save_res = client.post("/api/history/save", json={"case_id": unsaved_tmp_id})
        assert exp_save_res.status_code == 404
        assert "Analysis expired, please re-run it" in exp_save_res.json().get("detail", "")
        print("  [PASS] Saving expired transient ID returned 404 'Analysis expired, please re-run it'.")

        # But saved CASE-0001 MUST still exist in persistent storage and generate PDF
        saved_pdf_res = client.post("/api/report/pdf", json={"case_id": "CASE-0001"})
        assert saved_pdf_res.status_code == 200, f"Expected 200 for saved case PDF after restart, got {saved_pdf_res.status_code}"
        assert saved_pdf_res.headers.get("content-type") == "application/pdf"
        print("  [PASS] Saved CASE-0001 successfully generated PDF from persistent storage after server restart.")

        # -------------------------------------------------------------
        # 9. Test Deletion & Monotonic ID Preservation
        # -------------------------------------------------------------
        print("\n[TEST 9] Testing Deletion & Monotonic Counter Preservation...")
        # Delete CASE-0001
        del_res = client.delete("/api/history/CASE-0001")
        assert del_res.status_code == 200, f"Delete failed: {del_res.text}"
        assert del_res.json() == {"status": "deleted", "case_id": "CASE-0001"}

        # Verify history is now empty
        assert len(client.get("/api/history").json()) == 0
        assert client.get("/api/history/CASE-0001").status_code == 404
        print("  [PASS] DELETE /api/history/CASE-0001 removed the case.")

        # Analyze Sample 2 and save it
        fpath2 = os.path.join(SAMPLE_DIR, "02_classic_phishing.eml")
        with open(fpath2, "rb") as f:
            s2_bytes = f.read()
        res_s2 = client.post("/api/analyze", files={"file": ("02_classic_phishing.eml", s2_bytes, "message/rfc822")})
        s2_tmp_id = res_s2.json()["case_id"]

        save_s2_res = client.post("/api/history/save", json={"case_id": s2_tmp_id})
        assert save_s2_res.status_code == 200
        s2_saved_id = save_s2_res.json()["case_id"]
        assert s2_saved_id == "CASE-0002", f"Expected monotonic CASE-0002 (never reuse CASE-0001), got {s2_saved_id}"
        print(f"  [PASS] Monotonic counter preserved after delete: next case assigned {s2_saved_id}.")

        # Clear all saved cases
        clear_res = client.delete("/api/history")
        assert clear_res.status_code == 200
        assert clear_res.json() == {"status": "cleared"}
        assert len(client.get("/api/history").json()) == 0
        print("  [PASS] DELETE /api/history cleared all saved cases.")

        # Analyze Sample 3 and save it - next_id should still NOT reset to 1
        fpath3 = os.path.join(SAMPLE_DIR, "03_spoofed_bec.eml")
        with open(fpath3, "rb") as f:
            s3_bytes = f.read()
        res_s3 = client.post("/api/analyze", files={"file": ("03_spoofed_bec.eml", s3_bytes, "message/rfc822")})
        s3_tmp_id = res_s3.json()["case_id"]

        save_s3_res = client.post("/api/history/save", json={"case_id": s3_tmp_id})
        assert save_s3_res.status_code == 200
        s3_saved_id = save_s3_res.json()["case_id"]
        assert s3_saved_id == "CASE-0003", f"Expected monotonic CASE-0003 after clear_all, got {s3_saved_id}"
        print(f"  [PASS] Monotonic counter preserved after clear_all: next case assigned {s3_saved_id}.")

        # -------------------------------------------------------------
        # 10. Test Corrupt File Recovery
        # -------------------------------------------------------------
        print("\n[TEST 10] Testing Corrupt File Handling & .bak Backup...")
        # Write corrupted JSON to history file
        with open(test_history_path, "w", encoding="utf-8") as f:
            f.write("{corrupt: this is not valid json! %$#@")

        # Loading should not crash; it should rename to .bak and return fresh (1, [])
        next_id, cases = storage._load_persistent_data()
        assert next_id == 1, f"Expected reset next_id=1, got {next_id}"
        assert cases == [], f"Expected empty cases, got {cases}"
        assert os.path.exists(test_history_path + ".bak"), "Expected corrupt file to be renamed to .bak"
        print("  [PASS] Corrupt history.json was safely backed up to history.json.bak and reset without crashing.")

        # -------------------------------------------------------------
        # 11. Test CLI Reset History Functionality
        # -------------------------------------------------------------
        print("\n[TEST 11] Testing CLI storage.reset_history_file()...")
        storage.reset_history_file()
        next_id, cases = storage._load_persistent_data()
        assert next_id == 1 and len(cases) == 0
        assert len(storage._temp_cache) == 0
        print("  [PASS] reset_history_file() resets next_id=1, cases=[], and empties temp cache.")

        # -------------------------------------------------------------
        # Summary Table
        # -------------------------------------------------------------
        print("\n" + "="*80)
        print(f"{'Sample':<12} | {'Verdict':<20} | {'Expected':<20} | {'Rules Fired':<12} | {'Expected Rules':<14} | {'Match?':<6}")
        print("-"*80)
        for r in summary_rows:
            print(f"{r['sample']:<12} | {r['verdict']:<20} | {r['expected_verdict']:<20} | {r['rules']:<12} | {r['expected_rules']:<14} | {r['match']:<6}")
        print("="*80)

        if all_passed:
            print("\n>>> ALL TESTS PASSED SUCCESSFULLY (Exit Code 0) <<<\n")
            return 0
        else:
            print("\n>>> SOME TESTS FAILED (Exit Code 1) <<<\n")
            return 1

    finally:
        # Cleanup temporary directory
        temp_dir.cleanup()

if __name__ == "__main__":
    code = run_tests()
    sys.exit(code)
