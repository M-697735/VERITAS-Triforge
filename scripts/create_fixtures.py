import os
import base64

fixtures_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend', 'tests', 'fixtures', 'real'))
os.makedirs(fixtures_dir, exist_ok=True)

f1 = """From: newsletter@techweekly.org
To: security-team@victimcorp.com
Subject: Tech Weekly #42: Advances in Distributed Forensics
Date: Mon, 20 Oct 2026 09:15:00 +0000
Message-ID: <tw-42-20261020@techweekly.org>
Authentication-Results: mx.victimcorp.com; dkim=pass header.i=@techweekly.org; spf=pass (google.com: domain of newsletter@techweekly.org designates 209.85.208.65 as permitted sender)
Received: from mail-ed1-f65.google.com (mail-ed1-f65.google.com [209.85.208.65])
    by mx.victimcorp.com with ESMTPS id abc123google
    for <security-team@victimcorp.com>;
    Mon, 20 Oct 2026 09:15:02 +0000
Content-Type: text/plain; charset="utf-8"

Welcome to Tech Weekly Issue #42.
In this edition, we explore distributed email forensics, RFC 2047 internationalization,
and zero-latency offline correlation engines.
Best regards,
The TechWeekly Editorial Staff
Mountain View, CA, USA
"""

f2 = """From: notifications@github.com
To: dev-leads@victimcorp.com
Subject: [GitHub] A security advisory was resolved in repository veritas/core
Date: Mon, 20 Oct 2026 11:20:00 +0000
Message-ID: <gh-alert-99182@github.com>
Authentication-Results: mx.victimcorp.com; dkim=pass header.i=@github.com; dmarc=pass
Received: from out-1.smtp.github.com (out-1.smtp.github.com [192.30.252.201])
    by mx.victimcorp.com with ESMTPS id gh99182
    for <dev-leads@victimcorp.com>;
    Mon, 20 Oct 2026 11:20:02 +0000
Content-Type: text/plain; charset="utf-8"

Hi @team,
A dependable security patch has been merged into main branch.
All unit tests and regression gates passed successfully.
GitHub Security Team
San Francisco, CA, USA
"""

f3 = """From: statements@firstnational-alerts.com
To: accounting@victimcorp.com
Subject: Your Monthly Enterprise Statement Is Ready for Download
Date: Tue, 21 Oct 2026 08:00:00 +0000
Message-ID: <ses-stmt-20261021@firstnational-alerts.com>
Authentication-Results: mx.victimcorp.com; dkim=pass header.i=@firstnational-alerts.com; spf=pass (amazonses.com: 54.240.8.42 designates amazonses)
Received: from a8-42.smtp-out.amazonses.com (a8-42.smtp-out.amazonses.com [54.240.8.42])
    by mx.victimcorp.com with ESMTPS id ses10293
    for <accounting@victimcorp.com>;
    Tue, 21 Oct 2026 08:00:03 +0000
Content-Type: text/plain; charset="utf-8"

Dear Accounting Partner,
Your monthly statement for period ending October 2026 is ready.
You may review it inside your authenticated banking dashboard.
First National Client Services
New York, NY, USA
"""

f4 = """From: pm@partnercompany.com
To: engineers@victimcorp.com
Subject: Invitation: Architecture Review Sync @ Wed 10am
Date: Tue, 21 Oct 2026 14:00:00 +0000
Message-ID: <cal-inv-5544@partnercompany.com>
Received: from mail.partnercompany.com (mail.partnercompany.com [198.51.100.15])
    by mx.victimcorp.com with ESMTPS id cal778
    for <engineers@victimcorp.com>;
    Tue, 21 Oct 2026 14:00:04 +0000
Content-Type: multipart/alternative; boundary="boundary_cal_44"

--boundary_cal_44
Content-Type: text/plain; charset="utf-8"

Please join us for the Q4 Architecture Review Sync.
Wednesday, October 22, 2026 at 10:00 AM UTC.
--boundary_cal_44
Content-Type: text/html; charset="utf-8"

<html><body><p>Please join us for the <b>Q4 Architecture Review Sync</b>.</p></body></html>
--boundary_cal_44
Content-Type: text/calendar; method=REQUEST; charset="utf-8"

BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//PartnerCompany//Calendar Sync//EN
BEGIN:VEVENT
SUMMARY:Architecture Review Sync
DTSTART:20261022T100000Z
DTEND:20261022T110000Z
END:VEVENT
END:VCALENDAR
--boundary_cal_44--
"""

f5 = """From: offers@cloudtools-marketing.net
To: subscriber@victimcorp.com
Subject: Unlock Your Team Collaboration Cloud Workspace
Date: Wed, 22 Oct 2026 10:30:00 +0000
Message-ID: <mkt-7788@cloudtools-marketing.net>
Received: from mkt-rel.cloudtools-marketing.net (mkt-rel.cloudtools-marketing.net [198.51.100.22])
    by mx.victimcorp.com with ESMTPS id mkt7788
    for <subscriber@victimcorp.com>;
    Wed, 22 Oct 2026 10:30:03 +0000
Content-Type: text/html; charset="utf-8"

<!DOCTYPE html>
<html>
<body>
  <h2>Empower your security workflow</h2>
  <p>Learn how top incident responders automate triage and investigation.</p>
  <p><a href="https://cloudtools-marketing.net/upgrade">Explore Features & Pricing</a></p>
  <p><a href="https://cloudtools-marketing.net/unsubscribe">Unsubscribe</a></p>
</body>
</html>
"""

