# VERITAS — Email Forensics Platform

**VERITAS** is a novel email forensics platform that evaluates raw `.eml` files across **five independent evidence layers** and surfaces explicit **cross-layer contradictions** rather than relying on a single isolated fraud score.

---

## Key Features & Architecture

1. **5 Independent Evidence Layers** (Status: `VERIFIED`, `PROBABLE`, `UNCERTAIN`):
   - **Layer 1 (Claimed Identity)**: From/Reply-To/Return-Path parsing, claimed role, organization, and signature location.
   - **Layer 2 (Technical Identity)**: Delivery-time `Authentication-Results` parsing (SPF, DKIM, DMARC) with DKIM signing domain alignment check.
   - **Layer 3 (Content and Intent)**: Rule-based urgency/BEC cues + Scikit-learn TF-IDF Logistic Regression baseline classifier (`"Baseline classifier — trained on public + synthetic samples"`).
   - **Layer 4 (Infrastructure)**: Originating IP extraction (single/multi-hop), offline `geo_db.json` region lookup (`"Estimated region (±X km)"`), WHOIS domain age, and hosting/VPN ASN identification.
   - **Layer 5 (Historical Pattern)**: NetworkX graph correlation against a 30-case seeded history (`seeded_history.json`).

2. **Cross-Layer Contradiction Engine (Rules C1 – C6)**:
   - **C1 — Geographic Identity Mismatch**: Signature location vs Geolocated IP location.
   - **C2 — Domain/Identity Spoofing**: Visible From domain vs DKIM signing domain or Reply-To domain mismatch.
   - **C3 — Throwaway Domain with Business Content**: Clean content sent from domain registered < 30 days ago.
   - **C4 — Authenticated Sender Matches Historical Fraud Cluster**: Technical auth pass vs Layer 5 historical fraud cluster match (Compromised Account Pattern).
   - **C5 — High-Risk Content from Datacenter Infrastructure**: Urgency/BEC content sent from hosting/datacenter IP.
   - **C6 — Anonymized Origin**: Clean identity & auth routed through an anonymizing VPN exit node.

3. **Pitch Deck UI & Forensic PDF Export**:
   - Cyber-forensic dark UI built with React + Vite + Tailwind CSS.
   - 1-Click Hackathon Preset Buttons for all 5 sample `.eml` files.
   - Force-directed NetworkX graph view and regional accuracy circle map.
   - Downloadable ReportLab Forensic PDF with SHA-256 source hash for chain-of-custody.

---

## Quick Start Instructions

### Prerequisites
- Python 3.11 or 3.13
- Node.js (v18+) & npm

### One-Command Full Stack Launch (`npm run dev`)
Run from either the **project root** or from the **`frontend/`** directory:

```bash
npm run dev
```

This single command launches both:
- **Backend API**: FastAPI / Uvicorn running on `http://127.0.0.1:8000`
- **Frontend App**: React + Vite hot-reload dev server on `http://localhost:3001`
- Automatically opens the web application in your default browser.

### Alternative Production Demo Launchers
- **Windows**: Double click or run `start-demo.bat`
- **macOS / Linux**: Run `./start-demo.sh`

---

## Offline Data & Privacy Disclosure

> [!NOTE]
> **Simulated Demo Dataset**:
> All GeoIP, WHOIS, and ASN data in this demo is simulated from bundled local JSON registries (`geo_db.json`, `domain_registry.json`) for deterministic offline evaluation. No external network requests are made.

---

## Machine Learning Model Information

- **Algorithm**: TF-IDF Vectorizer + Logistic Regression trained on synthetic template and public lure patterns.
- **Scikit-learn Version**: Trained and serialized with `scikit-learn==1.9.0` (pinned in `backend/requirements.txt` alongside `joblib==1.6.0`).
- To re-train or inspect the model:
  ```bash
  python backend/app/data/dataset/train_model.py
  ```

---

## 5 Demo Sample Email Suite

1. **`01_clean_legitimate.eml`**: Routine Q3 audit review from `sarah.jenkins@acmecorp.com`.
   - **Fired Rules**: None (0 total) | **Verdict**: `Likely Legitimate`
2. **`02_classic_phishing.eml`**: Microsoft 365 credential suspension lure from Bucharest hosting IP.
   - **Fired Rules**: `C1`, `C5` (2 total) | **Verdict**: `Likely Fraudulent`
3. **`03_spoofed_bec.eml`**: Urgent acquisition wire transfer from CEO signed by misaligned domain.
   - **Fired Rules**: `C1`, `C2`, `C5` (3 total) | **Verdict**: `Likely Fraudulent`
4. **`04_compromised_account.eml`**: Authentic DKIM-signed vendor email requesting banking detail update.
   - **Fired Rules**: `C4`, `C5` (2 total) | **Verdict**: `Likely Fraudulent`
5. **`05_vpn_obscured.eml`**: Legitimate architecture proposal routed through Mullvad VPN exit node.
   - **Fired Rules**: `C6` (1 total) | **Verdict**: `Needs Review`

## Case Management & History Persistence

VERITAS features an explicit **temporary-to-permanent case management** workflow:

1. **Transient Analysis by Default**:
   - Uploading or analyzing an email generates an in-memory analysis with a transient random ID (e.g., `TMP-A1B2C3D4`).
   - The analysis is kept in a 50-entry in-memory FIFO cache for quick review and PDF export.
   - It is **not** written to disk and does not appear in Case History unless explicitly saved.
2. **Explicit Saving ("Save to Case History")**:
   - Clicking **Save to Case History** permanently stores the full analysis in `backend/app/data/history.json`.
   - The case is assigned a permanent monotonic ID (e.g., `CASE-0001`, `CASE-0002`).
   - Deduplication by SHA-256 hash ensures identical emails are not duplicated in history.
