import html as html_lib
import os
import re
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

from .email import EMAIL_RE, normalize_email, is_public_business_email, email_quality_score

CONTACT_HINTS = (
    "contact", "nous-contacter", "contactez", "mentions-legales", "mentions", "legal",
    "impressum", "equipe", "team", "a-propos", "about", "cabinet", "agence", "societe",
    "entreprise", "coordonnees", "direction", "staff", "office"
)


def _deobfuscate_text(text):
    text = html_lib.unescape(text or "")
    replacements = [
        (r"\s*(?:\[|\()\s*at\s*(?:\]|\))\s*", "@"),
        (r"\s+(?:at|arobase)\s+", "@"),
        (r"\s*(?:\[|\()\s*dot\s*(?:\]|\))\s*", "."),
        (r"\s+(?:dot|point)\s+", "."),
    ]
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text, flags=re.I)
    return text


def _emails_from_soup(soup):
    candidates = []
    for node in soup.select('a[href^="mailto:"]'):
        candidates.append(normalize_email(node.get("href")))

    # Visible text, HTML attributes and lightly-obfuscated addresses.
    texts = [soup.get_text(" ", strip=True), str(soup)]
    for raw in texts:
        decoded = _deobfuscate_text(raw)
        candidates.extend(normalize_email(x) for x in EMAIL_RE.findall(decoded))

    # Common data attributes used by themes/plugins to hide emails from bots.
    for node in soup.find_all(True):
        for key, value in node.attrs.items():
            if not isinstance(value, str):
                continue
            if "mail" in key.lower() or "email" in key.lower() or "@" in value:
                decoded = _deobfuscate_text(value)
                candidates.extend(normalize_email(x) for x in EMAIL_RE.findall(decoded))

    return [e for e in dict.fromkeys(candidates) if e]


def extract_public_contacts(url, max_pages=8):
    if not url:
        return {"email": None, "contact_form_url": None, "phone": None}
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    headers = {
        "User-Agent": os.getenv(
            "USER_AGENT",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 FewuraProspect/2.0"
        ),
        "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.7",
    }

    emails = []
    forms = []
    phone = None
    visited = set()

    try:
        with httpx.Client(timeout=12, headers=headers, follow_redirects=True) as client:
            first = client.get(url)
            first.raise_for_status()
            root_url = str(first.url)
            root_host = urlparse(root_url).netloc.lower()
            queue = [(root_url, first.text)]

            while queue and len(visited) < max_pages:
                page_url, page_html = queue.pop(0)
                if page_url in visited:
                    continue
                visited.add(page_url)

                soup = BeautifulSoup(page_html, "lxml")
                emails.extend(_emails_from_soup(soup))

                if soup.find("form") and any(k in page_url.lower() for k in ("contact", "coordonne", "about", "equipe")):
                    forms.append(page_url)

                if not phone:
                    tel = soup.select_one('a[href^="tel:"]')
                    if tel:
                        phone = tel.get("href", "").replace("tel:", "").strip()

                # Rank internal links instead of stopping at only 2 contact/legal pages.
                links = []
                for a in soup.select("a[href]"):
                    href = a.get("href", "").strip()
                    if not href or href.startswith(("mailto:", "tel:", "javascript:", "#")):
                        continue
                    absolute = urljoin(page_url, href).split("#", 1)[0]
                    parsed = urlparse(absolute)
                    if parsed.netloc.lower() != root_host:
                        continue
                    text = (href + " " + a.get_text(" ", strip=True)).lower()
                    score = sum(1 for hint in CONTACT_HINTS if hint in text)
                    if score:
                        links.append((score, absolute))

                for _, absolute in sorted(links, key=lambda x: x[0], reverse=True):
                    if absolute in visited or any(absolute == u for u, _ in queue):
                        continue
                    try:
                        response = client.get(absolute)
                        ctype = response.headers.get("content-type", "")
                        if response.is_success and ("text/html" in ctype or not ctype):
                            queue.append((str(response.url), response.text))
                    except Exception:
                        continue
                    if len(visited) + len(queue) >= max_pages:
                        break

    except Exception:
        pass

    unique = [normalize_email(e) for e in dict.fromkeys(emails)]
    valid = [e for e in unique if is_public_business_email(e, url)]
    valid.sort(key=lambda e: email_quality_score(e, url), reverse=True)
    best_email = valid[0] if valid else None

    return {
        "email": best_email,
        "contact_form_url": forms[0] if forms else None,
        "phone": phone,
    }
