import json
import os
import glob
import datetime
import urllib.request
import ipaddress
from typing import Dict, Any, Optional, Tuple
from app.engine.status_taxonomy import evaluate_layer4_status

GEO_DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'geo_db.json')
DOMAIN_REG_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'domain_registry.json')
KNOWN_PROVIDERS_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'known_providers.json')
GEOIP_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'geoip')
RDAP_CACHE_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'rdap_cache.json')

_geo_db = None
_domain_reg = None
_known_providers = None
_mmdb_city_reader = None
_mmdb_asn_reader = None
_checked_mmdb = False

def get_geo_db():
    global _geo_db
    if _geo_db is None:
        if os.path.exists(GEO_DB_PATH):
            with open(GEO_DB_PATH, 'r', encoding='utf-8') as f:
                _geo_db = json.load(f)
        else:
            _geo_db = {}
    return _geo_db

def get_domain_reg():
    global _domain_reg
    if _domain_reg is None:
        if os.path.exists(DOMAIN_REG_PATH):
            with open(DOMAIN_REG_PATH, 'r', encoding='utf-8') as f:
                _domain_reg = json.load(f)
        else:
            _domain_reg = {}
    return _domain_reg

def get_known_providers():
    global _known_providers
    if _known_providers is None:
        if os.path.exists(KNOWN_PROVIDERS_PATH):
            try:
                with open(KNOWN_PROVIDERS_PATH, 'r', encoding='utf-8') as f:
                    _known_providers = json.load(f)
            except Exception:
                _known_providers = []
        else:
            _known_providers = []
    return _known_providers

def get_mmdb_readers():
    global _mmdb_city_reader, _mmdb_asn_reader, _checked_mmdb
    if not _checked_mmdb:
        _checked_mmdb = True
        try:
            import maxminddb
            if os.path.exists(GEOIP_DIR):
                city_files = glob.glob(os.path.join(GEOIP_DIR, "*city*.mmdb"))
                asn_files = glob.glob(os.path.join(GEOIP_DIR, "*asn*.mmdb"))
                if city_files:
                    _mmdb_city_reader = maxminddb.open_database(city_files[0])
                if asn_files:
                    _mmdb_asn_reader = maxminddb.open_database(asn_files[0])
        except Exception:
            _mmdb_city_reader = None
            _mmdb_asn_reader = None
    return _mmdb_city_reader, _mmdb_asn_reader

def lookup_real_mmdb(ip: str) -> Optional[Dict[str, Any]]:
    city_reader, asn_reader = get_mmdb_readers()
    if not city_reader and not asn_reader:
        return None
        
    result = {}
    has_data = False
    
    if city_reader:
        try:
            cdata = city_reader.get(ip)
            if cdata:
                has_data = True
                city_names = cdata.get("city", {}).get("names", {})
                country_names = cdata.get("country", {}).get("names", {})
                city = city_names.get("en") or "Unknown City"
                country = country_names.get("en") or "Unknown Country"
                loc = cdata.get("location", {})
                accuracy_radius_km = loc.get("accuracy_radius")
                result["city"] = city
                result["country"] = country
                result["accuracy_radius_km"] = accuracy_radius_km
        except Exception:
            pass

    if asn_reader:
        try:
            adata = asn_reader.get(ip)
            if adata:
                has_data = True
                asn_num = adata.get("autonomous_system_number")
                asn_org = adata.get("autonomous_system_organization") or "Unknown ASN"
                result["asn"] = f"AS{asn_num}" if asn_num else "Unknown ASN"
                result["asn_org"] = asn_org
        except Exception:
            pass
            
    if has_data:
        return result
    return None

KNOWN_PROVIDER_IP_RANGES = [
    ("Google LLC", "AS15169", [
        ipaddress.ip_network("209.85.128.0/17"),
        ipaddress.ip_network("172.217.0.0/16"),
        ipaddress.ip_network("142.250.0.0/15"),
        ipaddress.ip_network("74.125.0.0/16"),
    ]),
    ("Microsoft Corporation", "AS8075", [
        ipaddress.ip_network("40.92.0.0/15"),
        ipaddress.ip_network("52.100.0.0/14"),
        ipaddress.ip_network("104.47.0.0/17"),
        ipaddress.ip_network("192.30.252.0/22"),
    ]),
    ("Amazon.com (AWS / SES)", "AS16509", [
        ipaddress.ip_network("54.240.0.0/18"),
        ipaddress.ip_network("69.169.224.0/20"),
    ]),
    ("Twilio SendGrid", "AS11377", [
        ipaddress.ip_network("167.89.0.0/17"),
        ipaddress.ip_network("198.21.0.0/21"),
    ]),
]

