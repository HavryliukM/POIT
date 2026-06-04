# IoT Control Center

Webová IoT aplikácia pre real-time monitorovanie teploty, vlhkosti a intenzity osvetlenia pomocou mikrokontroléra **NodeMCU ESP32** a senzora **DHT11**. Backend postavený na **FastAPI + WebSockets**, frontend na čistom **HTML/CSS/JavaScript** s knižnicou **Chart.js**.

---

## Funkcie

- **Real-time vizualizácia** — animované SVG ciferníky (gauges) a dual-axis Chart.js graf aktualizované cez WebSocket
- **5-stupňové vyhodnotenie osvetlenia** — Tma / Tieň / Slabé svetlo / Silné svetlo / Priame svetlo (na základe ADC hodnoty LDR)
- **Automatické zastavenie pri priamom svetle** — ak LDR hodnota ≥ 3000, systém zastaví meranie a notifikuje UI
- **IR ovládanie** — mávnutie rukou (IR prekážkový senzor) alebo signál z diaľkového ovládača / telefónu (IR prijímač) prepína start/stop
- **Manuálna archivácia** — merania sa počas relácie bufferjú v pamäti; tlačidlo „Uložiť" ich zapíše do SQLite alebo CSV
- **Archívna vizualizácia** — načítanie a vykreslenie ľubovoľnej uloženej relácie (z DB podľa ID alebo z CSV súboru)
- **Simulačný režim** — ak ESP32 nie je pripojené, systém automaticky generuje syntetické dáta
- **Automatický reconnect** — WebSocket klient sa sám znovu pripája pri výpadku

<div align="center">
  <img src="docs/dashboard_monitoring.png" alt="Dashboard Monitoring" width="800"/>
</div>

---

## Technologický zásobník

| Vrstva | Technológia |
|:---|:---|
| Mikrokontrolér | NodeMCU ESP32 (Arduino framework) |
| Senzory | DHT11, LDR fotoodpor, IR prekážkový senzor, IR prijímač TSOP |
| Backend | Python 3.8+, FastAPI, Uvicorn, SQLAlchemy, pyserial |
| Databáza | SQLite (`database.db`) |
| Archívny súbor | CSV (`archive_session_YYYYMMDD_HHMMSS.csv`) |
| Frontend | HTML5, CSS3 (Vanilla), JavaScript ES6+ |
| Vizualizácia | Chart.js 4.x, SVG stroke-dasharray gauges |
| Komunikácia | WebSocket (real-time), HTTP REST (história, archív) |

---

## Splnenie požiadaviek zadania

| # | Požiadavka | Implementácia |
|:---:|:---|:---|
| 1 | **Open** | `SensorManager.open_system()` — spojenie s ESP32 alebo fallback do simulácie |
| 2 | **Nastavenie parametrov** | Perióda merania (s) nastaviteľná cez UI, odoslaná na ESP32 príkazom `interval:<ms>` |
| 3 | **Start** | `SensorManager.start_monitoring()` — spustí vlákno, vyčistí graf pre novú reláciu |
| 4 | **Výpis dát** | Tabuľka hodnôt s časom, teplotou, vlhkosťou a kategóriou osvetlenia |
| 5 | **Grafy** | Dual-axis Chart.js graf (teplota °C / vlhkosť %) pre celú reláciu |
| 6 | **Ciferníky** | SVG animované oblúky pre teplotu (0–50°C) a vlhkosť (0–100%) |
| 7 | **DB archív** | Manuálne uloženie relácie do SQLite, načítanie podľa ID s grafom a tabuľkou |
| 8 | **CSV archív** | Manuálne uloženie relácie do timestampovaného CSV súboru, výber zo zoznamu |
| 9 | **Stop** | `SensorManager.stop_monitoring()` — zastavenie vlákna + príkaz na ESP32 |
| 10 | **Close** | `SensorManager.close_system()` — zatvorenie Serial portu, deaktivácia systému |

---

## Rýchly štart

### 1. Inštalácia závislostí

```bash
pip install fastapi uvicorn sqlalchemy pyserial
```

### 2. (Voliteľné) Nahranie firmware do ESP32

1. Otvor `arduino_sketch/arduino_sketch.ino` v **Arduino IDE**
2. Nainštaluj knižnice cez *Library Manager*:
   - `DHT sensor library` (Adafruit)
   - `IRremote` (Armin Joachimsmeyer, v4.x)
3. Vyber dosku **ESP32 Dev Module** a správny COM port, nahraj kód

### 3. Konfigurácia COM portu

V súbore `sensor_manager.py`, riadok s `__init__`:
```python
def __init__(self, port="COM5", baudrate=9600):
```
Zmeň `"COM5"` na skutočný port ESP32 (napr. `COM3` na Windows, `/dev/ttyUSB0` na Linux).

### 4. Spustenie servera

```bash
python app.py
```

### 5. Otvor dashboard

```
http://127.0.0.1:5001
```

---

## Spustenie na Raspberry Pi OS (vo VirtualBox / VMware)

### Predpoklady

