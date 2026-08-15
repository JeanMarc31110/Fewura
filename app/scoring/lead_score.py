def compute(p):
    score=0
    for field,pts in [("website",10),("email",20),("phone",10),("category",20),("city",15),("source_url",10)]:
        if p.get(field): score += pts
    if p.get("address") or p.get("postal_code"): score += 10
    if p.get("contact_form_url"): score += 5
    return min(score,100)
