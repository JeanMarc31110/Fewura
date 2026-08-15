import os,smtplib
from email.message import EmailMessage
def send_email(to,subject,body,live=False):
    if not live: return {"status":"simule","id":"DRY-RUN"}
    if os.getenv("ALLOW_LIVE_SEND","false").lower()!="true": raise RuntimeError("Envoi réel désactivé")
    host=os.getenv("SMTP_HOST"); user=os.getenv("SMTP_USERNAME"); pwd=os.getenv("SMTP_PASSWORD"); sender=os.getenv("SMTP_FROM") or user
    if not all([host,user,pwd,sender]): raise RuntimeError("Configuration SMTP incomplète")
    msg=EmailMessage(); msg["From"]=sender; msg["To"]=to; msg["Subject"]=subject; msg.set_content(body)
    with smtplib.SMTP(host,int(os.getenv("SMTP_PORT","587")),timeout=30) as s:
        if os.getenv("SMTP_USE_TLS","true").lower()=="true": s.starttls()
        s.login(user,pwd); s.send_message(msg)
    return {"status":"envoye","id":msg.get("Message-ID")}
