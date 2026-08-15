from pathlib import Path
import csv
from openpyxl import Workbook
from app.services import list_prospects
BASE=Path(__file__).resolve().parents[1]
COLS=["company_name","category","address","postal_code","city","region","country","phone","website","email","contact_form_url","source_url","lead_score","email_status","status"]
def export_csv():
    p=BASE/"exports"/"prospects.csv"; p.parent.mkdir(exist_ok=True); data=list_prospects(limit=50000)
    with p.open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=COLS); w.writeheader(); [w.writerow({k:r.get(k) for k in COLS}) for r in data]
    return p
def export_xlsx():
    p=BASE/"exports"/"prospects.xlsx"; p.parent.mkdir(exist_ok=True); wb=Workbook(); ws=wb.active; ws.append(COLS)
    for r in list_prospects(limit=50000): ws.append([r.get(k) for k in COLS])
    wb.save(p); return p
