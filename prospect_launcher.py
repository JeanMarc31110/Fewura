import os,sys,time,socket,threading,webbrowser
from pathlib import Path
BASE=Path(sys.executable).resolve().parent if getattr(sys,"frozen",False) else Path(__file__).resolve().parent
os.chdir(BASE); sys.path.insert(0,str(BASE))
def open_when_ready():
    for _ in range(80):
        try:
            with socket.create_connection(("127.0.0.1",8010),timeout=.4): webbrowser.open("http://127.0.0.1:8010"); return
        except OSError: time.sleep(.25)
def main():
    from app.db import init_db; init_db(); threading.Thread(target=open_when_ready,daemon=True).start()
    import uvicorn; uvicorn.run("app.main:app",host="127.0.0.1",port=8010,log_level="warning",reload=False,access_log=False)
if __name__=="__main__": main()
