import threading
import time
import random
import csv
import os
import json
import serial
from datetime import datetime
from models import SessionLocal, SensorReading


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
        self._csv_path = "archive.csv"

        self.serial_port = port
        self.baudrate = baudrate
        self.arduino = None
        self.simulation_mode = True

        if not os.path.exists(self._csv_path):
            with open(self._csv_path, "w", newline="") as f:
                csv.writer(f).writerow(["timestamp", "temp", "hum", "target_temp", "actuator", "light", "light_val", "state"])

    def _try_connect_arduino(self):
        if self.arduino and self.arduino.is_open:
            return
        try:
            self.arduino = serial.Serial(self.serial_port, self.baudrate, timeout=1)
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
        if self.simulation_mode:
            self._sim_thread = threading.Thread(target=self._simulator_worker, daemon=True)
            self._sim_thread.start()
        else:
            if self.arduino and self.arduino.is_open:
                try:
                    self.arduino.write(b"start\n")
                    print("[Hardware] Sent start command to ESP32")
                except Exception as e:
                    print(f"[Hardware] Write error: {e}")
            
        self._broadcast_status("start", "Monitoring started.", trigger)
        return {"status": "success", "message": "Monitoring started."}

    def stop_monitoring(self, trigger=None):
        if not self.running:
            return {"status": "success", "message": "Monitoring already stopped."}
        self.running = False
        if not self.simulation_mode and self.arduino and self.arduino.is_open:
            try:
                self.arduino.write(b"stop\n")
                print("[Hardware] Sent stop command to ESP32")
            except Exception as e:
                print(f"[Hardware] Write error: {e}")
        self._broadcast_status("stop", "Monitoring stopped.", trigger)
        return {"status": "success", "message": "Monitoring stopped."}

    def set_interval(self, seconds: float):
        self.interval = max(0.5, float(seconds))
        return {"status": "success", "message": f"Refresh rate: {self.interval}s"}

    def set_target_temp(self, temp: float):
        self.target_temp = float(temp)
        return {"status": "success", "message": f"Target temperature set to {self.target_temp}°C"}

    def _process_data(self, temp, hum, light=0, light_val=0):
        """Regulation loop, archival and broadcasting"""
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

        # --- Archive to DB ---
        try:
            db = SessionLocal()
            db.add(SensorReading(
                temp=temp, hum=hum, 
                target_temp=self.target_temp, 
                actuator=self.actuator_state,
                light=light,
                light_val=light_val,
                state="RUNNING", timestamp=now
            ))
            db.commit()
        except Exception as e:
            print(f"[DB Error] {e}")
        finally:
            try:
                db.close()
            except:
                pass

        # --- Archive to CSV ---
        try:
            with open(self._csv_path, "a", newline="") as f:
                csv.writer(f).writerow([ts, temp, hum, self.target_temp, self.actuator_state, light, light_val, "RUNNING"])
        except Exception as e:
            print(f"[CSV Error] {e}")

        # --- Broadcast ---
        with self._lock:
            clients_snapshot = list(self._clients.items())

        for q, loop in clients_snapshot:
            try:
                loop.call_soon_threadsafe(q.put_nowait, payload)
            except:
                pass

    def _simulator_worker(self):
        while self.running and self.simulation_mode:
            temp = round(random.uniform(20.0, 30.0), 2)
            hum = round(random.uniform(40.0, 60.0), 2)
            light_val = random.randint(500, 3500)
            light = 1 if light_val >= 2200 else 0
            self._process_data(temp, hum, light, light_val)
            time.sleep(self.interval)

    def _serial_listener(self):
        if self.arduino:
            self.arduino.reset_input_buffer()
            
        while self.active and not self.simulation_mode:
            try:
                if self.arduino and self.arduino.in_waiting > 0:
                    line = self.arduino.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        try:
                            data = json.loads(line)
                            if "action" in data:
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
                self.simulation_mode = True
                # If we lose connection, fallback to simulation if still running
                if self.running:
                    self._sim_thread = threading.Thread(target=self._simulator_worker, daemon=True)
                    self._sim_thread.start()
                break
