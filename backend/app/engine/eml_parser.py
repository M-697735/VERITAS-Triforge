import email
import email.policy
from email.utils import parseaddr
from email.header import decode_header
import hashlib
import re
import ipaddress
from html.parser import HTMLParser
from urllib.parse import urlparse
from typing import Dict, Any, List, Tuple, Optional

def decode_rfc2047(header_val: Any) -> str:
    """
    Decodes RFC 2047 encoded header values with safe fallbacks:
    1. declared charset
    2. UTF-8
    3. errors='replace'
    Supports UTF-8, Hindi (Devanagari), Chinese (GB2312/GBK/Big5), etc.
    """
    if not header_val:
        return ""
    val_str = str(header_val)
    try:
        decoded_parts = decode_header(val_str)
        text_parts = []
        for content, encoding in decoded_parts:
            if isinstance(content, bytes):
                enc = (encoding or "utf-8").lower()
                try:
                    text_parts.append(content.decode(enc, errors="replace"))
                except (LookupError, UnicodeDecodeError):
                    try:
                        text_parts.append(content.decode("utf-8", errors="replace"))
                    except Exception:
                        text_parts.append(content.decode("latin-1", errors="replace"))
            else:
                text_parts.append(str(content))
        return " ".join(text_parts).strip()
    except Exception:
        return str(val_str)

def defang_url(url: str) -> str:
    """Defangs a URL for safe forensic display without clickable execution."""
    if not url:
        return ""
    defanged = re.sub(r'^http://', 'hxxp://', url, flags=re.IGNORECASE)
    defanged = re.sub(r'^https://', 'hxxps://', defanged, flags=re.IGNORECASE)
    defanged = defanged.replace('.', '[.]')
    return defanged

class EmailHTMLParser(HTMLParser):
    """Stdlib HTML Parser that extracts visible text and structured links."""
    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.links = []
        self._current_href = None
        self._current_text = []
        self._ignore_tag = False

    def handle_starttag(self, tag, attrs):
        tag_lower = tag.lower()
        if tag_lower in ("script", "style", "head", "title"):
            self._ignore_tag = True
            return

        if tag_lower == "a":
            href = None
            for k, v in attrs:
                if k.lower() == "href" and v:
                    href = v.strip()
                    break
            self._current_href = href
            self._current_text = []

    def handle_endtag(self, tag):
        tag_lower = tag.lower()
        if tag_lower in ("script", "style", "head", "title"):
            self._ignore_tag = False
            return

        if tag_lower == "a":
            if self._current_href:
                anchor_text = "".join(self._current_text).strip()
                self._record_link(anchor_text, self._current_href)
            self._current_href = None
            self._current_text = []
        elif tag_lower in ("p", "br", "div", "tr", "li", "h1", "h2", "h3", "h4", "h5", "h6"):
            self.text_parts.append("\n")

    def handle_data(self, data):
        if not self._ignore_tag:
            self.text_parts.append(data)
            if self._current_href is not None:
                self._current_text.append(data)

    def _record_link(self, display_text: str, href: str):
        if not href or href.startswith(("javascript:", "mailto:", "#")):
            return
            
        parsed = urlparse(href)
        destination_domain = (parsed.netloc or "").lower().split(":")[0].strip()
        
        # Check if display text contains a domain/URL
        display_domain = None
        disp_parsed = urlparse(display_text if display_text.startswith(("http://", "https://")) else f"http://{display_text}")
        if disp_parsed.netloc and "." in disp_parsed.netloc:
            # Only consider it a display domain if it looks like a valid hostname
            pot_dom = disp_parsed.netloc.lower().split(":")[0].strip()
            if re.match(r'^[a-z0-9.-]+\.[a-z]{2,}$', pot_dom):
                display_domain = pot_dom

        self.links.append({
            "display_text": display_text or href,
            "href": href,
            "display_domain": display_domain,
            "destination_domain": destination_domain,
            "defanged_destination": defang_url(href)
        })

    def get_visible_text(self) -> str:
        return "".join(self.text_parts).strip()

