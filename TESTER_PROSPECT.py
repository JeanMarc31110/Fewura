from app.db import init_db, execute, one
from app.scoring.lead_score import compute
from app.extraction.email import is_generic_business_email
from app.services import upsert_prospect
from app.campaigns.sender import run_campaign
import json
init_db()
assert compute({"website":"x","email":"contact@x.fr","phone":"1","category":"x","city":"x","source_url":"x","address":"x"}) >= 90
assert is_generic_business_email("contact@example.com")
assert not is_generic_business_email("jean.dupont@example.com")
p={"company_name":"Test SARL","category":"test","address":"1 rue Test","postal_code":"31000","city":"Toulouse","country":"FR","phone":"0102030405","website":"https://example.com","email":"contact@example.com","source_url":"https://example.com","source_type":"demo"}
upsert_prospect(p,enrich=False)
cid=execute("INSERT INTO campaigns(name,subject,body,filter_json) VALUES(?,?,?,?)",("Demo","Bonjour {entreprise}","Message pour {entreprise}",json.dumps({"category":"test","city":"Toulouse","min_score":0})))
res=run_campaign(cid,live=False,confirm=False,limit=1)
assert res["sent_or_simulated"]==1 and res["results"][0]["status"]=="simule"
print("FEWURA PROSPECT : TESTS CORE OK")
