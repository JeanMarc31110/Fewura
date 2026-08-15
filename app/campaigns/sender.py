import os,time,json
from app.db import one, execute
from app.services import list_prospects
from .composer import render
from .compliance import can_contact
from app.connectors.smtp_sender import send_email

def run_campaign(campaign_id, live=False, confirm=False, limit=10):
    camp=one("SELECT * FROM campaigns WHERE id=?",(campaign_id,))
    if not camp: raise ValueError("Campagne introuvable")
    if live and not confirm: raise ValueError("Confirmation explicite requise")
    limit=min(max(1,int(limit)),int(os.getenv("DAILY_SEND_LIMIT","20")))
    f=json.loads(camp.get("filter_json") or "{}"); prospects=list_prospects(f.get("category"),f.get("city"),int(f.get("min_score",0)),True,500)
    out=[]; n=0
    for p in prospects:
        if n>=limit: break
        ok,reason=can_contact(p,campaign_id)
        if not ok: out.append({"prospect":p["company_name"],"status":"ignore","reason":reason}); continue
        subject=render(camp["subject"],p); body=render(camp["body"],p)
        if "ne plus" not in body.lower() and "désins" not in body.lower(): body += "\n\nSi vous ne souhaitez plus recevoir de message de notre part, répondez « STOP »."
        try:
            res=send_email(p["email"],subject,body,live); execute("INSERT INTO communications(prospect_id,campaign_id,recipient,subject,status,provider_message_id) VALUES(?,?,?,?,?,?)",(p["id"],campaign_id,p["email"],subject,res["status"],res.get("id"))); out.append({"prospect":p["company_name"],"email":p["email"],"status":res["status"]}); n+=1
            if live: time.sleep(float(os.getenv("SEND_DELAY_SECONDS","10")))
        except Exception as e:
            execute("INSERT INTO communications(prospect_id,campaign_id,recipient,subject,status,error) VALUES(?,?,?,?,?,?)",(p["id"],campaign_id,p["email"],subject,"erreur",str(e))); out.append({"prospect":p["company_name"],"status":"erreur","error":str(e)})
    return {"campaign_id":campaign_id,"live":live,"processed":len(out),"sent_or_simulated":n,"results":out}
