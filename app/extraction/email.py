import re
try:
    import dns.resolver
except Exception:
    dns = None
EMAIL_RE = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
GENERIC = {"contact","info","commercial","sales","bonjour","hello","accueil","direction","secretariat","serviceclient","support"}

def normalize_email(x): return (x or "").strip().lower().replace("mailto:", "").split("?",1)[0]
def is_generic_business_email(email):
    e = normalize_email(email)
    return bool(EMAIL_RE.fullmatch(e)) and (e.split("@",1)[0] in GENERIC or e.split("@",1)[0].startswith(("contact","info","commercial","sales","accueil","direction")))
def email_status(email):
    e = normalize_email(email)
    if not EMAIL_RE.fullmatch(e): return "invalide"
    if dns is None: return "syntaxe valide"
    try: dns.resolver.resolve(e.split("@",1)[1], "MX", lifetime=3); return "domaine valide"
    except Exception: return "inconnu"
