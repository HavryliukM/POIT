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
