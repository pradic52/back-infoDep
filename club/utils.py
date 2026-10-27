import ipaddress
import re

from django.conf import settings


# ---------------------------------------------------------------------------
# Estimation pour les statistiques : 157 -> "150+", 23 -> "20+"
# ---------------------------------------------------------------------------
def estimate(n: int) -> dict:
    n = max(int(n), 0)
    if n == 0:
        return {"value": 0, "display": "0"}
    if n < 10:
        step = 1
    elif n < 50:
        step = 5
    elif n < 100:
        step = 10
    elif n < 500:
        step = 50
    elif n < 1000:
        step = 100
    else:
        step = 500
    floor = (n // step) * step
    return {"value": floor, "display": f"{floor}+"}


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------
def client_ip(request) -> str:
    if getattr(settings, "TRUST_X_FORWARDED_FOR", False):
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def mask_ip(ip: str) -> str:
    """192.168.12.34 -> 192.168.12.0 ; IPv6 -> préfixe /48."""
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return ""
    prefix = 24 if addr.version == 4 else 48
    return str(ipaddress.ip_network(f"{ip}/{prefix}", strict=False).network_address)


_geoip_reader = None


def geolocate(ip: str, request) -> dict:
    """Pays/région/ville. Utilise GeoLite2 si GEOIP_DB_PATH est défini, sinon
    l'en-tête CF-IPCountry (Cloudflare) s'il existe. L'IP complète n'est pas stockée."""
    global _geoip_reader
    result = {"country": "", "country_code": "", "region": "", "city": ""}
    path = getattr(settings, "GEOIP_DB_PATH", None)
    if path and ip:
        try:
            import geoip2.database

            if _geoip_reader is None:
                _geoip_reader = geoip2.database.Reader(str(path))
            r = _geoip_reader.city(ip)
            result.update(
                country=r.country.name or "",
                country_code=r.country.iso_code or "",
                region=r.subdivisions.most_specific.name or "",
                city=r.city.name or "",
            )
        except Exception:
            pass
    if not result["country_code"]:
        cf = request.META.get("HTTP_CF_IPCOUNTRY", "")
        if len(cf) == 2 and cf.upper() not in ("XX", "T1"):
            result["country_code"] = cf.upper()
    return result


def parse_user_agent(ua: str) -> dict:
    ua = ua or ""
    low = ua.lower()
    if "ipad" in low or "tablet" in low:
        device = "tablet"
    elif "mobi" in low or "iphone" in low or "android" in low:
        device = "mobile"
    elif re.search(r"bot|crawl|spider|slurp", low):
        device = "bot"
    else:
        device = "desktop"

    if "edg/" in low or "edge/" in low:
        browser = "Edge"
    elif "opr/" in low or "opera" in low:
        browser = "Opera"
    elif "firefox" in low or "fxios" in low:
        browser = "Firefox"
    elif "chrome" in low or "crios" in low:
        browser = "Chrome"
    elif "safari" in low:
        browser = "Safari"
    else:
        browser = "Autre"

    if "windows" in low:
        os_name = "Windows"
    elif "android" in low:
        os_name = "Android"
    elif "iphone" in low or "ipad" in low or "ios" in low:
        os_name = "iOS"
    elif "mac os" in low or "macintosh" in low:
        os_name = "macOS"
    elif "linux" in low:
        os_name = "Linux"
    else:
        os_name = "Autre"
    return {"device_type": device, "browser": browser, "os": os_name}
