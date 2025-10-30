import os
import sys
import time
import json
import subprocess
from pathlib import Path
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Form
from fastapi.responses import PlainTextResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# ------------------------
# Абсолютные импорты через пакет src
# ------------------------
from src.utils.utils import load_json, save_json, ensure_dir
from src import config
from src.logger import logger

# ------------------------
# Директории и файлы
# ------------------------
PROJECT_DIR = Path(__file__).parent.resolve()  # src/webpanel
ROOT_DIR = PROJECT_DIR.parent  # src/

LOGS_DIR = Path(config.WEB_LOG).parent
ensure_dir(LOGS_DIR)

CHANNELS_FILE = Path(config.CHANNELS_FILE)
STATS_FILE = Path(config.STATS_FILE)
RECORDS_FILE = Path(config.RECORDS_FILE)
ensure_dir(Path(RECORDS_FILE).parent / "logs")

STATIC_DIR = PROJECT_DIR / "static"
TEMPLATES_DIR = PROJECT_DIR / "templates"
ensure_dir(STATIC_DIR)

# ------------------------
# Bot management
# ------------------------
class Bot:
    def __init__(self, name: str, module: str):
        self.name = name
        self.module = module  # модуль для запуска через -m
        self.proc: subprocess.Popen | None = None
        self.log_file: Path | None = None
        self.active = False

    def is_running(self):
        return self.proc is not None and self.proc.poll() is None

    def start(self):
        if self.is_running():
            logger.info(f"✅ {self.name} уже запущен")
            return True

        self.log_file = LOGS_DIR / f"{self.name.lower()}_subprocess.log"
        log_handle = open(self.log_file, "a", encoding="utf-8")
        log_handle.write(f"\n=== Bot started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
        log_handle.flush()

        env = dict(**os.environ)
        env["PYTHONPATH"] = str(ROOT_DIR.parent)
        env["PYTHONUNBUFFERED"] = "1"

        try:
            self.proc = subprocess.Popen(
                [sys.executable, "-m", self.module],
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                cwd=ROOT_DIR.parent,
                env=env,
            )
            time.sleep(1)
            if self.proc.poll() is not None:
                logger.error(f"❌ {self.name} crashed immediately. Check logs: {self.log_file}")
                return False
            self.active = True
            logger.info(f"✅ {self.name} started successfully (PID {self.proc.pid})")
            return True
        except Exception as e:
            logger.exception(f"❌ Failed to start {self.name}: {e}")
            return False

    def stop(self):
        if not self.is_running():
            logger.info(f"ℹ️ {self.name} не запущен")
            return False
        try:
            self.proc.terminate()
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait()
        finally:
            self.proc = None
            self.active = False
        logger.info(f"✅ {self.name} stopped")
        return True

# ------------------------
# Initialize bots
# ------------------------
bot_status = {
    "Forwarder": Bot("Forwarder", "src.bot.forwarder"),
    "Records": Bot("Records", "src.bot.sil_bot"),
}

# ------------------------
# Lifespan для корректного завершения
# ------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 WebPanel starting...")
    yield
    logger.info("🛑 Shutting down WebPanel, stopping all bots...")
    for bot in bot_status.values():
        bot.stop()

# ------------------------
# FastAPI app
# ------------------------
app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)
templates.env.globals.update(enumerate=enumerate, len=len, range=range, zip=zip, str=str)

# ------------------------
# Routes
# ------------------------
@app.get("/admin")
def admin(request: Request):
    channels = load_json(CHANNELS_FILE, [])
    stats = load_json(STATS_FILE, {})
    records = load_json(RECORDS_FILE, [])
    log_files = sorted([f.name for f in LOGS_DIR.glob("*.log")], reverse=True)
    bots = [{"name": b.name, "active": b.is_running()} for b in bot_status.values()]

    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "channels": channels, "stats": stats, "records": records, "logs": log_files, "bots": bots}
    )

# --- Channels API ---
@app.post("/api/channels/add")
def add_channel(name: str = Form(...)):
    channels = load_json(CHANNELS_FILE, [])
    if name and name not in channels:
        channels.append(name)
        save_json(CHANNELS_FILE, channels)
    return JSONResponse({"status": "ok"})

@app.post("/api/channels/delete")
def delete_channel(name: str = Form(...)):
    channels = load_json(CHANNELS_FILE, [])
    if name in channels:
        channels.remove(name)
        save_json(CHANNELS_FILE, channels)
    return JSONResponse({"status": "ok"})

@app.post("/api/channels/edit")
def edit_channel(old_name: str = Form(...), new_name: str = Form(...)):
    channels = load_json(CHANNELS_FILE, [])
    if old_name in channels and new_name:
        idx = channels.index(old_name)
        channels[idx] = new_name
        save_json(CHANNELS_FILE, channels)
    return JSONResponse({"status": "ok"})

# --- Logs API ---
@app.get("/api/logs")
def get_log(file: str):
    path = LOGS_DIR / file
    if not path.exists():
        return PlainTextResponse("File not found", status_code=404)
    return PlainTextResponse(path.read_text(encoding="utf-8"))

# --- Bots API ---
@app.get("/api/bots")
def get_bots():
    return [{"name": b.name, "active": b.is_running()} for b in bot_status.values()]

@app.post("/api/bots/{action}")
def control_bot(action: str, name: str = Form(...)):
    bot = bot_status.get(name)
    if not bot:
        return JSONResponse({"status": "error", "message": f"Bot '{name}' not found"}, status_code=404)

    if action in ("start", "restart"):
        if action == "restart":
            bot.stop()
        success = bot.start()
        if not success:
            return JSONResponse({"status": "error", "message": f"Start {name} failed"}, status_code=500)
    elif action == "stop":
        bot.stop()
    else:
        return JSONResponse({"status": "error", "message": f"Unknown action '{action}'"}, status_code=400)
    return JSONResponse({"status": "ok", "message": f"{action} {name} successful"})

# --- Records API ---
@app.post("/api/records/add")
def add_record(user: str = Form(...), movement: str = Form(...), weight: float = Form(...), date: str = Form(...)):
    try:
        date = datetime.strptime(date, "%Y-%m-%d").strftime("%d.%m.%Y")
    except ValueError:
        pass
    records = load_json(RECORDS_FILE, [])
    records.append({"user": user, "movement": movement, "weight": weight, "date": date})
    save_json(RECORDS_FILE, records)
    return JSONResponse({"status": "ok"})

@app.post("/api/records/delete")
def delete_record(index: int = Form(...)):
    records = load_json(RECORDS_FILE, [])
    if 0 <= index < len(records):
        records.pop(index)
        save_json(RECORDS_FILE, records)
    return JSONResponse({"status": "ok"})

@app.post("/api/records/edit")
def edit_record(index: int = Form(...), user: str = Form(...), movement: str = Form(...), weight: float = Form(...), date: str = Form(...)):
    try:
        date = datetime.strptime(date, "%Y-%m-%d").strftime("%d.%m.%Y")
    except ValueError:
        pass
    records = load_json(RECORDS_FILE, [])
    if 0 <= index < len(records):
        records[index] = {"user": user, "movement": movement, "weight": weight, "date": date}
        save_json(RECORDS_FILE, records)
    return JSONResponse({"status": "ok"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.webpanel.webpanel:app",
        host=config.WEB_HOST,
        port=config.WEB_PORT,
        reload=True
    )