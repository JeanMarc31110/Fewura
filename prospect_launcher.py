from __future__ import annotations

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

BASE = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
os.chdir(BASE)
sys.path.insert(0, str(BASE))


def _write_crash_log(exc: BaseException) -> None:
    try:
        from app.paths import logs_dir

        path = logs_dir() / "startup-error.log"
        path.write_text(
            "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
            encoding="utf-8",
        )
    except Exception:
        pass


def _port_open() -> bool:
    try:
        with socket.create_connection((HOST, PORT), timeout=0.4):
            return True
    except OSError:
        return False


def _open_when_ready() -> None:
    if NO_BROWSER:
        return
    for _ in range(120):
        if _port_open():
            try:
                webbrowser.open(f"http://{HOST}:{PORT}")
            except Exception:
                pass
            return
        time.sleep(0.25)


def main() -> int:
    try:
        from app.db import init_db

        init_db()
        from app.main import app

        threading.Thread(target=_open_when_ready, daemon=True).start()

        import uvicorn

        # PyInstaller est compile en mode fenetre (console=False). Dans ce mode,
        # sys.stdout/sys.stderr peuvent etre None. La configuration de logging
        # par defaut d'Uvicorn appelle isatty() et peut alors planter.
        # log_config=None supprime cette dependance a une console.
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
        _write_crash_log(exc)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
