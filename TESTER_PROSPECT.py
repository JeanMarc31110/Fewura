from app.db import init_db, execute, one
from app.scoring.lead_score import compute
from app.extraction.email import is_generic_business_email
from app.services import upsert_prospect
from app.campaigns.sender import run_campaign
from app.connectors.whatsapp_sender import normalize_phone
import json

init_db()
assert compute({"website":"x","email":"contact@x.fr","phone":"1","category":"x","city":"x","source_url":"x","address":"x"}) >= 90
assert is_generic_business_email("contact@example.com")
assert not is_generic_business_email("jean.dupont@example.com")
assert normalize_phone("06 12 34 56 78") == "33612345678"

p = {
    "company_name":"Test SARL","category":"test-email","address":"1 rue Test","postal_code":"31000",
    "city":"Toulouse","country":"FR","phone":"0102030405","website":"https://example.com",
    "email":"contact@example.com","source_url":"https://example.com","source_type":"demo"
}
upsert_prospect(p, enrich=False)
cid = execute(
    "INSERT INTO campaigns(name,subject,body,filter_json) VALUES(?,?,?,?)",
    ("Demo email","Bonjour {entreprise}","Message pour {entreprise}",json.dumps({"category":"test-email","city":"Toulouse","min_score":0}))
)
res = run_campaign(cid, live=False, confirm=False, limit=1)
assert res["sent_or_simulated"] == 1
assert res["results"][0]["status"] == "simule"
assert res["results"][0]["channel"] == "email"

p2 = {
    "company_name":"Test WhatsApp SARL","category":"test-whatsapp","address":"2 rue Test","postal_code":"31000",
    "city":"Toulouse","country":"FR","phone":"06 12 34 56 78","website":"https://example.org",
    "email":None,"source_url":"https://example.org","source_type":"demo"
}
upsert_prospect(p2, enrich=False)
cid2 = execute(
    "INSERT INTO campaigns(name,subject,body,filter_json) VALUES(?,?,?,?)",
    ("Demo WhatsApp","Bonjour {entreprise}","Message WhatsApp pour {entreprise}",json.dumps({"category":"test-whatsapp","city":"Toulouse","min_score":0}))
)
res2 = run_campaign(cid2, live=False, confirm=False, limit=1)
assert res2["sent_or_simulated"] == 1
assert res2["results"][0]["status"] == "simule"
assert res2["results"][0]["channel"] == "whatsapp"
assert res2["results"][0]["recipient"] == "33612345678"

print("FEWURA PROSPECT : TESTS CORE + WHATSAPP OK")
