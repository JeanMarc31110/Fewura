from pathlib import Path
import os, json, signal, threading, time

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from app.paths import user_data_dir, install_dir

load_dotenv(user_data_dir() / ".env", override=False)
load_dotenv(install_dir() / ".env", override=False)

from app.db import init_db, rows, one, execute, connect
from app.search.engine import search_businesses
from app.services import upsert_prospect, list_prospects
from app.campaigns.sender import run_campaign
from app.exporter import export_csv, export_xlsx

BASE = Path(__file__).resolve().parents[1]
app = FastAPI(title="FEWURA PROSPECT", version="1.0.6")
app.mount("/static", StaticFiles(directory=str(BASE / "app" / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE / "app" / "templates"))

_shutdown_lock = threading.Lock()
_shutdown_timer: threading.Timer | None = None

@app.on_event("startup")
def startup():
    init_db()

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    stats = {
        "prospects": one("SELECT count(*) n FROM prospects")["n"],
        "emails": one("SELECT count(*) n FROM prospects WHERE email IS NOT NULL AND email<>''")["n"],
        "sent": one("SELECT count(*) n FROM communications WHERE status='envoye'")["n"],
        "simulated": one("SELECT count(*) n FROM communications WHERE status='simule'")["n"],
    }
    context = {
        "prospects": list_prospects(limit=200),
        "campaigns": rows("SELECT * FROM campaigns ORDER BY id DESC LIMIT 20"),
        "stats": stats,
        "live_enabled": os.getenv("ALLOW_LIVE_SEND", "false").lower() == "true",
    }
    return templates.TemplateResponse(request, "dashboard.html", context)

@app.post("/search")
def search(zone: str = Form(...), category: str = Form("all"), radius_km: int = Form(20), max_results: int = Form(50), enrich: bool = Form(False)):
    try:
        found = search_businesses(zone, category, radius_km, max_results)
    except Exception as e:
        raise HTTPException(502, str(e))
    for p in found:
        upsert_prospect(p, enrich=enrich)
    return RedirectResponse("/", 303)

@app.post("/campaigns")
def campaign(name: str = Form(...), subject: str = Form(...), body: str = Form(...), category: str = Form(""), city: str = Form(""), min_score: int = Form(0)):
    execute("INSERT INTO campaigns(name,subject,body,filter_json) VALUES(?,?,?,?)", (name, subject, body, json.dumps({"category": category or None, "city": city or None, "min_score": min_score}, ensure_ascii=False)))
    return RedirectResponse("/", 303)

@app.post("/campaigns/{cid}/run")
def run(cid: int, live: bool = Form(False), confirm: bool = Form(False), limit: int = Form(10)):
    try:
        return JSONResponse(run_campaign(cid, live, confirm, limit))
    except Exception as e:
        raise HTTPException(400, str(e))

@app.post("/prospects/{pid}/dnc")
def dnc(pid: int, reason: str = Form("opposition")):
    p = one("SELECT * FROM prospects WHERE id=?", (pid,))
    if not p:
        raise HTTPException(404)
    domain = p["email"].split("@", 1)[1] if p.get("email") and "@" in p["email"] else None
    execute("INSERT INTO do_not_contact(email,domain,company_name,reason) VALUES(?,?,?,?)", (p.get("email"), domain, p.get("company_name"), reason))
    execute("UPDATE prospects SET status='désinscrit' WHERE id=?", (pid,))
    return RedirectResponse("/", 303)


def _delete_prospect_ids(ids: list[int]) -> int:
    clean_ids = sorted({int(x) for x in ids if int(x) > 0})
    if not clean_ids:
        return 0
    marks = ",".join("?" for _ in clean_ids)
    con = connect()
    try:
        con.execute(f"UPDATE communications SET prospect_id=NULL WHERE prospect_id IN ({marks})", clean_ids)
        cur = con.execute(f"DELETE FROM prospects WHERE id IN ({marks})", clean_ids)
        con.commit()
        return int(cur.rowcount or 0)
    finally:
        con.close()


@app.post("/prospects/{pid}/delete")
def delete_one_prospect(pid: int):
    _delete_prospect_ids([pid])
    return RedirectResponse("/", 303)


@app.post("/prospects/delete-selected")
async def delete_selected_prospects(request: Request):
    form = await request.form()
    raw_ids = form.getlist("prospect_ids")
    ids: list[int] = []
    for raw in raw_ids:
        try:
            ids.append(int(str(raw)))
        except (TypeError, ValueError):
            continue
    _delete_prospect_ids(ids)
    return RedirectResponse("/", 303)


@app.post("/prospects/delete-all")
def delete_all_prospects(confirm_delete_all: str = Form("")):
    if confirm_delete_all != "SUPPRIMER_TOUT":
        raise HTTPException(400, "Confirmation de suppression totale invalide")
    con = connect()
    try:
        con.execute("UPDATE communications SET prospect_id=NULL WHERE prospect_id IS NOT NULL")
        con.execute("DELETE FROM prospects")
        con.commit()
    finally:
        con.close()
    return RedirectResponse("/", 303)

@app.get("/export/csv")
def ecsv():
    return FileResponse(export_csv(), filename="prospects.csv")

@app.get("/export/xlsx")
def exlsx():
    return FileResponse(export_xlsx(), filename="prospects.xlsx")


def _require_local(request: Request) -> None:
    client_host = request.client.host if request.client else ""
    if client_host not in {"127.0.0.1", "::1", "localhost", "testclient"}:
        raise HTTPException(403, "Arrêt autorisé uniquement depuis le PC local")


def _terminate_process() -> None:
    try:
        os.kill(os.getpid(), signal.SIGTERM)
    except Exception:
        os._exit(0)


def _shutdown_after_response() -> None:
    time.sleep(0.35)
    _terminate_process()


@app.post("/shutdown")
def shutdown(request: Request):
    _require_local(request)
    threading.Thread(target=_shutdown_after_response, daemon=True).start()
    return {"ok": True, "message": "FEWURA va s'arrêter"}


@app.post("/shutdown/schedule")
def schedule_shutdown(request: Request):
    global _shutdown_timer
    _require_local(request)
    with _shutdown_lock:
        if _shutdown_timer:
            _shutdown_timer.cancel()
        _shutdown_timer = threading.Timer(2.5, _terminate_process)
        _shutdown_timer.daemon = True
        _shutdown_timer.start()
    return {"ok": True}


@app.post("/shutdown/cancel")
def cancel_shutdown(request: Request):
    global _shutdown_timer
    _require_local(request)
    with _shutdown_lock:
        if _shutdown_timer:
            _shutdown_timer.cancel()
            _shutdown_timer = None
    return {"ok": True}


@app.get("/health")
def health():
    return {"ok": True, "app": "FEWURA PROSPECT", "version": "1.0.6"}
