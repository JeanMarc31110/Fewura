from pathlib import Path
import os, json, httpx
from .geolocation import geocode
BASE = Path(__file__).resolve().parents[2]
CATEGORIES = json.loads((BASE / "config" / "categories.json").read_text(encoding="utf-8"))

def search_businesses(zone, category="all", radius_km=20, max_results=50):
    geo = geocode(zone); radius = max(1000, min(int(radius_km)*1000, 50000)); limit = max(1, min(int(max_results), 100))
    cfg = CATEGORIES.get(category, {}) if category != "all" else {}
    if cfg:
        clauses = "".join(f'nwr(around:{radius},{geo["lat"]},{geo["lon"]})["{k}"="{v}"]["name"];' for k, vals in cfg.items() for v in vals)
    else:
        clauses = "".join(f'nwr(around:{radius},{geo["lat"]},{geo["lon"]})["name"]["{k}"];' for k in ["shop","office","amenity","craft","tourism"])
    query = f'[out:json][timeout:30];({clauses});out center tags {limit};'
    headers = {"User-Agent": os.getenv("USER_AGENT", "FEWURA-PROSPECT/1.0")}
    with httpx.Client(timeout=40, headers=headers) as c:
        r = c.post("https://overpass-api.de/api/interpreter", content=query.encode()); r.raise_for_status(); data = r.json()
    out = []
    for e in data.get("elements", [])[:limit]:
        t = e.get("tags", {}); center = e.get("center", {}); name = t.get("name")
        if not name: continue
        out.append({
          "company_name": name,
          "category": t.get("office") or t.get("shop") or t.get("amenity") or t.get("craft") or t.get("tourism") or category,
          "address": " ".join(x for x in [t.get("addr:housenumber", ""), t.get("addr:street", "")] if x),
          "postal_code": t.get("addr:postcode"), "city": t.get("addr:city") or zone, "region": None,
          "country": t.get("addr:country", "FR"), "lat": e.get("lat", center.get("lat")), "lon": e.get("lon", center.get("lon")),
          "phone": t.get("contact:phone") or t.get("phone"), "website": t.get("contact:website") or t.get("website"),
          "email": t.get("contact:email") or t.get("email"),
          "source_url": f'https://www.openstreetmap.org/{e.get("type")}/{e.get("id")}', "source_type": "OpenStreetMap"
        })
    return out
