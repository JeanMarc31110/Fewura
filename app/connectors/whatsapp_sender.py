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


def whatsapp_config() -> dict:
    graph_version = (os.getenv("WHATSAPP_GRAPH_VERSION") or "").strip()
    phone_number_id = (os.getenv("WHATSAPP_PHONE_NUMBER_ID") or "").strip()
    token = (os.getenv("WHATSAPP_ACCESS_TOKEN") or "").strip()
    template_name = (os.getenv("WHATSAPP_TEMPLATE_NAME") or "").strip()
    template_language = (os.getenv("WHATSAPP_TEMPLATE_LANGUAGE") or "fr").strip()

    missing = []
    if not graph_version:
        missing.append("WHATSAPP_GRAPH_VERSION")
    if not phone_number_id:
        missing.append("WHATSAPP_PHONE_NUMBER_ID")
    if not token:
        missing.append("WHATSAPP_ACCESS_TOKEN")

    api_url = ""
    if graph_version and phone_number_id:
        api_url = f"https://graph.facebook.com/{graph_version}/{phone_number_id}/messages"

    return {
        "configured": not missing,
        "missing": missing,
        "graph_version": graph_version,
        "phone_number_id": phone_number_id,
        "token": token,
        "api_url": api_url,
        "template_name": template_name,
        "template_language": template_language,
    }


def _text_payload(recipient: str, body: str) -> dict:
    return {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient,
        "type": "text",
        "text": {"preview_url": False, "body": body},
    }


def _template_payload(recipient: str, template_name: str, language: str, body: str) -> dict:
    # Le template Meta doit être créé et approuvé dans WhatsApp Manager.
    # Le premier paramètre BODY reçoit le texte personnalisé de Fewura.
    return {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": language},
            "components": [
                {
                    "type": "body",
                    "parameters": [{"type": "text", "text": body}],
                }
            ],
        },
    }


def send_whatsapp(phone: str, body: str, live: bool = False, use_template: bool | None = None) -> dict:
    normalized = normalize_phone(phone, os.getenv("WHATSAPP_DEFAULT_COUNTRY_CODE", "33"))
    if not normalized:
        raise ValueError("Numéro de téléphone absent ou invalide")

    cfg = whatsapp_config()

    if not live:
        mode = "template" if (use_template or cfg["template_name"]) else "text"
        return {
            "status": "simule",
            "id": None,
            "channel": "whatsapp",
            "recipient": normalized,
            "mode": mode,
        }

    if os.getenv("ALLOW_LIVE_SEND", "false").lower() != "true":
        raise ValueError("Envoi réel désactivé: ALLOW_LIVE_SEND doit valoir true")

    if not cfg["configured"]:
        raise ValueError("Configuration Meta WhatsApp incomplète: " + ", ".join(cfg["missing"]))

    if use_template is None:
        use_template = os.getenv("WHATSAPP_USE_TEMPLATE", "true").lower() == "true"

    if use_template:
        if not cfg["template_name"]:
            raise ValueError("WHATSAPP_TEMPLATE_NAME requis pour un envoi WhatsApp initié par l'entreprise")
        payload = _template_payload(normalized, cfg["template_name"], cfg["template_language"], body)
    else:
        payload = _text_payload(normalized, body)

    headers = {
        "Authorization": f"Bearer {cfg['token']}",
        "Content-Type": "application/json",
    }

    with httpx.Client(timeout=30) as client:
        response = client.post(cfg["api_url"], headers=headers, json=payload)
        if response.is_error:
            detail = response.text[:1000]
            raise RuntimeError(f"WhatsApp Cloud API HTTP {response.status_code}: {detail}")
        data = response.json()

    message_id = None
    if isinstance(data, dict):
        messages = data.get("messages") or []
        if messages and isinstance(messages[0], dict):
            message_id = messages[0].get("id")

    return {
        "status": "envoye",
        "id": message_id,
        "channel": "whatsapp",
        "recipient": normalized,
        "mode": "template" if use_template else "text",
    }
