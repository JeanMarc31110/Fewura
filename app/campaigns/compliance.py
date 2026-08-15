from app.db import one
from app.connectors.whatsapp_sender import normalize_phone


def preferred_channel(p):
    email = (p.get("email") or "").strip().lower()
    if email:
        return "email", email
    phone = normalize_phone(p.get("phone") or "")
    if phone:
        return "whatsapp", phone
    return None, None


def can_contact(p, campaign_id=None):
    channel, recipient = preferred_channel(p)
    if not channel:
        return False, "aucun email ni téléphone exploitable", None, None

    company = p.get("company_name", "")
    if channel == "email":
        domain = recipient.split("@", 1)[1] if "@" in recipient else ""
        blocked = one(
            "SELECT id FROM do_not_contact WHERE lower(email)=? OR lower(domain)=? OR lower(company_name)=lower(?) LIMIT 1",
            (recipient, domain, company),
        )
    else:
        blocked = one(
            "SELECT id FROM do_not_contact WHERE phone=? OR lower(company_name)=lower(?) LIMIT 1",
            (recipient, company),
        )

    if blocked:
        return False, "liste opposition", channel, recipient

    if campaign_id and one(
        "SELECT id FROM communications WHERE campaign_id=? AND channel=? AND lower(recipient)=lower(?) AND status IN ('envoye','simule') LIMIT 1",
        (campaign_id, channel, recipient),
    ):
        return False, "déjà contacté", channel, recipient

    return True, "ok", channel, recipient
