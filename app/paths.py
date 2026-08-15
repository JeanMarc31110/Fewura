from __future__ import annotations

import os
from pathlib import Path

APP_VENDOR = "FEWURA"
APP_NAME = "PROSPECT"


def install_dir() -> Path:
    """Directory containing the installed application code/resources."""
    return Path(__file__).resolve().parents[1]


def user_data_dir() -> Path:
    """Writable per-user application directory.

    Windows: %LOCALAPPDATA%\FEWURA\PROSPECT
    Other OSes: ~/.local/share/FEWURA/PROSPECT (or XDG_DATA_HOME)
    """
    if os.name == "nt":
        root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
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
