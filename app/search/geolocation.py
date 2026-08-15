import os, httpx

def geocode(zone: str):
    headers = {"User-Agent": os.getenv("USER_AGENT", "FEWURA-PROSPECT/1.0")}
    params = {"q": zone, "format": "jsonv2", "limit": 1, "countrycodes": "fr"}
    with httpx.Client(timeout=15, headers=headers, follow_redirects=True) as c:
        r = c.get("https://nominatim.openstreetmap.org/search", params=params)
        r.raise_for_status(); data = r.json()
    if not data: raise ValueError(f"Zone introuvable: {zone}")
    return {"lat": float(data[0]["lat"]), "lon": float(data[0]["lon"]), "display_name": data[0].get("display_name", zone)}
