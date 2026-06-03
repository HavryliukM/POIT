#include <DHT.h>
#include <IRremote.h> // Používa štandardnú knižnicu IRremote

// Definícia pinov na ESP32 (Číslo GPIO zodpovedá označeniu D na väčšine NodeMCU dosiek)
#define DHTPIN 23        // Pin pre DHT11 dáta -> zapoj na doske na pin D23
#define DHTTYPE DHT11    // Typ senzora: DHT11
#define IRPIN 19         // Vstup pre IR prekážkový senzor -> zapoj na doske na pin D19
#define LDRPIN 34        // Vstup pre LDR fotoodpor -> zapoj na doske na pin D34 (alebo VP / P34)
#define IR_RECV_PIN 18   // Vstup pre IR prijímač -> zapoj na doske na pin D18

DHT dht(DHTPIN, DHTTYPE);

bool isMeasuring = false;
int lastIrState = HIGH;

unsigned long lastDebounceTime = 0;
unsigned long debounceDelay = 250; // Ochraná lehota pre prekážkový senzor

unsigned long lastMeasurementTime = 0;
unsigned long measurementInterval = 1000; // Interval merania (1 sekunda)

// Prahová hodnota pre detekciu priameho svetla (0 - 4095 na 12-bit ADC ESP32)
// Čím viac svetla dopadá na fotoodpor v zapojení s 10k pull-down odporom, tým je hodnota bližšia k 4095.
const int LIGHT_THRESHOLD = 2200; 

void setup() {
  Serial.begin(9600); // Inicializácia sériového spojenia s Python backendom
  dht.begin();
  
  pinMode(IRPIN, INPUT);
  pinMode(LDRPIN, INPUT);
  
  // Inicializácia IR prijímača z telefónu / ovládača
  IrReceiver.begin(IR_RECV_PIN, ENABLE_LED_FEEDBACK);
  
  delay(1500);
  Serial.println("{\"status\": \"Arduino/ESP32 Initialized\"}");
}

void loop() {
  // 0. Kontrola prichádzajúcich príkazov z Pythonu cez Serial
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

  // 1. Kontrola IR prekážkového senzora (mávnutie rukou na štart/stop)
  int irState = digitalRead(IRPIN);
  
  // Prekážkový senzor vracia LOW pri detekcii ruky/prekážky
  if (irState == LOW && lastIrState == HIGH && (millis() - lastDebounceTime) > debounceDelay) {
    isMeasuring = !isMeasuring;
    lastDebounceTime = millis();
    
    // Oznámenie stavu cez sériovú linku
    if (isMeasuring) {
      Serial.println("{\"action\": \"start\", \"trigger\": \"IR prekážkový senzor\"}");
    } else {
      Serial.println("{\"action\": \"stop\", \"trigger\": \"IR prekážkový senzor\"}");
    }
  }
  lastIrState = irState;

  // 2. Kontrola signálu z IR prijímača (ovládanie telefónom / ovládačom)
  if (IrReceiver.decode()) {
    // Ak dostaneme akýkoľvek platný IR signál (alebo špecifické tlačidlo)
    // Prepne stav snímania (štart / stop)
    if ((millis() - lastDebounceTime) > debounceDelay) {
      isMeasuring = !isMeasuring;
      lastDebounceTime = millis();
      
      if (isMeasuring) {
        Serial.println("{\"action\": \"start\", \"trigger\": \"IR diaľkový ovládač\"}");
      } else {
        Serial.println("{\"action\": \"stop\", \"trigger\": \"IR diaľkový ovládač\"}");
      }
    }
    IrReceiver.resume(); // Pripraví prijímač na ďalší kód
  }

  // 3. Meranie teploty, vlhkosti a svetla
  if (isMeasuring) {
    if (millis() - lastMeasurementTime > measurementInterval) {
      lastMeasurementTime = millis();
      
      float h = dht.readHumidity();
      float t = dht.readTemperature();
      int lightVal = analogRead(LDRPIN);
      int directLight = (lightVal >= LIGHT_THRESHOLD) ? 1 : 0;

      // Odoslanie kompletného JSONu cez Serial
      if (!isnan(h) && !isnan(t)) {
        Serial.print("{\"temp\": ");
        Serial.print(t);
        Serial.print(", \"hum\": ");
        Serial.print(h);
        Serial.print(", \"light\": ");
        Serial.print(directLight);
        Serial.print(", \"light_val\": ");
        Serial.print(lightVal);
        Serial.println("}");
      } else {
        Serial.println("{\"error\": \"Failed to read from DHT sensor!\"}");
      }
    }
  }
}
