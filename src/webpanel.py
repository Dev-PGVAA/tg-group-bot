import os
import json
import logging
import sys
import subprocess
import time
from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse, PlainTextResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from utils import load_json, save_json, ensure_dir
import config

# Logging
ensure_dir(os.path.dirname(config.WEB_LOG))
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(config.WEB_LOG, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("webpanel")

app = FastAPI()

# Static files
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
ensure_dir(STATIC_DIR)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Templates
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

templates.env.globals.update(
    enumerate=enumerate,
    len=len,
    range=range,
    zip=zip,
    str=str,
)

# Data files
CHANNELS_FILE = config.CHANNELS_FILE
STATS_FILE = config.STATS_FILE
RECORDS_FILE = config.RECORDS_FILE
LOGS_DIR = os.path.join(os.path.dirname(RECORDS_FILE), "logs")
ensure_dir(LOGS_DIR)

# Bot status storage (subprocess handles)
bot_status = {
    "Forwarder": {"proc": None, "active": False, "script": "forwarder_main.py", "log_file": None},
    "DiedOnSteroids": {"proc": None, "active": False, "script": "sil_bot.py", "log_file": None},
}

# --- Routes ---
@app.get("/admin")
def admin(request: Request):
    channels = load_json(CHANNELS_FILE, [])
    stats = load_json(STATS_FILE, {})
    records = load_json(RECORDS_FILE, [])
    log_files = [f for f in sorted(os.listdir(LOGS_DIR), reverse=True) if f.endswith(".log")]

    bots = [{"name": name, "active": info["active"]} for name, info in bot_status.items()]

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "channels": channels,
            "stats": json.dumps(stats),
            "records": records,
            "logs": log_files,
            "bots": bots,
        }
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
    path = os.path.join(LOGS_DIR, file)
    if not os.path.isfile(path):
        return PlainTextResponse("File not found", status_code=404)
    with open(path, encoding="utf-8") as f:
        return PlainTextResponse(f.read())

# --- Bots API ---
@app.get("/api/bots")
def get_bots():
    # Check if processes are actually running
    for name, info in bot_status.items():
        if info["proc"] is not None:
            poll_result = info["proc"].poll()
            if poll_result is not None:  # Process has terminated
                log.warning(f"Bot {name} terminated with code: {poll_result}")
                
                # Read last lines of log to see error
                if info.get("log_file"):
                    try:
                        with open(info["log_file"], "r", encoding="utf-8") as f:
                            lines = f.readlines()
                            last_lines = ''.join(lines[-10:]) if lines else "No output"
                            log.error(f"Bot {name} last output:\n{last_lines}")
                    except:
                        pass
                
                info["proc"] = None
                info["active"] = False
    
    return [{"name": name, "active": info["active"]} for name, info in bot_status.items()]

