from __future__ import annotations

import ctypes
import os
import socket
import sys
import threading
import time
import traceback
import webbrowser
from pathlib import Path

HOST = os.environ.get("FEWURA_HOST", "127.0.0.1")
PORT = int(os.environ.get("FEWURA_PORT", "8010"))
NO_BROWSER = os.environ.get("FEWURA_NO_BROWSER", "0") == "1"
URL = f"http://{HOST}:{PORT}"

BASE = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
os.chdir(BASE)
sys.path.insert(0, str(BASE))


def _log_path() -> Path | None:
    try:
        from app.paths import logs_dir
        return logs_dir() / "startup-error.log"
    except Exception:
        return None


def _write_crash_log(exc: BaseException) -> Path | None:
    path = _log_path()
    if path is None:
        return None
    try:
        path.write_text(
            "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
            encoding="utf-8",
        )
        return path
    except Exception:
        return None


def _message_box(title: str, message: str) -> None:
    try:
        ctypes.windll.user32.MessageBoxW(None, message, title, 0x10)
    except Exception:
        pass


def _port_open() -> bool:
    try:
        with socket.create_connection((HOST, PORT), timeout=0.4):
            return True
    except OSError:
        return False


def _open_browser() -> None:
    if NO_BROWSER:
        return
    try:
        webbrowser.open(URL)
    except Exception:
        pass


def _open_when_ready() -> None:
    if NO_BROWSER:
        return
    for _ in range(120):
        if _port_open():
            _open_browser()
            return
        time.sleep(0.25)


def main() -> int:
    try:
        # Si Fewura tourne déjà, un double-clic sur le raccourci doit simplement
        # rouvrir l'interface au lieu d'essayer de lancer un second serveur.
        if _port_open():
            _open_browser()
            return 0

        from app.db import init_db
        init_db()
        from app.main import app

        threading.Thread(target=_open_when_ready, daemon=True).start()

        import uvicorn
        config = uvicorn.Config(
            app=app,
            host=HOST,
            port=PORT,
            log_config=None,
            log_level="warning",
            access_log=False,
            reload=False,
        )
        server = uvicorn.Server(config)
        server.run()
        return 0
    except BaseException as exc:
        path = _write_crash_log(exc)
        details = "Fewura n'a pas pu démarrer."
        if path:
            details += f"\n\nJournal d'erreur :\n{path}"
        _message_box("FEWURA PROSPECT - Erreur de démarrage", details)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
