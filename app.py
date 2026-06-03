from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from models import SessionLocal, SensorReading
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


@app.get("/api/history/db")
async def get_history_db(limit: int = 50, from_date: str = None):
    """Load archived data from SQLite DB with optional date filter."""
    from datetime import datetime
    db = SessionLocal()
    query = db.query(SensorReading).order_by(SensorReading.timestamp.desc())
    if from_date:
        try:
            dt = datetime.strptime(from_date, "%Y-%m-%d")
            query = query.filter(SensorReading.timestamp >= dt)
        except ValueError:
            pass
    readings = query.limit(max(1, min(limit, 500))).all()
    data = [r.to_dict() for r in readings]
    db.close()
    return JSONResponse(content=data)


@app.get("/api/history/csv")
async def get_history_csv(limit: int = 50):
    """Load archived data from CSV file."""
    import csv as csv_mod, os
    csv_path = "archive.csv"
    if not os.path.exists(csv_path):
        return JSONResponse(content=[])
    rows = []
    with open(csv_path, "r", newline="", encoding="utf-8") as f:
        reader = csv_mod.DictReader(f)
        for row in reader:
            try:
                rows.append({
                    "timestamp": row.get("timestamp", ""),
                    "temp":      float(row.get("temp", 0)),
                    "hum":       float(row.get("hum", 0)),
                    "light":     int(float(row.get("light", 0))),
                    "light_val": int(float(row.get("light_val", 0))),
                })
            except (ValueError, KeyError):
                continue
    # Return last N rows
    limit = max(1, min(limit, 500))
    return JSONResponse(content=rows[-limit:])
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
