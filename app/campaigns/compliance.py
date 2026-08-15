from app.db import one
def can_contact(p,campaign_id=None):
    email=(p.get("email") or "").lower()
    if not email: return False,"email absent"
    domain=email.split("@",1)[1]
    if one("SELECT id FROM do_not_contact WHERE lower(email)=? OR lower(domain)=? OR lower(company_name)=lower(?) LIMIT 1",(email,domain,p.get("company_name",""))): return False,"liste opposition"
    if campaign_id and one("SELECT id FROM communications WHERE campaign_id=? AND lower(recipient)=? AND status IN ('envoye','simule') LIMIT 1",(campaign_id,email)): return False,"déjà contacté"
    return True,"ok"