def match_known_provider_by_ip(ip_str: str) -> Optional[Dict[str, Any]]:
    if not ip_str:
        return None
    try:
        ip_obj = ipaddress.ip_address(ip_str)
    except ValueError:
        return None
        
    for prov_name, prov_asn, networks in KNOWN_PROVIDER_IP_RANGES:
        for net in networks:
            if ip_obj in net:
                return {
                    "asn": prov_asn,
                    "provider": prov_name,
                    "verification_source": "Known ESP CIDR Range"
                }
    return None

def check_major_mail_provider(asn: str, asn_org: str) -> Optional[Dict[str, Any]]:
    providers = get_known_providers()
    asn_clean = (asn or "").strip().upper()
    org_clean = (asn_org or "").lower()
    
    for p in providers:
        p_asn = p.get("asn", "").strip().upper()
        p_name = p.get("provider", "")
        if p_asn and p_asn == asn_clean:
            return p
        if p_name.lower() in org_clean:
            return p
    return None

def lookup_rdap_domain_age(from_domain: str) -> Optional[Tuple[int, str]]:
    """Performs Live RDAP query for domain age with safe fallback and cache."""
    if not from_domain or "." not in from_domain:
        return None
        
    cache = {}
    if os.path.exists(RDAP_CACHE_PATH):
        try:
            with open(RDAP_CACHE_PATH, 'r', encoding='utf-8') as f:
                cache = json.load(f)
        except Exception:
            cache = {}
            
    if from_domain in cache:
        cached = cache[from_domain]
        return cached.get("domain_age_days"), cached.get("registrar", "RDAP Registry")
        
    url = f"https://rdap.org/domain/{from_domain}"
    req = urllib.request.Request(url, headers={"User-Agent": "VERITAS-Forensics/1.0", "Accept": "application/json"})
    
    try:
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            data = json.loads(resp.read().decode('utf-8', errors='replace'))
            events = data.get("events", [])
            reg_date_str = None
            for ev in events:
                if ev.get("eventAction") in ("registration", "created"):
                    reg_date_str = ev.get("eventDate")
                    break
                    
            if reg_date_str:
                # e.g. "2020-05-15T00:00:00Z"
                reg_dt = datetime.datetime.fromisoformat(reg_date_str.replace("Z", "+00:00"))
                now = datetime.datetime.now(datetime.timezone.utc)
                age_days = (now - reg_dt).days
                registrar = "RDAP Verified Registrar"
                for ent in data.get("entities", []):
                    if "registrar" in ent.get("roles", []):
                        fn = ent.get("vcardArray", [None, [["fn", {}, "text", "RDAP Registrar"]]])
                        try:
                            registrar = fn[1][0][3]
                        except Exception:
                            pass
                cache[from_domain] = {"domain_age_days": age_days, "registrar": registrar}
                try:
                    with open(RDAP_CACHE_PATH, 'w', encoding='utf-8') as f:
                        json.dump(cache, f, indent=2)
                except Exception:
                    pass
                return age_days, registrar
    except Exception:
        pass
    return None

