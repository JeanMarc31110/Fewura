import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path


PORT = 3000
APP_FOLDER = "FÉWURA – Agent commercial"


def app_directory():
    local_appdata = os.environ.get("LOCALAPPDATA", "").strip()
    if local_appdata:
        installed = Path(local_appdata) / APP_FOLDER
        if installed.exists():
            return installed
    return Path(sys.executable).resolve().parent / APP_FOLDER


def node_executable(project):
    bundled = project / "runtime" / "node.exe"
    if bundled.exists():
        return str(bundled)
    found = shutil.which("node.exe") or shutil.which("node")
    if found:
        return found
    program_files = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
    candidate = program_files / "nodejs" / "node.exe"
    if candidate.exists():
        return str(candidate)
    raise FileNotFoundError("Node.js est introuvable. Installez Node.js puis relancez FÉWURA.")


def server_is_running():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.25)
        return sock.connect_ex(("127.0.0.1", PORT)) == 0


def start_server(project):
    if server_is_running():
        return
    subprocess.Popen(
        [node_executable(project), "server.js"],
        cwd=str(project),
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        close_fds=True,
    )
    for _ in range(20):
        if server_is_running():
            return
        time.sleep(0.15)


def main():
    project = app_directory()
    if not (project / "server.js").exists() or not (project / "desktop_app.py").exists():
        raise FileNotFoundError(f"Dossier de l’agent introuvable : {project}")
    start_server(project)
    sys.path.insert(0, str(project))
    from desktop_app import FewuraDesktop

    FewuraDesktop().mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("FÉWURA – Agent commercial", str(error))
        root.destroy()
