from pathlib import Path
import os, json, httpx
from .geolocation import geocode

BASE = Path(__file__).resolve().parents[2]
CATEGORIES = json.loads((BASE / "config" / "categories.json").read_text(encoding="utf-8"))

OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.nchc.org.tw/api/interpreter",
]


def _build_query(lat, lon, radius, category):
    cfg = CATEGORIES.get(category, {}) if category != "all" else {}
    if cfg:
        clauses = "".join(
            f'nwr(around:{radius},{lat},{lon})["{k}"="{v}"];'
            for k, vals in cfg.items()
            for v in vals
        )
    else:
        clauses = "".join(
            f'nwr(around:{radius},{lat},{lon})["{k}"];'
            for k in ["shop", "office", "amenity", "craft", "tourism"]
        )
    # Ordre Overpass robuste : niveau de detail (tags), geometrie (center), limite.
    return f'[out:json][timeout:30];({clauses});out tags center {max(100, radius // 1000)};'


def _fetch_overpass(query, headers):
    errors = []
    with httpx.Client(timeout=45, headers=headers, follow_redirects=True) as c:
        for endpoint in OVERPASS_ENDPOINTS:
            try:
                r = c.post(endpoint, data={"data": query})
                r.raise_for_status()
                data = r.json()
                if isinstance(data, dict) and "elements" in data:
                    return data
                errors.append(f"{endpoint}: réponse inattendue")
            except Exception as exc:
                errors.append(f"{endpoint}: {exc}")
    raise RuntimeError("Aucun serveur Overpass disponible. " + " | ".join(errors))


def search_businesses(zone, category="all", radius_km=20, max_results=50):
    geo = geocode(zone)
    radius = max(1000, min(int(radius_km) * 1000, 50000))
    limit = max(1, min(int(max_results), 100))
    query = _build_query(geo["lat"], geo["lon"], radius, category)
    headers = {"User-Agent": os.getenv("USER_AGENT", "FEWURA-PROSPECT/1.0")}
    data = _fetch_overpass(query, headers)

    out = []
    seen = set()
    for e in data.get("elements", []):
        if len(out) >= limit:
            break
        t = e.get("tags", {})
        center = e.get("center", {})
        name = t.get("name") or t.get("brand") or t.get("operator")
        if not name:
            continue

        key = (name.lower().strip(), t.get("addr:street"), t.get("addr:housenumber"))
        if key in seen:
            continue
        seen.add(key)

        out.append({
            "company_name": name,
            "category": t.get("office") or t.get("shop") or t.get("amenity") or t.get("craft") or t.get("tourism") or category,
            "address": " ".join(x for x in [t.get("addr:housenumber", ""), t.get("addr:street", "")] if x),
            "postal_code": t.get("addr:postcode"),
            "city": t.get("addr:city") or zone,
            "region": None,
            "country": t.get("addr:country", "FR"),
            "lat": e.get("lat", center.get("lat")),
            "lon": e.get("lon", center.get("lon")),
            "phone": t.get("contact:phone") or t.get("phone"),
            "website": t.get("contact:website") or t.get("website"),
            "email": t.get("contact:email") or t.get("email"),
            "source_url": f'https://www.openstreetmap.org/{e.get("type")}/{e.get("id")}',
            "source_type": "OpenStreetMap",
        })
    return out
