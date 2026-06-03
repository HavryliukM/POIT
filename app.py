from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from models import SessionLocal, SensorReading, SavedSession
from sensor_manager import SensorManager
import json
import asyncio

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

sensor_manager = SensorManager()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/history")
async def get_history():
    db = SessionLocal()
    readings = db.query(SensorReading).order_by(SensorReading.timestamp.desc()).limit(50).all()
    data = [r.to_dict() for r in readings]
    db.close()
    return JSONResponse(content=data)


@app.get("/api/archive/load_db")
async def load_archive_db(id: int):
    """Load a packaged session from DB by ID."""
    db = SessionLocal()
    session_record = db.query(SavedSession).filter(SavedSession.id == id).first()
    db.close()
    if not session_record:
        return JSONResponse(status_code=404, content={"message": f"Relácia s ID {id} neexistuje."})
    if not session_record.data:
        return JSONResponse(content=[])
    return JSONResponse(content=json.loads(session_record.data))


@app.get("/api/archive/load_csv")
async def load_archive_csv(file: str):
    """Load session data from a specific CSV file."""
    import csv as csv_mod, os
    # Sanitize path to prevent directory traversal
    filename = os.path.basename(file)
    if not os.path.exists(filename):
        return JSONResponse(status_code=404, content={"message": f"Súbor {filename} neexistuje."})
    
    rows = []
    with open(filename, "r", newline="", encoding="utf-8") as f:
        reader = csv_mod.DictReader(f)
        for row in reader:
            try:
                temp_str = row.get("temp")
                hum_str = row.get("hum")
                temp = float(temp_str) if temp_str else 0.0
                hum = float(hum_str) if hum_str else 0.0
                
                light_str = row.get("light")
                light = int(float(light_str)) if light_str else 0
                
                light_val_str = row.get("light_val")
                light_val = int(float(light_val_str)) if light_val_str else 0
                
                rows.append({
                    "timestamp": row.get("timestamp", ""),
                    "temp":      temp,
                    "hum":       hum,
                    "light":     light,
                    "light_val": light_val,
                })
            except Exception:
                continue
    return JSONResponse(content=rows)

@app.get("/api/archive/list_csv")
async def list_csv_files():
    """List all archive_session_*.csv files in the directory."""
    import os, glob
    files = glob.glob("archive_session_*.csv")
    files.sort(reverse=True)
    basenames = [os.path.basename(f) for f in files]
    return JSONResponse(content=basenames)


@app.post("/api/archive/save_db")
async def save_archive_db():
    res = sensor_manager.save_to_db()
    return JSONResponse(content=res)


@app.post("/api/archive/save_csv")
async def save_archive_csv():
    res = sensor_manager.save_to_csv()
    return JSONResponse(content=res)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    # Each client gets its own asyncio Queue
    loop = asyncio.get_running_loop()
    q = asyncio.Queue()
    sensor_manager.add_client(loop, q)

    async def push_loop():
        """Continuously sends sensor data from queue to this websocket client."""
        try:
            while True:
                data = await q.get()
                await websocket.send_text(json.dumps(data))
        except (asyncio.CancelledError, WebSocketDisconnect):
            pass

    push_task = asyncio.create_task(push_loop())

    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            action = msg.get("action", "")

            if action == "open":
                result = sensor_manager.open_system()
            elif action == "close":
                result = sensor_manager.close_system()
            elif action == "start":
                result = sensor_manager.start_monitoring()
            elif action == "stop":
                result = sensor_manager.stop_monitoring()
            elif action == "set_params":
                interval = float(msg.get("interval", 1.0))
                result = sensor_manager.set_interval(interval)
            elif action == "set_target":
                target = float(msg.get("target", 25.0))
                result = sensor_manager.set_target_temp(target)
            else:
                result = {"status": "error", "message": f"Unknown action: {action}"}

            await websocket.send_text(json.dumps({"type": "response", "data": result}))

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WS error: {e}")
    finally:
        push_task.cancel()
        sensor_manager.remove_client(q)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001, log_level="info")
