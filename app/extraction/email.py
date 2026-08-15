import re
from urllib.parse import urlparse

try:
    import dns.resolver
except Exception:
    dns = None

EMAIL_RE = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
GENERIC = {
    "contact", "info", "commercial", "sales", "bonjour", "hello", "accueil",
    "direction", "secretariat", "serviceclient", "support", "office", "admin",
    "administration", "agence", "cabinet", "communication", "marketing", "rh",
    "recrutement", "reservation", "reservations", "booking", "service", "contacteznous"
}
DISPOSABLE_DOMAINS = {
    "mailinator.com", "guerrillamail.com", "10minutemail.com", "tempmail.com",
    "yopmail.com", "trashmail.com"
}
FREE_MAIL_DOMAINS = {
    "gmail.com", "googlemail.com", "outlook.com", "hotmail.com", "live.com",
    "yahoo.com", "yahoo.fr", "orange.fr", "wanadoo.fr", "free.fr", "laposte.net",
    "icloud.com", "proton.me", "protonmail.com"
}


def normalize_email(x):
    value = (x or "").strip().lower().replace("mailto:", "").split("?", 1)[0]
    return value.strip(" <>\"'()[]{}.,;:")


def email_domain(email):
    e = normalize_email(email)
    return e.split("@", 1)[1] if EMAIL_RE.fullmatch(e) else ""


def website_domain(url):
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    host = (urlparse(url).hostname or "").lower().strip(".")
    return host[4:] if host.startswith("www.") else host


def same_business_domain(email, website=None):
    ed = email_domain(email)
    wd = website_domain(website)
    if not ed or not wd:
        return False
    return ed == wd or ed.endswith("." + wd) or wd.endswith("." + ed)


def is_generic_business_email(email):
    e = normalize_email(email)
    if not EMAIL_RE.fullmatch(e):
        return False
    local = e.split("@", 1)[0]
    compact = re.sub(r"[._+-]", "", local)
    return local in GENERIC or compact in GENERIC or local.startswith(
        ("contact", "info", "commercial", "sales", "accueil", "direction", "office", "admin")
    )


def is_public_business_email(email, website=None):
    """Accept a valid public professional address instead of only generic mailboxes."""
    e = normalize_email(email)
    if not EMAIL_RE.fullmatch(e):
        return False
    domain = email_domain(e)
    if not domain or domain in DISPOSABLE_DOMAINS:
        return False
    local = e.split("@", 1)[0]
    if local in {"noreply", "no-reply", "donotreply", "do-not-reply"}:
        return False
    if website and same_business_domain(e, website):
        return True
    if is_generic_business_email(e):
        return True
    # A named mailbox on a non-free domain is still a legitimate professional contact.
    return domain not in FREE_MAIL_DOMAINS


def email_quality_score(email, website=None):
    e = normalize_email(email)
    if not is_public_business_email(e, website):
        return -100
    score = 0
    if same_business_domain(e, website):
        score += 60
    if is_generic_business_email(e):
        score += 30
    else:
        score += 20
    if email_domain(e) not in FREE_MAIL_DOMAINS:
        score += 10
    if any(k in e.split("@", 1)[0] for k in ("contact", "commercial", "direction", "office", "info", "sales")):
        score += 10
    return score


def email_status(email):
    e = normalize_email(email)
    if not EMAIL_RE.fullmatch(e):
        return "invalide"
    if dns is None:
        return "syntaxe valide"
    try:
        dns.resolver.resolve(e.split("@", 1)[1], "MX", lifetime=3)
        return "domaine valide"
    except Exception:
        return "inconnu"
