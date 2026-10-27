import os
import shutil
import tempfile
import pytest
from app.main import run_analysis_pipeline, SAMPLES_META, SAMPLE_DIR
from app.ingest.dropfolder import DropfolderWatcher
from app.ingest import inbox_store
from app import storage

FIXTURES_REAL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'fixtures', 'real'))

def read_fixture(name: str) -> bytes:
    p = os.path.join(FIXTURES_REAL_DIR, name)
    with open(p, 'rb') as f:
        return f.read()

@pytest.fixture(autouse=True)
def isolate_test_environment(monkeypatch):
    """Isolate history.json and inbox.json in temp directory for every test."""
    temp_dir = tempfile.mkdtemp()
    test_hist_file = os.path.join(temp_dir, 'history.json')
    test_inbox_file = os.path.join(temp_dir, 'inbox.json')
    
    monkeypatch.setattr(storage, 'HISTORY_FILE', test_hist_file)
    monkeypatch.setattr(inbox_store, 'INBOX_FILE', test_inbox_file)
    storage._temp_cache.clear()
    
    yield
    shutil.rmtree(temp_dir, ignore_errors=True)

def test_major_mail_providers_not_flagged_as_datacenter_threat():
    raw_bytes = read_fixture('01_gmail_newsletter.eml')
    res = run_analysis_pipeline(raw_bytes, filename='01_gmail_newsletter.eml')
    
    l4 = res['layer4']
    rule_ids = [c['rule_id'] for c in res.get('contradictions', [])]
    
    assert l4['infra_category'] == 'major_mail_provider'
    assert l4['status'] == 'VERIFIED'
    assert 'C5' not in rule_ids, "Major mail provider (Google) must not trigger datacenter rule C5"

def test_forwarded_abuse_report_unwrapping():
    raw_bytes = read_fixture('06_forwarded_abuse_report.eml')
    res = run_analysis_pipeline(raw_bytes, filename='06_forwarded_abuse_report.eml')
    
    assert res['is_forwarded_report'] is True
    assert res['reported_by'] == 'alice.analyst@victimcorp.com'
    assert 'admin@micr0soft-portal.xyz' in res['email_meta']['from_header']
    assert 'Password Reset' in res['email_meta']['subject']
    assert res['layer4']['originating_ip'] == '185.220.101.44'

def test_html_link_forensics_and_mismatch():
    raw_bytes = read_fixture('08_credential_harvest_lure.eml')
    res = run_analysis_pipeline(raw_bytes, filename='08_credential_harvest_lure.eml')
    
    links = res['layer3'].get('details', {}).get('links', [])
    assert len(links) >= 1
    
    mismatched = [lnk for lnk in links if lnk.get('mismatch')]
    assert len(mismatched) >= 1, "Expected at least one mismatched link"
    
    target_lnk = mismatched[0]
    assert '198.51.100.99' in target_lnk.get('href', '')
    assert target_lnk.get('defanged_destination', '').startswith('hxxp://')
    
    shorteners = [lnk for lnk in links if lnk.get('is_shortener')]
    assert len(shorteners) >= 1, "Expected detection of bit.ly URL shortener"

def test_safe_attachment_inspection():
    raw_bytes = read_fixture('09_malicious_attachment_lure.eml')
    res = run_analysis_pipeline(raw_bytes, filename='09_malicious_attachment_lure.eml')
    
    attachments = res['layer3'].get('details', {}).get('attachments', [])
    assert len(attachments) >= 1
    
    att = attachments[0]
    assert att['filename'] == 'Invoice_90214.pdf.js'
    assert att['is_risky'] is True
    assert 'dangerous' in att.get('risk_reason', '').lower() or 'extension' in att.get('risk_reason', '').lower()
    assert att.get('sha256') is not None

def test_rfc2047_multilingual_decoding():
    raw_bytes = read_fixture('07_multilingual_hindi_chinese.eml')
    res = run_analysis_pipeline(raw_bytes, filename='07_multilingual_hindi_chinese.eml')
    
    subj = res['email_meta']['subject']
    from_hdr = res['email_meta']['from_header']
    
    assert 'सुरक्षा' in subj or 'Security' in subj
    assert 'Navin' in from_hdr or 'navin@globalvendor.in' in from_hdr

