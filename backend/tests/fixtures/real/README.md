# VERITAS Real Email Test Fixtures

This directory contains 9 forensic test fixtures designed to stress-test the VERITAS email forensics engine against authentic real-world email structures, standards compliance, and attack variants.

## Privacy & Safety Standards
- **Zero PII**: No real individual private data or corporate secrets are included.
- **Reserved IP Ranges**: All non-major IPs use RFC 5737 (`192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24`) or simulated public test ranges (`185.220.101.0/24`).
- **Major Providers**: Real provider IP addresses and ASNs (Google AS15169, GitHub AS36459, Amazon SES AS16509) are used to verify major mail provider classification.
- **Safe Payloads**: Attachments contain benign text test scripts (`.pdf.js`) and are **never** executed or saved to disk.

## Fixture Index
1. `01_gmail_newsletter.eml`: Authentic Google Workspace/Gmail structure, DKIM passed, Google IP and ASN.
2. `02_github_notification.eml`: Authentic GitHub security notification with DMARC pass.
3. `03_bank_legitimate_esp.eml`: Banking statement notice sent via Amazon SES.
4. `04_multipart_calendar_invite.eml`: Multipart alternative with text, html, and calendar invitation (`text/calendar`).
5. `05_html_only_marketing.eml`: HTML-only email testing tag stripping and link extraction.
6. `06_forwarded_abuse_report.eml`: Forwarded email with `message/rfc822` attachment; tests automatic report unwrapping and `reported_by` extraction.
7. `07_multilingual_hindi_chinese.eml`: RFC 2047 encoded multi-lingual headers (Hindi and Chinese) and body text.
8. `08_credential_harvest_lure.eml`: Credential lure with text/target link domain mismatch (`https://portal.office.com` pointing to `198.51.100.99`) and URL shortener.
9. `09_malicious_attachment_lure.eml`: Double extension `.pdf.js` script attachment testing safe attachment inspection.