def extract_signature_block(text: str) -> str:
    signoff_keywords = ["best regards", "regards", "sincerely", "thanks", "thank you", "cheers", "best"]
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    
    for idx, line in enumerate(lines):
        line_lower = line.lower()
        for kw in signoff_keywords:
            if line_lower.startswith(kw) or line_lower == kw:
                return "\n".join(lines[idx:])
                
    # Fallback: last 5 lines if text has >= 5 lines
    if len(lines) >= 5:
        return "\n".join(lines[-5:])
    return text

DEMO_PUBLIC_NETWORKS = [
    ipaddress.ip_network("192.0.2.0/24"),
    ipaddress.ip_network("198.51.100.0/24"),
    ipaddress.ip_network("203.0.113.0/24"),
    ipaddress.ip_network("2001:db8::/32")
]

def _is_public_ip(ip_obj: Any) -> bool:
    if ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_multicast or ip_obj.is_unspecified:
        return False
    for net in DEMO_PUBLIC_NETWORKS:
        if ip_obj in net:
            return True
    if ip_obj.is_private or ip_obj.is_reserved:
        return False
    return True

def extract_originating_ip(received_headers: List[str]) -> Optional[str]:
    """
    Extracts the bottom-most public originating IP address from Received headers.
    msg.get_all returns headers top-to-bottom (most recent first), so we iterate reversed.
    Returns None if no public IP is found (zero fallback claims).
    """
    ipv4_pattern = re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b')
    bracket_pattern = re.compile(r'\[([0-9a-fA-F:.]+)\]')
    ipv6_pattern = re.compile(r'\b(?:[0-9a-fA-F]{1,4}:){1,7}[0-9a-fA-F]{1,4}\b|\b::(?:[0-9a-fA-F]{1,4}:){0,6}[0-9a-fA-F]{1,4}\b')
    
    for header in reversed(received_headers):
        header_str = str(header)
        candidates = []
        
        # 1. Bracketed IPs (most common for hop definitions)
        for match in bracket_pattern.findall(header_str):
            candidates.append(match)
            
        # 2. IPv4
        for match in ipv4_pattern.findall(header_str):
            candidates.append(match)
            
        # 3. IPv6
        for match in ipv6_pattern.findall(header_str):
            candidates.append(match)
            
        for cand in candidates:
            cand = cand.strip()
            try:
                ip_obj = ipaddress.ip_address(cand)
                if _is_public_ip(ip_obj):
                    return str(ip_obj)
            except ValueError:
                continue
                
    return None

def extract_hops(received_headers: List[str]) -> List[Dict[str, Any]]:
    """Builds a complete, ordered list of hops for UI forensics display."""
    hops = []
    ipv4_pattern = re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b')
    bracket_pattern = re.compile(r'\[([0-9a-fA-F:.]+)\]')
    
    # Iterate from earliest (bottom) to latest (top)
    for idx, header in enumerate(reversed(received_headers)):
        header_str = str(header).replace("\r", " ").replace("\n", " ").strip()
        found_ip = None
        for cand in bracket_pattern.findall(header_str) + ipv4_pattern.findall(header_str):
            try:
                ip_obj = ipaddress.ip_address(cand.strip())
                found_ip = str(ip_obj)
                is_pub = _is_public_ip(ip_obj)
                break
            except ValueError:
                continue
        else:
            is_pub = False
            
        hops.append({
            "hop_index": idx + 1,
            "ip": found_ip,
            "is_public": is_pub,
            "raw_header": header_str[:300]
        })
    return hops

def parse_auth_results(msg: email.message.Message) -> Dict[str, Any]:
    """
    Parses topmost Authentication-Results, Received-SPF, and ARC-Authentication-Results.
    Topmost Authentication-Results is the receiving server's assertion.
    """
    auth_headers = msg.get_all("Authentication-Results", [])
    topmost_auth = str(auth_headers[0]) if auth_headers else ""
    
    authserv_id = None
    if topmost_auth:
        match_srv = re.match(r'^\s*([a-zA-Z0-9.-]+)\s*;', topmost_auth)
        if match_srv:
            authserv_id = match_srv.group(1).lower()

    received_spf = str(msg.get("Received-SPF", ""))
    arc_auth = str(msg.get("ARC-Authentication-Results", ""))
    
    assertion_note = f"as asserted by {authserv_id}" if authserv_id else "asserted by receiving gateway"

    return {
        "topmost_auth": topmost_auth,
        "authserv_id": authserv_id,
        "assertion_note": assertion_note,
        "received_spf": received_spf,
        "arc_auth": arc_auth,
        "all_auth_headers": [str(h) for h in auth_headers]
    }

