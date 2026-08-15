import csv
from openpyxl import Workbook
from app.services import list_prospects
from app.paths import exports_dir

COLS=["company_name","category","address","postal_code","city","region","country","phone","website","email","contact_form_url","source_url","lead_score","email_status","status"]


def export_csv():
    p=exports_dir()/"prospects.csv"; data=list_prospects(limit=50000)
    with p.open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=COLS); w.writeheader(); [w.writerow({k:r.get(k) for k in COLS}) for r in data]
    return p


def export_xlsx():
    p=exports_dir()/"prospects.xlsx"; wb=Workbook(); ws=wb.active; ws.append(COLS)
    for r in list_prospects(limit=50000): ws.append([r.get(k) for k in COLS])
    wb.save(p); return p
