from app.db import connect, rows
from app.search.deduplication import fingerprint
from app.scoring.lead_score import compute
from app.extraction.website import extract_public_contacts
from app.extraction.discovery import discover_official_website
from app.extraction.email import email_status, is_public_business_email, normalize_email


def upsert_prospect(p, enrich=False):
    if enrich and not p.get("website"):
        p["website"] = discover_official_website(p.get("company_name"), p.get("city"))

    if enrich and p.get("website") and not p.get("email"):
        c = extract_public_contacts(p["website"])
        p["email"] = c.get("email")
        p["contact_form_url"] = c.get("contact_form_url")
        p["phone"] = p.get("phone") or c.get("phone")

    if p.get("email"):
        p["email"] = normalize_email(p["email"])
        if not is_public_business_email(p["email"], p.get("website")):
            p["email"] = None

    p["email_status"] = email_status(p.get("email")) if p.get("email") else "inconnu"
    p["lead_score"] = compute(p)
    p["confidence"] = round(p["lead_score"] / 100, 2)
    p["fingerprint"] = fingerprint(p)

    cols = [
        "company_name", "category", "address", "postal_code", "city", "region", "country",
        "lat", "lon", "phone", "website", "email", "contact_form_url", "source_url",
        "source_type", "confidence", "lead_score", "email_status", "fingerprint"
    ]
    vals = [p.get(c) for c in cols]
    con = connect()
    old = con.execute("SELECT id FROM prospects WHERE fingerprint=?", (p["fingerprint"],)).fetchone()
    if old:
        assignments = ",".join(f"{c}=?" for c in cols[:-1])
        con.execute(
            f"UPDATE prospects SET {assignments},last_checked_at=CURRENT_TIMESTAMP WHERE fingerprint=?",
            vals[:-1] + [p["fingerprint"]],
        )
        rid = old["id"]
    else:
        qs = ",".join("?" for _ in cols)
        con.execute(f"INSERT INTO prospects({','.join(cols)}) VALUES({qs})", vals)
        rid = con.execute("SELECT last_insert_rowid()").fetchone()[0]
    con.commit()
    con.close()
    return rid


def list_prospects(category=None, city=None, min_score=0, only_email=False, limit=500):
    q = "SELECT * FROM prospects WHERE lead_score>=?"
    ps = [min_score]
    if category:
        q += " AND category=?"
        ps.append(category)
    if city:
        q += " AND city LIKE ?"
        ps.append("%" + city + "%")
    if only_email:
        q += " AND email IS NOT NULL AND email<>''"
    q += " ORDER BY lead_score DESC,id DESC LIMIT ?"
    ps.append(limit)
    return rows(q, ps)
