import re
from urllib.parse import urlparse

try:
    from ddgs import DDGS
except Exception:
    DDGS = None

BLOCKED_HOSTS = {
    "facebook.com", "www.facebook.com", "instagram.com", "www.instagram.com",
    "linkedin.com", "www.linkedin.com", "pagesjaunes.fr", "www.pagesjaunes.fr",
    "tripadvisor.fr", "www.tripadvisor.fr", "societe.com", "www.societe.com",
    "verif.com", "www.verif.com", "pappers.fr", "www.pappers.fr",
    "google.com", "www.google.com", "maps.google.com", "x.com", "twitter.com",
    "youtube.com", "www.youtube.com"
}


def _tokens(value):
    return {
        t for t in re.findall(r"[a-z0-9]{3,}", (value or "").lower())
        if t not in {"sas", "sarl", "eurl", "sa", "sasu", "france", "entreprise", "societe"}
    }


def _host(url):
    try:
        h = (urlparse(url).hostname or "").lower().strip(".")
        return h[4:] if h.startswith("www.") else h
    except Exception:
        return ""


def discover_official_website(company_name, city=None, max_results=8):
    """Best-effort discovery of a likely official website from public web results."""
    if not company_name or DDGS is None:
        return None

    query = f'"{company_name}" {city or ""} site officiel contact'.strip()
    company_tokens = _tokens(company_name)
    city_tokens = _tokens(city)
    ranked = []

    try:
        results = DDGS().text(query, region="fr-fr", safesearch="moderate", max_results=max_results)
        for item in results or []:
            url = item.get("href") or item.get("url")
            if not url:
                continue
            host = _host(url)
            if not host or host in BLOCKED_HOSTS or any(host.endswith("." + b) for b in BLOCKED_HOSTS):
                continue

            haystack = " ".join([host, item.get("title", ""), item.get("body", "")]).lower()
            score = 0
            score += 4 * sum(1 for t in company_tokens if t in haystack)
            score += 1 * sum(1 for t in city_tokens if t in haystack)
            if any(k in haystack for k in ("contact", "officiel", "accueil", "cabinet", "agence")):
                score += 2
            if host.endswith(".fr"):
                score += 1
            ranked.append((score, url))
    except Exception:
        return None

    if not ranked:
        return None
    ranked.sort(key=lambda x: x[0], reverse=True)
    return ranked[0][1] if ranked[0][0] >= 4 else None
