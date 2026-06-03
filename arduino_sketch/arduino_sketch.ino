#include <DHT.h>
#include <IRremote.h> // Používa štandardnú knižnicu IRremote

// Definícia pinov na ESP32
#define DHTPIN 23        // Pin pre DHT11 dáta
#define DHTTYPE DHT11    // Typ senzora: DHT11
#define IRPIN 19         // Vstup pre IR prekážkový senzor
#define LDRPIN 34        // Vstup pre LDR fotoodpor
#define IR_RECV_PIN 18   // Vstup pre IR prijímač

DHT dht(DHTPIN, DHTTYPE);

bool isMeasuring = false;
int lastIrState = HIGH;

unsigned long lastDebounceTime = 0;
unsigned long debounceDelay = 250; // Ochranná lehota

unsigned long lastMeasurementTime = 0;
unsigned long measurementInterval = 1000; // Interval merania

unsigned long lastLightCheckTime = 0;
const unsigned long LIGHT_CHECK_INTERVAL = 2000; // Kontrola svetla

void setup() {
  Serial.begin(9600); // Sériové spojenie s Pythonom
  dht.begin();
  
  pinMode(IRPIN, INPUT);
  pinMode(LDRPIN, INPUT);
  
  // Inicializácia IR prijímača z telefónu / ovládača
  IrReceiver.begin(IR_RECV_PIN, ENABLE_LED_FEEDBACK);
  
  delay(1500);
  Serial.println("{\"status\": \"Arduino/ESP32 Initialized\"}");
}

void loop() {
  // 0. Príkazy z Pythonu
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (cmd == "start") {
      isMeasuring = true;
      Serial.println("{\"action\": \"start\", \"trigger\": \"Web UI\"}");
    } else if (cmd == "stop") {
      isMeasuring = false;
      Serial.println("{\"action\": \"stop\", \"trigger\": \"Web UI\"}");
    } else if (cmd.startsWith("interval:")) {
      String msStr = cmd.substring(9);
      long newInterval = msStr.toInt();
      if (newInterval >= 500) {
        measurementInterval = newInterval;
      }
    }
  }

  // 1. Kontrola IR prekážkového senzora
  int irState = digitalRead(IRPIN);
  
  // LOW = detekcia prekážky
  if (irState == LOW && lastIrState == HIGH && (millis() - lastDebounceTime) > debounceDelay) {
    isMeasuring = !isMeasuring;
    lastDebounceTime = millis();
    
    // Oznámenie stavu
    if (isMeasuring) {
      Serial.println("{\"action\": \"start\", \"trigger\": \"IR prekážkový senzor\"}");
    } else {
      Serial.println("{\"action\": \"stop\", \"trigger\": \"IR prekážkový senzor\"}");
    }
  }
  lastIrState = irState;

  // 2. Kontrola signálu z IR prijímača
  if (IrReceiver.decode()) {
    // Prepne stav merania po prijatí kódu
    if ((millis() - lastDebounceTime) > debounceDelay) {
      isMeasuring = !isMeasuring;
      lastDebounceTime = millis();
      
      if (isMeasuring) {
        Serial.println("{\"action\": \"start\", \"trigger\": \"IR diaľkový ovládač\"}");
      } else {
        Serial.println("{\"action\": \"stop\", \"trigger\": \"IR diaľkový ovládač\"}");
      }
    }
    IrReceiver.resume(); // Ďalší kód
  }

  // 3. Meranie teploty, vlhkosti a svetla
  if (isMeasuring) {
    if (millis() - lastMeasurementTime > measurementInterval) {
      lastMeasurementTime = millis();
      
      float h = dht.readHumidity();
      float t = dht.readTemperature();
      int lightVal = analogRead(LDRPIN);

      // Odoslanie JSON dát
      if (!isnan(h) && !isnan(t)) {
        Serial.print("{\"temp\": ");
        Serial.print(t);
        Serial.print(", \"hum\": ");
        Serial.print(h);
        Serial.print(", \"light_val\": ");
        Serial.print(lightVal);
        Serial.println("}");
      } else {
        Serial.println("{\"error\": \"Failed to read from DHT sensor!\"}");
      }
    }
  }

  // 4. Sledovanie svetla pri zastavenom meraní
  if (!isMeasuring) {
    if (millis() - lastLightCheckTime > LIGHT_CHECK_INTERVAL) {
      lastLightCheckTime = millis();
      int lightVal = analogRead(LDRPIN);
      Serial.print("{\"light_val\": ");
      Serial.print(lightVal);
      Serial.println("}");
    }
  }
}