def parse_eml(raw_bytes: bytes, depth: int = 0) -> Dict[str, Any]:
    """
    Robust RFC 822 email parser:
    - Decodes RFC 2047 multi-lingual headers
    - Unwraps forwarded-as-attachment reports (message/rfc822 or .eml) preserving reported_by
    - Collects ALL text/plain and text/html parts
    - Extracts links & defanged URLs via stdlib HTML parser
    - Extracts attachment metadata (sha256, size, content-type) without disk execution
    - Returns ordered hops and topmost gateway authentication assertions
    """
    sha256_hash = hashlib.sha256(raw_bytes).hexdigest()
    msg = email.message_from_bytes(raw_bytes, policy=email.policy.default)
    
    # Check for Forwarded-as-attachment (message/rfc822 or .eml attachment)
    is_forwarded_report = False
    reported_by = None
    outer_report_meta = None
    
    if depth == 0 and msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            cdisp = str(part.get("Content-Disposition", ""))
            fname = str(part.get_filename() or "")
            
            is_rfc822 = (ctype == "message/rfc822")
            is_eml_file = (fname.lower().endswith(".eml") or ("attachment" in cdisp and "message" in ctype))
            
            if is_rfc822 or is_eml_file:
                # Found inner email!
                inner_payload = part.get_payload()
                inner_bytes = None
                
                if isinstance(inner_payload, list) and inner_payload:
                    inner_bytes = inner_payload[0].as_bytes()
                elif isinstance(inner_payload, email.message.Message):
                    inner_bytes = inner_payload.as_bytes()
                elif isinstance(inner_payload, bytes):
                    inner_bytes = inner_payload
                else:
                    inner_bytes = part.get_payload(decode=True)
                    
                if inner_bytes and len(inner_bytes) > 20:
                    outer_from = decode_rfc2047(msg.get("From", ""))
                    _, outer_addr = parseaddr(outer_from)
                    reported_by = outer_addr or outer_from
                    outer_report_meta = {
                        "outer_subject": decode_rfc2047(msg.get("Subject", "(No Subject)")),
                        "outer_from": outer_from,
                        "outer_date": decode_rfc2047(msg.get("Date", "")),
                        "outer_message_id": decode_rfc2047(msg.get("Message-ID", "")),
                        "outer_sha256": sha256_hash
                    }
                    
                    # Recursively parse the inner email
                    inner_result = parse_eml(inner_bytes, depth=depth + 1)
                    inner_result["is_forwarded_report"] = True
                    inner_result["reported_by"] = reported_by
                    inner_result["outer_report_meta"] = outer_report_meta
                    return inner_result

    # Standard Headers with RFC 2047 Decoding
    from_header = decode_rfc2047(msg.get("From", ""))
    to_header = decode_rfc2047(msg.get("To", ""))
    reply_to_header = decode_rfc2047(msg.get("Reply-To", from_header))
    return_path_header = decode_rfc2047(msg.get("Return-Path", from_header))
    subject = decode_rfc2047(msg.get("Subject", "(No Subject)"))
    date = decode_rfc2047(msg.get("Date", ""))
    message_id = decode_rfc2047(msg.get("Message-ID", ""))
    dkim_signature = str(msg.get("DKIM-Signature", ""))
    
    # Parse addresses
    from_name, from_addr = parseaddr(from_header)
    reply_name, reply_addr = parseaddr(reply_to_header)
    return_name, return_addr = parseaddr(return_path_header)
    
    if not reply_addr:
        reply_addr = from_addr
    if not return_addr:
        return_addr = from_addr
        
    from_domain = from_addr.split("@")[-1].lower() if "@" in from_addr else ""
    reply_to_domain = reply_addr.split("@")[-1].lower() if "@" in reply_addr else ""
    return_path_domain = return_addr.split("@")[-1].lower() if "@" in return_addr else ""
    
    # Body and Attachments Extraction
    text_plain_parts = []
    text_html_parts = []
    attachments = []
    
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", ""))
            filename = part.get_filename()
            
            # Check if this part is an attachment
            is_attachment = ("attachment" in content_disposition.lower()) or bool(filename)
            
            if is_attachment:
                payload = part.get_payload(decode=True) or b""
                decoded_fname = decode_rfc2047(filename or "unnamed_attachment")
                attachments.append({
                    "filename": decoded_fname,
                    "content_type": content_type,
                    "size": len(payload),
                    "sha256": hashlib.sha256(payload).hexdigest()
                })
            else:
                if content_type == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        try:
                            text_plain_parts.append(payload.decode(charset, errors="replace"))
                        except LookupError:
                            text_plain_parts.append(payload.decode("utf-8", errors="replace"))
                elif content_type == "text/html":
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        try:
                            text_html_parts.append(payload.decode(charset, errors="replace"))
                        except LookupError:
                            text_html_parts.append(payload.decode("utf-8", errors="replace"))
    else:
        content_type = msg.get_content_type()
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            try:
                decoded_text = payload.decode(charset, errors="replace")
            except LookupError:
                decoded_text = payload.decode("utf-8", errors="replace")
                
            if content_type == "text/html":
                text_html_parts.append(decoded_text)
            else:
                text_plain_parts.append(decoded_text)
                
    body_text = "\n\n".join(text_plain_parts).strip()
    body_html = "\n\n".join(text_html_parts).strip()
    
    # HTML Parsing and Link Extraction
    links = []
    if body_html:
        html_parser = EmailHTMLParser()
        try:
            html_parser.feed(body_html)
            links = html_parser.links
            if not body_text:
                body_text = html_parser.get_visible_text()
        except Exception:
            pass

    # Also scan plain text for URLs
    url_pattern = re.compile(r'\bhttps?://[^\s<>"]+\b')
    for raw_url in url_pattern.findall(body_text):
        parsed = urlparse(raw_url)
        dest_domain = (parsed.netloc or "").lower().split(":")[0].strip()
        # Only add if not already captured in links
        if not any(l.get("href") == raw_url for l in links):
            links.append({
                "display_text": raw_url,
                "href": raw_url,
                "display_domain": dest_domain,
                "destination_domain": dest_domain,
                "defanged_destination": defang_url(raw_url)
            })

    # Extract signature block (lines after sign-off triggers)
    signature_block = extract_signature_block(body_text)
    
    # Received headers and IP extraction
    received_headers = msg.get_all("Received", [])
    originating_ip = extract_originating_ip(received_headers)
    hops = extract_hops(received_headers)
    
    # Authentication Results
    auth_info = parse_auth_results(msg)
    auth_results = auth_info["topmost_auth"]
    
    return {
        "sha256_hash": sha256_hash,
        "subject": subject,
        "date": date,
        "message_id": message_id,
        "from_header": from_header,
        "to_header": to_header,
        "from_name": from_name,
        "from_addr": from_addr,
        "from_domain": from_domain,
        "reply_to_header": reply_to_header,
        "reply_addr": reply_addr,
        "reply_to_domain": reply_to_domain,
        "return_path_header": return_path_header,
        "return_addr": return_addr,
        "return_path_domain": return_path_domain,
        "auth_results": auth_results,
        "auth_details": auth_info,
        "dkim_signature": dkim_signature,
        "body_text": body_text,
        "body_html": body_html,
        "signature_block": signature_block,
        "received_headers": [str(r) for r in received_headers],
        "originating_ip": originating_ip,
        "hops": hops,
        "links": links,
        "attachments": attachments,
        "is_forwarded_report": is_forwarded_report,
        "reported_by": reported_by,
        "outer_report_meta": outer_report_meta,
        "raw_bytes": raw_bytes
    }
