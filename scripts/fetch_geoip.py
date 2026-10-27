"""
VERITAS - DB-IP Lite Offline GeoIP & ASN Database Fetcher

ATTRIBUTION & LICENSE NOTICE:
=============================
This product includes DB-IP Lite data created by DB-IP (https://db-ip.com),
licensed under the Creative Commons Attribution 4.0 International License (CC BY 4.0).
To view a copy of this license, visit:
https://creativecommons.org/licenses/by/4.0/

Usage:
    python scripts/fetch_geoip.py [--month YYYY-MM] [--dest backend/app/data/geoip]
"""

import os
import sys
import gzip
import shutil
import datetime
import argparse
import urllib.request
from pathlib import Path

ATTRIBUTION_TEXT = """
================================================================================
DB-IP LITE LICENSE & ATTRIBUTION (CC BY 4.0):
"This product includes DB-IP Lite data created by DB-IP (https://db-ip.com)"
Distributed under Creative Commons Attribution 4.0 International License.
================================================================================
"""

def get_default_dest():
    base_dir = Path(__file__).resolve().parent.parent
    return base_dir / "backend" / "app" / "data" / "geoip"

def download_and_extract(url: str, output_path: Path):
    print(f"[*] Downloading from: {url}")
    temp_gz = output_path.with_suffix(".mmdb.gz.tmp")
    
    headers = {
        "User-Agent": "VERITAS-Email-Forensics/1.0 (Educational Security Research; https://github.com/veritas)"
    }
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req, timeout=60) as resp, open(temp_gz, "wb") as f_out:
            shutil.copyfileobj(resp, f_out)
            
        print(f"[*] Extracting to: {output_path}")
        with gzip.open(temp_gz, "rb") as gz_in, open(output_path, "wb") as f_out:
            shutil.copyfileobj(gz_in, f_out)
            
        if temp_gz.exists():
            temp_gz.unlink()
        print(f"[+] Successfully installed: {output_path.name} ({output_path.stat().st_size:,} bytes)")
        return True
    except Exception as e:
        if temp_gz.exists():
            temp_gz.unlink()
        print(f"[-] Failed to download/extract {url}: {e}", file=sys.stderr)
        return False

def main():
    parser = argparse.ArgumentParser(description="Fetch DB-IP Lite City and ASN MMDB databases.")
    parser.add_argument("--month", default=None, help="Year-Month for DB-IP release (e.g. 2026-10). Defaults to current/previous month.")
    parser.add_argument("--dest", default=None, help="Target destination directory for MMDB files.")
    args = parser.parse_args()

    print(ATTRIBUTION_TEXT)
    
    target_dir = Path(args.dest) if args.dest else get_default_dest()
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # Determine target month
    now = datetime.datetime.now(datetime.timezone.utc)
    months_to_try = []
    if args.month:
        months_to_try.append(args.month)
    else:
        current_ym = now.strftime("%Y-%m")
        # Previous month
        first_of_month = now.replace(day=1)
        prev_month = (first_of_month - datetime.timedelta(days=1)).strftime("%Y-%m")
        months_to_try = [current_ym, prev_month]
        
    databases = [
        ("city", "dbip-city-lite", target_dir / "dbip-city-lite.mmdb"),
        ("asn", "dbip-asn-lite", target_dir / "dbip-asn-lite.mmdb")
    ]
    
    for db_type, db_prefix, dest_file in databases:
        success = False
        for ym in months_to_try:
            url = f"https://download.db-ip.com/free/{db_prefix}-{ym}.mmdb.gz"
            if download_and_extract(url, dest_file):
                success = True
                break
        if not success:
            print(f"[!] Warning: Could not download {db_type} database for months {months_to_try}.", file=sys.stderr)
            print(f"    You may manually place '{dest_file.name}' into '{target_dir}'.")

if __name__ == "__main__":
    main()
