import hashlib,re
def fingerprint(p):
    domain=re.sub(r'^https?://(www\.)?','',(p.get('website') or '').lower()).split('/')[0]
    raw='|'.join([(p.get('company_name') or '').lower().strip(),domain,(p.get('phone') or '').strip(),(p.get('address') or '').lower().strip(),(p.get('city') or '').lower().strip()])
    return hashlib.sha256(raw.encode()).hexdigest()
