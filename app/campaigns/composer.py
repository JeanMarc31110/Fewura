def render(text,p):
    for k,v in {"entreprise":p.get("company_name",""),"ville":p.get("city",""),"secteur":p.get("category",""),"site":p.get("website","")}.items(): text=text.replace("{"+k+"}",str(v or ""))
    return text