@app.post("/api/bots/{action}")
async def control_bot(action: str, name: str = Form(...)):
    log.info(f"=== BOT CONTROL REQUEST ===")
    log.info(f"Action: {action}")
    log.info(f"Name: {name}")
    log.info(f"Current working directory: {os.getcwd()}")
    log.info(f"Script directory: {os.path.dirname(__file__)}")
    log.info(f"Python executable: {sys.executable}")
    
    if name not in bot_status:
        log.error(f"Bot not found: {name}")
        return JSONResponse(
            {"status": "error", "message": f"Bot '{name}' not found"}, 
            status_code=404
        )

    bot = bot_status[name]
    
    try:
        # Stop running process
        if action in ("stop", "restart"):
            if bot["proc"] is not None:
                log.info(f"Stopping bot {name}, PID: {bot['proc'].pid}")
                try:
                    bot["proc"].terminate()
                    try:
                        bot["proc"].wait(timeout=5)
                        log.info(f"Bot {name} stopped gracefully")
                    except subprocess.TimeoutExpired:
                        log.warning(f"Bot {name} didn't stop gracefully, killing...")
                        bot["proc"].kill()
                        bot["proc"].wait()
                        log.info(f"Bot {name} killed")
                except Exception as e:
                    log.error(f"Error stopping bot {name}: {e}")
                finally:
                    # Close log file
                    if bot.get("log_file_handle"):
                        bot["log_file_handle"].close()
                        bot["log_file_handle"] = None
                    
                    bot["proc"] = None
                    bot["active"] = False
            else:
                log.info(f"Bot {name} was not running")

        # Start process
        if action in ("start", "restart"):
            if bot["proc"] is not None and bot["proc"].poll() is None:
                log.warning(f"Bot {name} is already running")
                return JSONResponse(
                    {"status": "error", "message": f"Bot '{name}' is already running"}, 
                    status_code=400
                )
            
            # Determine script path
            script_dir = os.path.dirname(os.path.abspath(__file__))
            script_path = os.path.join(script_dir, bot["script"])
            
            log.info(f"Looking for script at: {script_path}")
            log.info(f"Script exists: {os.path.exists(script_path)}")
            
            if not os.path.exists(script_path):
                # Try alternative paths
                alternative_paths = [
                    os.path.join(os.getcwd(), bot["script"]),
                    os.path.join(script_dir, "src", bot["script"]),
                    bot["script"]  # Absolute or relative to cwd
                ]
                
                for alt_path in alternative_paths:
                    log.info(f"Trying alternative path: {alt_path}")
                    if os.path.exists(alt_path):
                        script_path = alt_path
                        log.info(f"Found script at: {script_path}")
                        break
                else:
                    log.error(f"Script not found in any location")
                    return JSONResponse(
                        {"status": "error", "message": f"Script '{bot['script']}' not found. Tried: {script_path}"}, 
                        status_code=500
                    )
            
            log.info(f"Starting bot {name} with script: {script_path}")
            
            # Prepare log file
            log_file_path = os.path.join(LOGS_DIR, f"{name.lower()}_subprocess.log")
            bot["log_file"] = log_file_path
            
            log.info(f"Bot output will be logged to: {log_file_path}")
            
            try:
                log_file_handle = open(log_file_path, "a", encoding="utf-8")
                log_file_handle.write(f"\n\n=== Bot started at {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
                log_file_handle.flush()
                
                # Get environment variables
                env = os.environ.copy()
                env['PYTHONUNBUFFERED'] = '1'  # Disable Python output buffering
                
                # Start subprocess
                bot["proc"] = subprocess.Popen(
                    [sys.executable, "-u", script_path],  # -u for unbuffered
                    stdout=log_file_handle,
                    stderr=subprocess.STDOUT,
                    cwd=script_dir,
                    env=env,
                    bufsize=0  # Unbuffered
                )
                
                bot["log_file_handle"] = log_file_handle
                bot["active"] = True
                
                log.info(f"Bot {name} started with PID: {bot['proc'].pid}")
                
                # Wait a bit and check if it's still running
                time.sleep(1)
                poll_result = bot["proc"].poll()
                
                if poll_result is not None:
                    log.error(f"Bot {name} exited immediately with code: {poll_result}")
                    
                    # Read the log to see what went wrong
                    log_file_handle.flush()
                    with open(log_file_path, "r", encoding="utf-8") as f:
                        error_output = f.read()
                        log.error(f"Bot {name} error output:\n{error_output}")
                    
                    bot["active"] = False
                    bot["proc"] = None
                    
                    return JSONResponse(
                        {"status": "error", "message": f"Bot crashed immediately. Check log: {log_file_path}"}, 
                        status_code=500
                    )
                
                log.info(f"Bot {name} is running successfully")
                
            except Exception as e:
                log.exception(f"Error opening log file or starting process: {e}")
                return JSONResponse(
                    {"status": "error", "message": f"Failed to start: {str(e)}"}, 
                    status_code=500
                )
        
        return JSONResponse({
            "status": "ok", 
            "message": f"Bot {name} {action} successful"
        })
        
    except Exception as e:
        log.exception(f"Error controlling bot {name}: {e}")
        bot["active"] = False
        bot["proc"] = None
        return JSONResponse(
            {"status": "error", "message": f"Error: {str(e)}"}, 
            status_code=500
        )

# --- Records API ---
@app.post("/api/records/add")
def add_record(user: str = Form(...), movement: str = Form(...), weight: float = Form(...), date: str = Form(...)):
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
    records = load_json(RECORDS_FILE, [])
    if 0 <= index < len(records):
        records[index] = {"user": user, "movement": movement, "weight": weight, "date": date}
        save_json(RECORDS_FILE, records)
    return JSONResponse({"status": "ok"})

# Cleanup on shutdown
@app.on_event("shutdown")
def shutdown_event():
    log.info("Shutting down web panel, stopping all bots...")
    for name, info in bot_status.items():
        if info["proc"] is not None:
            try:
                log.info(f"Terminating bot {name}")
                info["proc"].terminate()
                info["proc"].wait(timeout=5)
            except:
                info["proc"].kill()
            finally:
                if info.get("log_file_handle"):
                    info["log_file_handle"].close()