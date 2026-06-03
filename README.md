# IoT Control Center

Modern IoT monitoring system designed for real-time sensor data visualization and archival. Built with FastAPI, WebSockets, and Chart.js.

## 🚀 Features

- **Real-time Visualization**: Dynamic line charts and radial gauges for temperature and humidity.
- **System States**: Managed state machine (Open, Start, Stop, Close) ensuring robust operation.
- **Dual Archiving**: Simultaneous data persistence to SQLite database and CSV log files.
- **Historical View**: Automatic retrieval of recent readings on startup.
- **Adaptive Performance**: User-configurable monitoring intervals (refresh rates).
- **Responsive Design**: Premium dark-themed UI with glassmorphism, optimized for multiple screen sizes.

## 🛠️ Technology Stack

- **Backend**: Python 3.x, FastAPI, SQLAlchemy, Uvicorn.
- **Communication**: Native WebSockets for low-latency telemetry.
- **Frontend**: Vanilla JavaScript (ES6+), CSS3 (Custom Design System), HTML5.
- **Visualization**: Chart.js (Trends), Canvas-Gauges (Radial Telemetry).
- **Database**: SQLite (Relational Storage), CSV (Flat-file Archival).

## 📋 Compliance with Requirements

This project fulfills all 10 points of the assignment:
1. **Open**: Initialization logic via `open_system()` method.
2. **Parameters**: Dynamic monitoring interval adjustment.
3. **Start**: Thread-safe monitoring activation.
4. **Data Listing**: Real-time history table with rolling pruning.
5. **Graphs**: Dynamic Chart.js trends with auto-scaling.
6. **Gauges**: Radial gauges for immediate telemetry.
7. **DB Archive**: Persistent storage in `database.db` with API retrieval.
8. **File Archive**: Log records appended to `archive.csv`.
9. **Stop**: Safe termination of monitoring threads.
10. **Close**: Full system deactivation and resource cleanup.

## 🏁 Getting Started

1. **Install Dependencies**:
   ```bash
   pip install fastapi uvicorn sqlalchemy pyserial
   ```

2. **Run Application**:
   ```bash
   python app.py
   ```

3. **Access Dashboard**:
   Open [http://127.0.0.1:5001](http://127.0.0.1:5001) in your browser.

## 🔌 NodeMCU ESP32 Hardware Setup

Projekt plne podporuje reálne zapojenie s mikrokontrolérom **NodeMCU ESP32** a sadou senzorov. Ak ESP32 pripojíte cez USB (sériový port `COM3` alebo iný), systém automaticky deteguje spojenie a prejde zo simulačného do hardvérového režimu.

### 1. Zoznam komponentov
- **NodeMCU ESP32** (Development Board)
- **DHT11** (Senzor teploty a vlhkosti)
- **Fotoodpor (LDR)** + **10kΩ rezistor** (Delič napätia pre intenzitu svetla)
- **IR prekážkový senzor (MH-Sensor-Series)** (Detekcia prekážky / mávnutia rukou)
- **IR prijímač (TSOP)** (Príjem signálu pre zapnutie/vypnutie z telefónu)
- Nepájivé pole, prepojovacie káble

### 2. Schéma zapojenia pinov (ESP32)

| Senzor | Pin Senzora | Interný GPIO pin (v kóde) | Popis na doske NodeMCU ESP32 | Poznámka |
| :--- | :--- | :--- | :--- | :--- |
| **DHT11** | VCC | - | **3V3** (alebo 3V) | Napájanie |
| | GND | - | **GND** (alebo G) | Spoločná zem |
| | DATA | **GPIO 23** | **D23** | Digitálny pin pre dáta |
| **IR prekážkový** | VCC | - | **3V3** (alebo 3V) | Napájanie |
| | GND | - | **GND** (alebo G) | Spoločná zem |
| | D0 (Digital) | **GPIO 19** | **D19** | Digitálny pin (LOW pri prekážke) |
| **LDR (Fotoodpor)**| Nožička 1 | - | **3V3** (alebo 3V) | Napájanie |
| | Nožička 2 | **GPIO 34 (Analog)**| **D34** (alebo VP / P34) | Analógový vstup + vodič na 10kΩ rezistor |
| | Rezistor | - | **GND** (alebo G) | Druhá nožička 10kΩ rezistora na GND |
| **IR Prijímač** | VCC | - | **3V3** (alebo 3V) | Napájanie |
| | GND | - | **GND** (alebo G) | Spoločná zem |
| | OUT / DATA | **GPIO 18** | **D18** | Digitálny pin pre IR signály |

### 3. Softvérová príprava ESP32
1. Otvorte súbor v zložke `arduino_sketch/arduino_sketch.ino` v Arduino IDE.
2. V Arduino IDE si nainštalujte nasledujúce knižnice (cez *Library Manager*):
   - **DHT sensor library** (od Adafruit)
   - **IRremote** (od Armin Joachimsmeyer)
3. Zvoľte správnu dosku (napr. *ESP32 Dev Module*) a port, a nahrajte kód.

### 4. Ovládanie hardvérom
- **Mávnutie rukou** pred IR prekážkovým senzorom zapne alebo vypne monitorovanie (štart/stop).
- **Vyslanie IR signálu** z telefónu (s IR blasterom) alebo akéhokoľvek diaľkového ovládača smerom k IR prijímaču taktiež prepne stav monitorovania (štart/stop).
- **Fotoodpor LDR** na základe intenzity svetla vyhodnocuje, či na zariadenie dopadá priame svetlo (zobrazí sa slnko/mesiac na webe).

## 📂 Project Structure

- `app.py`: FastAPI server and WebSocket hub.
- `sensor_manager.py`: Background thread management and sensor simulation.
- `models.py`: Database schema and ORM models.
- `static/`: Frontend assets (CSS, JS).
- `templates/`: HTML templates.
- `database.db`: SQLite database file.
- `archive.csv`: CSV archival file.