def test_dropfolder_watcher_and_inbox():
    with tempfile.TemporaryDirectory() as temp_drop:
        watcher = DropfolderWatcher(watch_dir=temp_drop)
        
        # Place test email in dropfolder
        test_eml_path = os.path.join(temp_drop, 'report_test.eml')
        with open(test_eml_path, 'wb') as f:
            f.write(read_fixture('01_gmail_newsletter.eml'))
            
        assert os.path.exists(test_eml_path)
        watcher.scan_once()
        
        # File should be moved to processed
        assert not os.path.exists(test_eml_path)
        processed_files = os.listdir(watcher.processed_dir)
        assert len(processed_files) == 1
        
        # Inbox store should contain the item
        items = inbox_store.get_inbox_items()
        assert len(items) == 1
        inbox_item = items[0]
        assert inbox_item['source'] == 'dropfolder'
        assert inbox_item['reviewed'] is False
        assert inbox_item['saved_case_id'] is None
        
        # Case history should still be completely empty!
        summaries = storage.get_history_summaries()
        assert len(summaries) == 0
        
        # Now explicitly save the inbox item
        saved_record, is_dup = inbox_store.save_inbox_item(inbox_item['id'], 'Cleared')
        assert is_dup is False
        assert saved_record['case_id'].startswith('CASE-')
        assert saved_record['analyst_label'] == 'CLEARED'
        
        # History should now have 1 case
        summaries = storage.get_history_summaries()
        assert len(summaries) == 1
        assert summaries[0]['case_id'] == saved_record['case_id']

def test_layer5_learning_from_analyst_saved_case():
    # Save a case with originating_ip 198.51.100.77 as Confirmed fraud
    fake_analysis = {
        'sha256_hash': 'abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890',
        'email_meta': {'subject': 'Known Malicious Campaign', 'from': 'bad@actor.com'},
        'layer1': {'from_domain': 'actor.com'},
        'layer4': {'originating_ip': '198.51.100.77', 'asn': 'AS9999'},
        'verdict': {'verdict': 'Likely Fraudulent', 'risk_score': 95}
    }
    saved_case, _ = storage.save_analysis_record(fake_analysis, 'Confirmed fraud')
    assert saved_case['case_id'].startswith('CASE-')
    
    # Now run an email that shares originating_ip 198.51.100.77
    raw_bytes = read_fixture('09_malicious_attachment_lure.eml')
    res = run_analysis_pipeline(raw_bytes, filename='09_malicious_attachment_lure.eml')
    
    l5 = res['layer5']
    assert l5['cluster_match'] is True
    assert l5['details']['has_fraud_match'] is True
    assert saved_case['case_id'] in l5['matched_case_ids']
    assert 'fraud' in l5['summary'].lower()

def test_bundled_samples_regression_gate():
    for meta in SAMPLES_META:
        p = os.path.join(SAMPLE_DIR, meta['filename'])
        with open(p, 'rb') as f:
            raw = f.read()
        res = run_analysis_pipeline(raw, filename=meta['filename'])
        
        rule_ids = sorted([c['rule_id'] for c in res.get('contradictions', [])])
        expected_rules = sorted(meta['expected_rule_ids'])
        
        assert res['verdict']['verdict'] == meta['expected_verdict']
        assert rule_ids == expected_rules

def test_inbox_api_endpoints():
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)
    
    # 1. Ingest status
    r = client.get('/api/ingest/status')
    assert r.status_code == 200
    st = r.json()
    assert 'dropfolder' in st and 'imap' in st
    
    # 2. Add an item directly via inbox_store
    raw_bytes = read_fixture('01_gmail_newsletter.eml')
    analysis = run_analysis_pipeline(raw_bytes, filename='01_gmail_newsletter.eml')
    item = inbox_store.add_inbox_item(analysis, source='dropfolder', filename='test.eml')
    inbox_id = item['id']
    
    # 3. List inbox
    r = client.get('/api/inbox')
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1
    assert items[0]['id'] == inbox_id
    assert items[0]['reviewed'] is False
    
    # 4. Get detail
    r = client.get(f'/api/inbox/{inbox_id}')
    assert r.status_code == 200
    detail = r.json()
    assert detail['id'] == inbox_id
    assert 'analysis' in detail
    
    # 5. Mark reviewed
    r = client.post(f'/api/inbox/{inbox_id}/review')
    assert r.status_code == 200
    assert r.json()['status'] == 'reviewed'
    
    # 6. Save item
    r = client.post(f'/api/inbox/{inbox_id}/save', json={'label': 'Confirmed fraud'})
    assert r.status_code == 200
    save_data = r.json()
    assert save_data['status'] == 'saved'
    assert save_data['saved_case']['case_id'].startswith('CASE-')
    assert save_data['saved_case']['analyst_label'] == 'CONFIRMED_FRAUD'
    
    # 7. Delete item
    r = client.delete(f'/api/inbox/{inbox_id}')
    assert r.status_code == 200
    assert r.json()['status'] == 'deleted'
    
    # 8. Confirm deleted
    r = client.get(f'/api/inbox/{inbox_id}')
    assert r.status_code == 404