f6 = """From: alice.analyst@victimcorp.com
To: phish-report@veritas.internal
Subject: FW: Action Required: Confirm Outlook 365 Password Reset
Date: Wed, 22 Oct 2026 16:45:00 +0000
Message-ID: <fwd-report-001@victimcorp.com>
Received: from mail.victimcorp.com (mail.victimcorp.com [10.0.0.5])
    by soc-ingest.victimcorp.com with ESMTP id rpt1234
    for <phish-report@veritas.internal>;
    Wed, 22 Oct 2026 16:45:01 +0000
Content-Type: multipart/mixed; boundary="fwd_boundary_99"

--fwd_boundary_99
Content-Type: text/plain; charset="utf-8"

Forwarding suspicious phishing lure received by employee inbox.
Employee clicked nothing. Origin looks like rogue bulletproof host.
--fwd_boundary_99
Content-Type: message/rfc822
Content-Disposition: attachment; filename="suspicious_lure.eml"

From: admin@micr0soft-portal.xyz
To: alice.analyst@victimcorp.com
Subject: Action Required: Confirm Outlook 365 Password Reset
Date: Wed, 22 Oct 2026 16:40:00 +0000
Message-ID: <inner-lure-8877@micr0soft-portal.xyz>
Received: from attack-node.xyz (attack-node.xyz [185.220.101.44])
    by mx.victimcorp.com with ESMTP id in1092
    for <alice.analyst@victimcorp.com>;
    Wed, 22 Oct 2026 16:40:02 +0000
Content-Type: text/plain; charset="utf-8"

Your Microsoft 365 corporate account will be suspended within 24 hours.
Click below to verify your credentials:
http://micr0soft-portal.xyz/login
Microsoft Security Team
--fwd_boundary_99--
"""

f7 = """From: =?UTF-8?B?4KSo4KS14KWA4KSoIOCkleClgeCkruCkvuCksA==?= <navin@globalvendor.in>
To: procurement@victimcorp.com
Subject: =?UTF-8?B?4KS44KWB4KSw4KSV4KWN4KS34KS+IOCkquCljeClgOCkruClh+CkguCknw==?= (Security Payment Notice) =?UTF-8?B?5a6J5YWo5Y2P6K6u?= (Safety Protocol)
Date: Thu, 23 Oct 2026 07:15:00 +0000
Message-ID: <multi-lang-776@globalvendor.in>
Received: from mail.globalvendor.in (mail.globalvendor.in [203.0.113.60])
    by mx.victimcorp.com with ESMTPS id multi776
    for <procurement@victimcorp.com>;
    Thu, 23 Oct 2026 07:15:03 +0000
Content-Type: text/plain; charset="utf-8"

नमस्ते (Namaste),
कृपया इस चालान की सुरक्षा समीक्षा करें।
您好 (Hello),
请查看最新的安全协议文档。
Best regards,
Navin Kumar
Mumbai, Maharashtra, India
"""

f8 = """From: security@micros0ft-portal.online
To: user@victimcorp.com
Subject: CRITICAL: Your Active Directory session will terminate in 1 hour
Date: Thu, 23 Oct 2026 12:00:00 +0000
Message-ID: <lure-link-994@micros0ft-portal.online>
Received: from rogue-vps.net (rogue-vps.net [185.220.101.99])
    by mx.victimcorp.com with ESMTP id rogue994
    for <user@victimcorp.com>;
    Thu, 23 Oct 2026 12:00:02 +0000
Content-Type: text/html; charset="utf-8"

<!DOCTYPE html>
<html>
<body>
  <h3>Your corporate account requires immediate password synchronization</h3>
  <p>Please authenticate immediately using the link below:</p>
  <p><a href="http://198.51.100.99/auth/login">https://portal.office.com/auth/login</a></p>
  <p>Alternative mirror: <a href="https://bit.ly/3xyz45">Shortened Security Link</a></p>
  <p>IT Helpdesk Support, Redmond, WA, USA</p>
</body>
</html>
"""

dummy_script_b64 = base64.b64encode(b"// Benign security test script for extension detection\nconsole.log('test');\n").decode('ascii')

f9 = f"""From: billing@swift-deliveries.biz
To: payroll@victimcorp.com
Subject: Overdue Invoice #INV-90214 with Wire Instructions
Date: Thu, 23 Oct 2026 15:30:00 +0000
Message-ID: <invoice-att-5541@swift-deliveries.biz>
Received: from rogue-sender.org (rogue-sender.org [198.51.100.77])
    by mx.victimcorp.com with ESMTP id att5541
    for <payroll@victimcorp.com>;
    Thu, 23 Oct 2026 15:30:03 +0000
Content-Type: multipart/mixed; boundary="att_boundary_88"

--att_boundary_88
Content-Type: text/plain; charset="utf-8"

Please find attached the signed contract and invoice statement.
Prompt settlement is required.
Accounts Payable
--att_boundary_88
Content-Type: application/octet-stream; name="Invoice_90214.pdf.js"
Content-Disposition: attachment; filename="Invoice_90214.pdf.js"
Content-Transfer-Encoding: base64

{dummy_script_b64}
--att_boundary_88--
"""

readme = """# VERITAS Real Email Test Fixtures

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
"""

files = {
    '01_gmail_newsletter.eml': f1,
    '02_github_notification.eml': f2,
    '03_bank_legitimate_esp.eml': f3,
    '04_multipart_calendar_invite.eml': f4,
    '05_html_only_marketing.eml': f5,
    '06_forwarded_abuse_report.eml': f6,
    '07_multilingual_hindi_chinese.eml': f7,
    '08_credential_harvest_lure.eml': f8,
    '09_malicious_attachment_lure.eml': f9,
    'README.md': readme
}

if __name__ == '__main__':
    for name, text in files.items():
        p = os.path.join(fixtures_dir, name)
        with open(p, 'w', encoding='utf-8') as f:
            f.write(text.strip() + '\n')
        print(f'Wrote {name}')
    print('All real fixtures generated successfully.')
