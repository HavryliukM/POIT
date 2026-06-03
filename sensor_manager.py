import threading
import time
import random
import csv
import os
import json
import serial
from datetime import datetime
from models import SessionLocal, SensorReading, SavedSession


class SensorManager:
    """
    Manages sensor simulation or Arduino hardware integration.
    Broadcasts data and actuator state to all connected WebSocket clients.
    """

    def __init__(self, port="COM5", baudrate=9600):
        self.running = False
        self.active = False
        self.interval = 1.0          
        self.target_temp = 25.0       # Target temperature for regulation
        self.actuator_state = 0       # 0 = OFF (Normal), 1 = ON (Cooling active)
        
        self._sim_thread = None
        self._serial_thread = None
        self._clients = {}            
        self._lock = threading.Lock()
        self._serial_lock = threading.Lock() # Lock to synchronize serial read/write
        self._csv_path = "archive.csv"
        self.session_buffer = []      # Buffer for current session

        self.serial_port = port
        self.baudrate = baudrate
        self.arduino = None
        self.simulation_mode = True

        if not os.path.exists(self._csv_path):
            with open(self._csv_path, "w", newline="") as f:
                csv.writer(f).writerow(["timestamp", "temp", "hum", "target_temp", "actuator", "light", "light_val", "state"])

    def _try_connect_arduino(self):
        with self._serial_lock:
            if self.arduino and self.arduino.is_open:
                return
            try:
                self.arduino = serial.Serial(self.serial_port, self.baudrate, timeout=1)
                self.arduino.dtr = False
                self.arduino.rts = False
                time.sleep(2) # Arduino auto-reset delay
                self.simulation_mode = False
                print(f"[Hardware] Connected to Arduino on {self.serial_port}")
            except Exception as e:
                self.simulation_mode = True
                print(f"[Hardware] Failed to connect to Arduino on {self.serial_port}. Using simulation mode.")

    def add_client(self, loop, queue):
        with self._lock:
            self._clients[queue] = loop

    def remove_client(self, queue):
        with self._lock:
            self._clients.pop(queue, None)

    def _broadcast_status(self, action, message, trigger=None):
        payload = {
            "type": "status_update",
            "data": {
                "action": action,
                "message": message,
                "trigger": trigger,
                "isRunning": self.running,
                "isOpen": self.active
            }
        }
        with self._lock:
            clients_snapshot = list(self._clients.items())

        for q, loop in clients_snapshot:
            try:
                loop.call_soon_threadsafe(q.put_nowait, payload)
            except:
                pass

    def open_system(self):
        self.active = True
        self._try_connect_arduino()
        
        if not self.simulation_mode and (self._serial_thread is None or not self._serial_thread.is_alive()):
            self._serial_thread = threading.Thread(target=self._serial_listener, daemon=True)
            self._serial_thread.start()
            
        self._broadcast_status("open", "System initialized.")
        return {"status": "success", "message": "System initialized."}

    def close_system(self):
        self.stop_monitoring()
        self.active = False
        with self._serial_lock:
            if self.arduino and self.arduino.is_open:
                self.arduino.close()
        self._broadcast_status("close", "System deactivated.")
        return {"status": "success", "message": "System deactivated."}

    def start_monitoring(self, trigger=None):
        if not self.active:
            return {"status": "error", "message": "System not open. Press Open first."}
        if self.running:
            return {"status": "success", "message": "Monitoring already running."}

        self.running = True
        self.session_buffer = [] # Clear buffer for new run
        if self.simulation_mode:
            self._sim_thread = threading.Thread(target=self._simulator_worker, daemon=True)
            self._sim_thread.start()
        else:
            with self._serial_lock:
                if self.arduino and self.arduino.is_open:
                    try:
                        self.arduino.write(b"start\n")
                        self.arduino.flush()
                        print("[Hardware] Sent start command to ESP32")
                    except Exception as e:
                        print(f"[Hardware] Write error: {e}")
            
        self._broadcast_status("start", "Monitoring started.", trigger)
        return {"status": "success", "message": "Monitoring started."}

    def stop_monitoring(self, trigger=None):
        if not self.running:
            return {"status": "success", "message": "Monitoring already stopped."}
        self.running = False
        if not self.simulation_mode:
            with self._serial_lock:
                if self.arduino and self.arduino.is_open:
                    try:
                        self.arduino.write(b"stop\n")
                        self.arduino.flush()
                        print("[Hardware] Sent stop command to ESP32")
                    except Exception as e:
                        print(f"[Hardware] Write error: {e}")
        self._broadcast_status("stop", "Monitoring stopped.", trigger)
        return {"status": "success", "message": "Monitoring stopped."}

    def set_interval(self, seconds: float):
        self.interval = max(0.5, float(seconds))
        if not self.simulation_mode:
            with self._serial_lock:
                if self.arduino and self.arduino.is_open:
                    try:
                        ms = int(self.interval * 1000)
                        self.arduino.write(f"interval:{ms}\n".encode())
                        self.arduino.flush()
                        print(f"[Hardware] Sent interval update to ESP32: {ms}ms")
                    except Exception as e:
                        print(f"[Hardware] Write error: {e}")
        return {"status": "success", "message": f"Refresh rate: {self.interval}s"}

    def set_target_temp(self, temp: float):
        self.target_temp = float(temp)
        return {"status": "success", "message": f"Target temperature set to {self.target_temp}°C"}

    def _process_data(self, temp, hum, light=0, light_val=0):
        """Regulation loop, archival and broadcasting"""
        # Ignore nonsense/invalid data
        if temp == 0.0 or hum == 0.0 or temp > 60.0 or temp < -10.0 or hum > 100.0 or hum < 0.0:
            return

        # Print to server terminal like Arduino serial port
        print(f'{{"temp": {temp:.2f}, "hum": {hum:.2f}, "light": {light}, "light_val": {light_val}}}', flush=True)

        if temp > self.target_temp + 0.5:
            self.actuator_state = 1
        elif temp < self.target_temp - 0.5:
            self.actuator_state = 0
            
        now = datetime.now()
        ts = now.strftime("%Y-%m-%d %H:%M:%S")

        payload = {
            "type": "sensor_data",
            "data": {
                "timestamp": ts, 
                "temp": temp, 
                "hum": hum, 
                "light": light,
                "light_val": light_val
            }
        }

        # --- Buffer for manual save ---
        self.session_buffer.append({
            "temp": temp,
            "hum": hum,
            "target_temp": self.target_temp,
            "actuator": self.actuator_state,
            "light": light,
            "light_val": light_val,
            "state": "RUNNING",
            "timestamp": now
        })

        # --- Broadcast ---
        with self._lock:
            clients_snapshot = list(self._clients.items())

        for q, loop in clients_snapshot:
            try:
                loop.call_soon_threadsafe(q.put_nowait, payload)
            except:
                pass

    def save_to_db(self):
        if not self.session_buffer:
            return {"status": "error", "message": "Žiadne nové dáta na uloženie do DB."}
        
        try:
            # Package session data into a JSON list
            serialized_data = []
            for r in self.session_buffer:
                serialized_data.append({
                    "timestamp": r["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
                    "temp": r["temp"],
                    "hum": r["hum"],
                    "target_temp": r["target_temp"],
                    "actuator": r["actuator"],
                    "light": r["light"],
                    "light_val": r["light_val"],
                    "state": r["state"]
                })
            
            db = SessionLocal()
            session_record = SavedSession(data=json.dumps(serialized_data))
            db.add(session_record)
            db.commit()
            session_id = session_record.id
            db.close()
            return {"status": "success", "message": f"Uložené do DB pod ID: {session_id} ({len(self.session_buffer)} bodov)"}
        except Exception as e:
            return {"status": "error", "message": f"Chyba pri ukladaní do DB: {e}"}

    def save_to_csv(self):
        if not self.session_buffer:
            return {"status": "error", "message": "Žiadne nové dáta na uloženie do CSV."}
        
        try:
            # Create a dedicated csv filename using unique timestamp
            ts_suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"archive_session_{ts_suffix}.csv"
            
            with open(filename, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp", "temp", "hum", "target_temp", "actuator", "light", "light_val", "state"])
                for r in self.session_buffer:
                    ts_str = r["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
                    writer.writerow([
                        ts_str, r["temp"], r["hum"], r["target_temp"],
                        r["actuator"], r["light"], r["light_val"], r["state"]
                    ])
            return {"status": "success", "message": f"Uložené do súboru: {filename} ({len(self.session_buffer)} riadkov)"}
        except Exception as e:
            return {"status": "error", "message": f"Chyba pri ukladaní do CSV: {e}"}

    def _simulator_worker(self):
        while self.running and self.simulation_mode:
            temp = round(random.uniform(20.0, 30.0), 2)
            hum = round(random.uniform(40.0, 60.0), 2)
            light_val = random.randint(500, 3500)
            light = 1 if light_val >= 2200 else 0
            self._process_data(temp, hum, light, light_val)
            time.sleep(self.interval)

    def _serial_listener(self):
        with self._serial_lock:
            if self.arduino:
                try:
                    self.arduino.reset_input_buffer()
                except Exception as e:
                    print(f"[Hardware] Failed to reset input buffer: {e}")
            
        while self.active and not self.simulation_mode:
            try:
                line = None
                with self._serial_lock:
                    if self.arduino and self.arduino.is_open and self.arduino.in_waiting > 0:
                        line = self.arduino.readline().decode('utf-8', errors='ignore').strip()
                
                if line:
                    try:
                        data = json.loads(line)
                        if "error" in data:
                            print(f"[ESP32 Error] {data['error']}", flush=True)
                        elif "action" in data:
                            action = data.get("action", "")
                            trigger = data.get("trigger", "IR prekážkový senzor")
                            if action == "start" and not self.running:
                                print(f"[Hardware] Triggered START by {trigger}")
                                self.start_monitoring(trigger)
                            elif action == "stop" and self.running:
                                print(f"[Hardware] Triggered STOP by {trigger}")
                                self.stop_monitoring(trigger)
                        elif "temp" in data and "hum" in data and self.running:
                            temp = float(data["temp"])
                            hum = float(data["hum"])
                            light = int(data.get("light", 0))
                            light_val = int(data.get("light_val", 0))
                            self._process_data(temp, hum, light, light_val)
                    except json.JSONDecodeError:
                        pass # Ignore malformed json
                else:
                    time.sleep(0.05)
            except Exception as e:
                print(f"[Hardware] Serial read error: {e}")
                break
