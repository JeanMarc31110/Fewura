import os
import re
import httpx


def normalize_phone(phone: str, default_country_code: str = "33") -> str:
    raw = re.sub(r"\D+", "", phone or "")
    if not raw:
        return ""
    if raw.startswith("00"):
        raw = raw[2:]
    if raw.startswith("0"):
        raw = default_country_code + raw[1:]
    return raw


def send_whatsapp(phone: str, body: str, live: bool = False) -> dict:
    normalized = normalize_phone(phone, os.getenv("WHATSAPP_DEFAULT_COUNTRY_CODE", "33"))
    if not normalized:
        raise ValueError("Numéro de téléphone absent ou invalide")

    if not live:
        return {"status": "simule", "id": None, "channel": "whatsapp", "recipient": normalized}

    if os.getenv("ALLOW_LIVE_SEND", "false").lower() != "true":
        raise ValueError("Envoi réel désactivé: ALLOW_LIVE_SEND doit valoir true")

    api_url = (os.getenv("WHATSAPP_API_URL") or "").strip()
    token = (os.getenv("WHATSAPP_ACCESS_TOKEN") or "").strip()
    if not api_url or not token:
        raise ValueError("Configuration WhatsApp Business incomplète: WHATSAPP_API_URL / WHATSAPP_ACCESS_TOKEN")

    payload = {
        "messaging_product": "whatsapp",
        "to": normalized,
        "type": "text",
        "text": {"preview_url": False, "body": body},
    }
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    with httpx.Client(timeout=30) as client:
        response = client.post(api_url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

    message_id = None
    if isinstance(data, dict):
        messages = data.get("messages") or []
        if messages and isinstance(messages[0], dict):
            message_id = messages[0].get("id")

    return {"status": "envoye", "id": message_id, "channel": "whatsapp", "recipient": normalized}