- Nainštalovaný **VirtualBox** alebo **VMware** na hostiteľskom PC
- Stiahnutý ISO obraz **Raspberry Pi OS** (64-bit Desktop): [raspberrypi.com/software](https://www.raspberrypi.com/software/operating-systems/)
- ESP32 pripojený cez USB do hostiteľského PC

---

### Krok 1 — USB Passthrough (prebratie ESP32 do VM)

> Kľúčový krok — bez neho VM nevidí ESP32.

**VirtualBox:**
1. Nainštaluj **VirtualBox Extension Pack** (rovnaká verzia ako VirtualBox, stiahni z virtualbox.org)
2. Vyber VM → **Nastavenia → USB → Pridaj filter** (ikona USB so `+`)
3. Vyber **Silicon Labs CP210x** alebo **CH340** (závisí od čipu tvojho ESP32)
4. Potvrď a spusti VM

**VMware:**
1. VM → **Settings → USB Controller → USB 3.1** (alebo 2.0)
2. Po spustení VM: **VM → Removable Devices → Silicon Labs CP210x → Connect**

---

### Krok 2 — Zistenie portu

Po pripojení ESP32 cez USB passthrough otvor terminál vo VM:

```bash
dmesg | tail -20
# Hľadaj riadok: "cp210x converter now attached to ttyUSB0"
# alebo:
ls /dev/ttyUSB* /dev/ttyACM*
sudo dmesg | grep -i usb
sudo dmesg | grep -i tty
```

ESP32 je zvyčajne `/dev/ttyUSB0` alebo vo VM `/dev/ttyACM0`.

---

### Krok 3 — Inštalácia závislostí

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip git -y
pip3 install fastapi uvicorn sqlalchemy pyserial
pip3 intall websockets
```

---

### Krok 4 — Klon projektu

```bash
git clone https://github.com/HavryliukM/POIT.git
cd POIT
```

---

### Krok 5 —  Zmeň serial port v kóde

V súbore `sensor_manager.py` zmeň riadok:

```python
# Pôvodné (Windows):
def __init__(self, port="COM5", baudrate=9600):

# Zmeň na:
def __init__(self, port="/dev/ttyACM0", baudrate=9600):
```

---

### Krok 6 — Spustenie servera

```bash
python3 app.py
```

---

### Krok 7 — Otvorenie dashboardu

- **Z VM samotnej:** `http://127.0.0.1:5001`
- **Z hostiteľského PC:** zisti IP VM cez `hostname -I`, potom `http://[IP-VM]:5001`

---

### Windows vs. Raspberry Pi OS — rozdiely

| | Windows | Raspberry Pi OS (VM/natívne) |
|:---|:---|:---|
| Serial port | `COM5` | `/dev/ttyUSB0` `/dev/ttyACM0` |
| Spustenie | `python app.py` | `python3 app.py` |
| Dashboard URL | `http://127.0.0.1:5001` | `http://127.0.0.1:5001` alebo `http://[IP]:5001` |

---

## Použité hardvérové komponenty

- **Senzor teploty a vlhkosti DHT11** — DHT11 na doske s LED + kábliky (#VST7991)
- **Nepájivé pole** 400 bodov (#DPS174)
- **Vývojová doska** NODE MCU ESP32 WiFi + Bluetooth - Áno (#IOT7551), naspájkované piny
- **Kábliky** 10 kusov 10 cm M-M a 10 kusov 10 cm M-F (#KAB999)
- **Rezistor** 10K ohm 1/4W z balenia (#ICS36904)
- **Fotorezistor** GL5528 (#ICS944)
- **Infračervený prijímač** VS1838 (#VST319)
- **Infračervený senzor prekážok** TCRT5000 (#VST884)

---

## Zapojenie senzorov (NodeMCU ESP32)

| Senzor | Pin senzora | GPIO | Označenie na doske | Poznámka |
|:---|:---|:---|:---|:---|
| **DHT11** | VCC | — | 3V3 | Napájanie 3.3 V |
| | GND | — | GND | Spoločná zem |
| | DATA | **GPIO 23** | D23 | Dátový pin |
| **IR prekážkový** | VCC | — | 3V3 | Napájanie |
| | GND | — | GND | Spoločná zem |
| | D0 | **GPIO 19** | D19 | LOW pri detekcii ruky |
| **LDR fotoodpor** | Nožička 1 | — | 3V3 | Cez LDR na napájanie |
| | Nožička 2 | **GPIO 34** | D34 / VP | ADC vstup + 10 kΩ rezistor na GND |
| **IR prijímač TSOP**| VCC | — | 3V3 | Napájanie |
| | GND | — | GND | Spoločná zem |
| | OUT | **GPIO 18** | D18 | Príjem IR signálov |

> **LDR delič napätia:** Fotoodpor je zapojený s 10 kΩ pull-down rezistorom. Čím viac svetla, tým vyšší napäťový potenciál na GPIO 34 (hodnota 0–4095 na 12-bit ADC ESP32).

---

## Štruktúra projektu

```
Project11/
├── app.py                        # FastAPI server, WebSocket hub, REST API
├── sensor_manager.py             # SensorManager — vlákna, broadcast, archivácia
├── models.py                     # SQLAlchemy ORM modely (SensorReading, SavedSession)
├── database.db                   # SQLite databáza (automaticky vytvorená)
├── archive_session_*.csv         # CSV archívy relácií (vytvorené manuálne)
├── arduino_sketch/
│   └── arduino_sketch.ino        # Firmware ESP32 (Arduino IDE)
├── static/
│   ├── css/style.css             # Design systém (dark glassmorphism)
│   └── js/main.js                # WebSocket klient, Chart.js, gauges, archív
├── templates/
│   └── index.html                # Jinja2 HTML šablóna dashboardu
├── README.md                     # Tento súbor
└── DOCUMENTATION.md              # Technická + používateľská príručka
```

---

## Licencia

Projekt bol vytvorený ako súčasť predmetu POIT (Programovanie a ovládanie IoT systémov).  
Autor: **Michal Havryliuk**