3. **Monotonic IDs & Deletion**:
   - Deleting a case or clearing case history never resets or reuses previously assigned case numbers (`next_id` is persisted).
4. **Resetting History**:
   - To completely reset case history back to `CASE-0001` and clear temporary caches:
     ```bash
     python backend/run.py --reset-history
     ```
     Or pass the flag through the launchers:
     ```bash
     start-demo.bat --reset-history
     # or
     ./start-demo.sh --reset-history
     ```

---

## Real Email Forensics & Hardening

VERITAS is engineered to handle authentic, real-world emails from major providers and complex attack lures:

1. **RFC 2047 Internationalization**:
   - Safely decodes multi-lingual and non-ASCII encoded headers (Base64 and Quoted-Printable) across Hindi, Chinese, Japanese, and European character sets.
   - Fallback chain (`declared -> utf-8 -> latin-1/replace`) guarantees zero crashes or mojibake.

2. **Forwarded Abuse Report Auto-Unwrapping**:
   - When employees forward suspicious emails as attachments (`message/rfc822` or `.eml`), VERITAS automatically detects and unwraps the outer envelope.
   - Extracts and displays the original reporter (`reported_by`) while isolating and evaluating the true sender's infrastructure and technical identity.

3. **HTML Hyperlink Forensics**:
   - Parses HTML bodies using standard library `html.parser` without external network fetches.
   - Defangs destination targets (`hxxp://`) for safe display.
   - Detects deceptive display vs. destination domain mismatches (e.g., text displays `https://portal.office.com` while target points to an attacker IP or typosquat domain).
   - Flags raw IP literal hostnames, Punycode IDN homographs (`xn--`), URL shorteners (bit.ly, t.co, tinyurl), and brand lookalikes (Levenshtein distance 1–2).

4. **Safe Attachment Inspection**:
   - Extracts attachment filenames, MIME types, byte sizes, and SHA-256 hashes without ever writing executable code to disk or executing files.
   - Flags dangerous extensions (`.exe`, `.scr`, `.js`, `.vbs`, `.iso`, `.img`, `.lnk`, `.html`, `.htm`) and deceptive double extensions (e.g., `Invoice.pdf.js`).

5. **Major Mail Provider Network Recognition**:
   - Verifies legitimate email service providers (Google Workspace, Microsoft 365, Amazon SES, SendGrid, Mailchimp, Zoho, Proton) against known ASN and IP CIDR ranges.
   - Prevents legitimate business infrastructure from being falsely flagged under Rule C5 (Datacenter Threat).

---

## Stage 2: "Report-a-Phish" Mailbox Ingestion

VERITAS provides automated background ingestion channels for enterprise SOC workflows:

1. **Drop-Folder Intake (`backend/inbox/`)**:
   - A dedicated background thread continuously watches `backend/inbox/` (polling every 3 seconds).
   - Dropping any raw `.eml` file into this folder triggers automatic 5-layer analysis.
   - Successfully analyzed emails are queued into the **Inbox tab** (`inbox.json`) and the source `.eml` is archived in `backend/inbox/processed/`. Failed files are moved to `backend/inbox/failed/` with an accompanying `.error.txt` diagnostic.

2. **Dedicated IMAP Mailbox Monitoring (Optional)**:
   - Configure your SOC phishing report mailbox in `.env` or system environment:
     ```env
     IMAP_HOST=imap.gmail.com
     IMAP_PORT=993
     IMAP_USER=phish-report@yourdomain.com
     IMAP_PASSWORD=your-app-password
     IMAP_FOLDER=INBOX
     IMAP_SSL=true
     ```
   - VERITAS securely polls unseen messages over SSL every 30 seconds, marks processed emails as `\Seen`, and queues them in the Inbox.
   - **Zero Credential Logging**: Credentials and passwords are never exposed, printed to logs, or persisted in analysis reports.

3. **Analyst Review & Labeling**:
   - Ingested emails remain unreviewed in the Inbox without cluttering permanent Case History.
   - Analysts can inspect the full analysis, toggle the review status, and save the case with an explicit analyst label:
     - `Confirmed fraud`
     - `Suspicious`
     - `Cleared`
   - **Dynamic Historical Learning**: Saved analyst cases immediately feed into Layer 5 (Historical Pattern), dynamically correlating subsequent emails sharing originating IPs or domains in the NetworkX graph.

---

## Offline vs. Live Mode

- **Default Offline Mode**:
  - Operates 100% offline with zero external network dependencies and zero egress latency.
  - GeoIP and ASN lookups utilize local databases (`backend/app/data/geo_db.json` and optional MaxMind/DB-IP MMDB files in `backend/app/data/geoip/`).
  - To download real offline DB-IP Lite databases (free under CC BY 4.0):
    ```bash
    python scripts/fetch_geoip.py
    ```
    *Attribution*: This product includes IP geolocation data created by DB-IP, available from https://db-ip.com under the Creative Commons Attribution 4.0 International License.

- **Opt-In Live Mode (`LIVE: network lookups`)**:
  - Clearly labelled in the UI and API.
  - Performs live DNS queries for public DKIM keys (`dnspython` + `dkimpy`) and live RDAP queries for domain registration age.
  - Failures in external lookups degrade gracefully to "Unresolved" without crashing the engine.

---

## Automated Verification & Regression Suite

Run the full automated test suites to verify platform integrity:

```bash
# 1. Primary Regression Gate (11 integration tests)
python backend/tests/verify_all.py

# 2. Real Email Hardening & Ingestion Suite (10 unit/integration tests)
python -m pytest backend/tests/test_real_emails.py -v
```