def test_mock_imap_watcher(monkeypatch):
    from app.ingest.imap_watcher import ImapWatcher
    
    monkeypatch.setenv('IMAP_HOST', 'imap.testserver.com')
    monkeypatch.setenv('IMAP_USER', 'soc-abuse@testserver.com')
    monkeypatch.setenv('IMAP_PASSWORD', 'super-secret-pw')
    
    watcher = ImapWatcher()
    assert watcher.is_configured() is True
    
    stored_flags = []
    
    class MockIMAP:
        def __init__(self, host, port):
            pass
        def login(self, u, p):
            pass
        def select(self, folder):
            pass
        def search(self, charset, criteria):
            return 'OK', [b'1']
        def fetch(self, num, query):
            raw = read_fixture('01_gmail_newsletter.eml')
            return 'OK', [(b'1 (RFC822 {1000}', raw)]
        def store(self, num, command, flags):
            stored_flags.append((num, command, flags))
        def close(self):
            pass
        def logout(self):
            pass
            
    import imaplib
    monkeypatch.setattr(imaplib, 'IMAP4_SSL', MockIMAP)
    
    processed = watcher.check_once()
    assert processed == 1
    assert len(stored_flags) == 1
    assert b'1' in stored_flags[0][0]
    
    # Verify item queued in inbox
    items = inbox_store.get_inbox_items()
    assert len(items) == 1
    assert items[0]['source'] == 'imap'
    
    # Verify credentials never leaked in get_status
    st = watcher.get_status()
    assert 'super-secret-pw' not in str(st)

def test_imap_api_endpoints_and_runtime_config(monkeypatch):
    import imaplib
    from fastapi.testclient import TestClient
    from app.main import app, imap_watcher
    from app.ingest import inbox_store

    inbox_store.reset_inbox()

    class MockIMAPSuccess:
        def __init__(self, host, port):
            pass
        def login(self, u, p):
            if p == 'wrong-pass':
                raise Exception('Invalid credentials')
        def select(self, folder, readonly=False):
            return 'OK', [b'1']
        def search(self, charset, criteria):
            return 'OK', [b'']
        def close(self):
            pass
        def logout(self):
            pass

    monkeypatch.setattr(imaplib, 'IMAP4_SSL', MockIMAPSuccess)
    client = TestClient(app)

    # 1. GET /api/ingest/imap/config
    r = client.get('/api/ingest/imap/config')
    assert r.status_code == 200
    assert 'password' not in r.json()

    # 2. POST /api/ingest/imap/test with wrong pass
    r = client.post('/api/ingest/imap/test', json={
        'host': 'imap.gmail.com',
        'port': 993,
        'user': 'demo@gmail.com',
        'password': 'wrong-pass',
        'folder': 'INBOX',
        'use_ssl': True
    })
    assert r.status_code == 200
    res = r.json()
    assert res['success'] is False
    assert 'wrong-pass' not in str(res)

    # 3. POST /api/ingest/imap/test with valid pass
    r = client.post('/api/ingest/imap/test', json={
        'host': 'imap.gmail.com',
        'port': 993,
        'user': 'demo@gmail.com',
        'password': 'good-password-1234',
        'folder': 'INBOX',
        'use_ssl': True
    })
    assert r.status_code == 200
    res = r.json()
    assert res['success'] is True

    # 4. POST /api/ingest/imap/configure (runtime only)
    r = client.post('/api/ingest/imap/configure', json={
        'host': 'imap.gmail.com',
        'port': 993,
        'user': 'demo@gmail.com',
        'password': 'good-password-1234',
        'folder': 'INBOX',
        'use_ssl': True,
        'poll_interval': 10.0
    })
    assert r.status_code == 200
    assert r.json()['status'] == 'CONNECTED'
    assert 'good-password-1234' not in str(r.json())

    # 5. POST /api/ingest/imap/sync
    r = client.post('/api/ingest/imap/sync')
    assert r.status_code == 200
    assert r.json()['status'] == 'ok'

    # 6. POST /api/ingest/imap/disconnect
    r = client.post('/api/ingest/imap/disconnect')
    assert r.status_code == 200
    assert r.json()['status'] == 'STOPPED'

def test_imap_processing_order_seen_flag_on_success(monkeypatch):
    import imaplib
    from app.ingest.imap_watcher import ImapWatcher
    from app.ingest import inbox_store

    inbox_store.reset_inbox()
    stored_flags = []
    
    class MockOrderIMAP:
        def __init__(self, host, port):
            pass
        def login(self, u, p):
            pass
        def select(self, folder):
            return 'OK', [b'1']
        def search(self, charset, criteria):
            return 'OK', [b'1 2']
        def fetch(self, num, query):
            # Message 1 is valid, Message 2 will raise an error
            if num == b'1':
                raw = read_fixture('01_gmail_newsletter.eml')
                return 'OK', [(b'1 (RFC822 {1000}', raw)]
            else:
                return 'OK', None
        def store(self, num, command, flags):
            stored_flags.append((num, command, flags))
        def close(self):
            pass
        def logout(self):
            pass

    monkeypatch.setattr(imaplib, 'IMAP4_SSL', MockOrderIMAP)

    watcher = ImapWatcher()
    watcher.configure('imap.test.com', 993, 'test@test.com', 'secret-pw', auto_start=False)

    processed = watcher.check_once()
    assert processed == 1
    # Only message 1 had \Seen flag stored; message 2 failed fetch/parse and was NOT marked \Seen
    assert len(stored_flags) == 1
    assert b'1' in stored_flags[0][0]
    assert '\\Seen' in stored_flags[0][2]


