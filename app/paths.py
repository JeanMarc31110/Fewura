from __future__ import annotations

import os
from pathlib import Path

APP_VENDOR = "FEWURA"
APP_NAME = "PROSPECT"


def install_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def user_data_dir() -> Path:
    override = os.environ.get("FEWURA_DATA_DIR")
    if override:
        path = Path(override).expanduser().resolve()
    elif os.name == "nt":
        root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        path = root / APP_VENDOR / APP_NAME
    else:
        root = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
        path = root / APP_VENDOR / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def database_path() -> Path:
    path = user_data_dir() / "data" / "prospect.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def exports_dir() -> Path:
    path = user_data_dir() / "exports"
    path.mkdir(parents=True, exist_ok=True)
    return path


def logs_dir() -> Path:
    path = user_data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path
