import os, httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from .email import EMAIL_RE, normalize_email, is_generic_business_email

def extract_public_contacts(url):
    if not url: return {"email":None,"contact_form_url":None,"phone":None}
    if not url.startswith(("http://","https://")): url = "https://" + url
    headers = {"User-Agent": os.getenv("USER_AGENT", "FEWURA-PROSPECT/1.0")}
    emails=[]; forms=[]; phone=None
    try:
        with httpx.Client(timeout=12, headers=headers, follow_redirects=True) as c:
            r=c.get(url); r.raise_for_status(); pages=[(str(r.url),r.text)]
            soup=BeautifulSoup(r.text,"lxml")
            for a in soup.select("a[href]"):
                href=a.get("href",""); txt=(href+" "+a.get_text(" ",strip=True)).lower()
                if any(k in txt for k in ["contact","nous-contacter","mentions-legales"]):
                    u=urljoin(str(r.url),href)
                    if urlparse(u).netloc==urlparse(str(r.url)).netloc:
                        try: rr=c.get(u); rr.raise_for_status(); pages.append((str(rr.url),rr.text))
                        except Exception: pass
                    if len(pages)>=3: break
            for page_url, html in pages:
                s=BeautifulSoup(html,"lxml")
                emails += [normalize_email(x.get("href")) for x in s.select('a[href^="mailto:"]')]
                emails += [normalize_email(x) for x in EMAIL_RE.findall(s.get_text(" "))]
                if s.find("form") and "contact" in page_url.lower(): forms.append(page_url)
                tel=s.select_one('a[href^="tel:"]')
                if tel and not phone: phone=tel.get("href","").replace("tel:","").strip()
    except Exception: pass
    generic=next((e for e in dict.fromkeys(emails) if is_generic_business_email(e)), None)
    return {"email":generic,"contact_form_url":forms[0] if forms else None,"phone":phone}