def analyze_layer4(parsed_eml: Dict[str, Any], live_reverify: bool = False) -> Dict[str, Any]:
    ip = parsed_eml.get("originating_ip")
    from_domain = parsed_eml.get("from_domain", "")
    
    geo_db = get_geo_db()
    domain_reg = get_domain_reg()
    
    # 1. IP GeoIP & ASN Lookup
    geoip_source = "simulated_dataset"
    
    if ip is None:
        is_resolved = False
        city = "Unresolved Location"
        country = "Unresolved Country"
        accuracy_radius_km = None
        asn = "Unresolved ASN"
        asn_org = "No originating IP found in Received headers"
        is_datacenter = False
        infra_category = "no_origin_ip"
        geoip_source = "unresolved"
    else:
        # Check real offline MMDB first if present
        mmdb_res = lookup_real_mmdb(ip)
        if mmdb_res:
            is_resolved = True
            city = mmdb_res.get("city", "Unresolved Location")
            country = mmdb_res.get("country", "Unresolved Country")
            accuracy_radius_km = mmdb_res.get("accuracy_radius_km")
            asn = mmdb_res.get("asn", "Unresolved ASN")
            asn_org = mmdb_res.get("asn_org", "Unresolved ASN")
            is_datacenter = False
            infra_category = "isp_network"
            geoip_source = "real_database"
        elif ip in geo_db and ip != "_meta":
            is_resolved = True
            ip_info = geo_db[ip]
            city = ip_info.get("city", "Unresolved Location")
            country = ip_info.get("country", "Unresolved Country")
            accuracy_radius_km = ip_info.get("accuracy_radius_km", 50)
            asn = ip_info.get("asn", "Unresolved ASN")
            asn_org = ip_info.get("asn_org", "Unresolved ASN Provider")
            is_datacenter = ip_info.get("is_datacenter", True)
            infra_category = ip_info.get("infra_category", "hosting_datacenter")
            geoip_source = "simulated_dataset"
        elif match_known_provider_by_ip(ip):
            prov = match_known_provider_by_ip(ip)
            is_resolved = True
            city = "Estimated Mail Egress"
            country = "United States"
            accuracy_radius_km = None
            asn = prov.get("asn", "AS15169")
            asn_org = f"{prov.get('provider')} (Legitimate Mail Provider)"
            is_datacenter = False
            infra_category = "major_mail_provider"
            geoip_source = "real_database"
        else:
            # Honest unresolved state — ZERO false claims, no fake accuracy radius
            is_resolved = False
            city = "Unresolved Location"
            country = "Unresolved Country"
            accuracy_radius_km = None
            asn = "Unresolved ASN"
            asn_org = "No local database match — origin cannot be resolved offline"
            is_datacenter = False
            infra_category = "unresolved_origin"
            geoip_source = "unresolved"

    # 2. Check Major Mail Provider Networks (Google, Microsoft, Amazon SES, SendGrid, etc.)
    # Applies to real emails/MMDB lookups, preserving bundled demo sample ground truth in geo_db.json
    if is_resolved and geoip_source != "simulated_dataset":
        provider_match = check_major_mail_provider(asn, asn_org)
        if provider_match:
            infra_category = "major_mail_provider"
            is_datacenter = False
            asn_org = f"{provider_match.get('provider')} (Legitimate Mail Provider)"

    # 3. Domain Registration Age Lookup
    domain_age_days = None
    registrar = "Unknown (not in offline registry)"
    
    if live_reverify:
        rdap_res = lookup_rdap_domain_age(from_domain)
        if rdap_res:
            domain_age_days, registrar = rdap_res
            
    if domain_age_days is None:
        if from_domain in domain_reg:
            dom_info = domain_reg[from_domain]
            domain_age_days = dom_info.get("domain_age_days")
            registrar = dom_info.get("registrar", "Standard Registrar Inc.")

    # 4. Central Status Taxonomy Evaluation
    status = evaluate_layer4_status(infra_category, is_datacenter, domain_age_days, is_resolved=is_resolved)
    
    status_reasons = []
    if ip is None:
        status_reasons.append("No originating IP found in Received headers.")
    elif not is_resolved:
        status_reasons.append("No local offline GeoIP record found for this IP.")
    elif infra_category == "major_mail_provider":
        status_reasons.append(f"Originating IP belongs to a verified legitimate major mail provider ({asn_org}).")
    elif infra_category == "hosting_datacenter" or is_datacenter:
        status_reasons.append("Originating IP belongs to a hosting/datacenter infrastructure ASN.")
    elif infra_category == "vpn_exit":
        status_reasons.append("Originating IP belongs to an anonymizing VPN exit node.")
    elif domain_age_days is not None and domain_age_days < 30:
        status_reasons.append(f"Domain registered recently ({domain_age_days} days old).")
    elif domain_age_days is None:
        status_reasons.append("Domain registration age unknown (not in offline registry).")
    else:
        status_reasons.append("Legitimate residential/corporate ISP with established domain age.")
        
    if ip is None:
        summary = "No originating IP found in Received headers"
    elif is_resolved:
        radius_str = f" ±{accuracy_radius_km}km" if accuracy_radius_km is not None else ""
        age_str = f"{domain_age_days} days" if domain_age_days is not None else "Unknown"
        summary = f"IP: {ip} ({city}, {country}{radius_str}) | ASN: {asn} ({asn_org}) | Domain Age: {age_str}"
    else:
        age_str = f"{domain_age_days} days" if domain_age_days is not None else "Unknown"
        summary = f"IP: {ip} (Unresolved Offline GeoIP) | No local database match — origin cannot be resolved offline | Domain Age: {age_str}"
    
    # Conservative GeoIP Wording: City is explicitly a city-level estimate
    if is_resolved:
        if accuracy_radius_km is not None:
            region_label = f"Estimated region ({city}, {country} ±{accuracy_radius_km} km city-level estimate)"
        else:
            region_label = f"Estimated region ({city}, {country} city-level estimate)"
    else:
        region_label = "Unresolved region (Offline Database Limit)"

    return {
        "originating_ip": ip,
        "city": city,
        "country": country,
        "accuracy_radius_km": accuracy_radius_km,
        "asn": asn,
        "asn_org": asn_org,
        "is_datacenter": is_datacenter,
        "infra_category": infra_category,
        "is_resolved": is_resolved,
        "geoip_source": geoip_source,
        "from_domain": from_domain,
        "domain_age_days": domain_age_days,
        "registrar": registrar,
        "status": status,
        "summary": summary,
        "details": {
            "status_reasons": status_reasons,
            "region_display_label": region_label,
            "live_reverify_used": live_reverify,
            "live_note": "LIVE: network lookups" if live_reverify else "Offline mode active"
        }
    }
