// ChainBreak Wokwi live-data source (build prompt v4 Section 6, v3 Section 10).
//
// Virtual ESP32 + DHT22 + potentiometer. Publishes plain numeric values
// (the backend parses plain floats, JSON {"value": x}, or Wokwi JSON) to
// CONFIGURABLE topics — set the three #defines below to the exact
// mqtt_topic strings you bound to nodes in the Environment Builder
// (e.g. chainbreak/env1/cooling/temp).
//
// Broker: broker.hivemq.com (shared, namespaced — Section 12.5).
// The backend subscribes with a wildcard, so topics bind instantly after
// you add them in the builder — no backend restart needed.

#include <WiFi.h>
#include <PubSubClient.h>

// ---------------- CONFIGURE ME (must match sensor_bindings.mqtt_topic) ----
#define WIFI_SSID      "Wokwi-GUEST"
#define WIFI_PASSWORD  ""
#define MQTT_BROKER    "broker.hivemq.com"
#define MQTT_PORT      1883
#define TOPIC_TEMP     "chainbreak/env1/cooling/temp"     // degC
#define TOPIC_HUM      "chainbreak/env1/treatment/level"  // % (repurposed)
#define TOPIC_POT      "chainbreak/env1/pot/position"     // raw 0-4095
#define PUBLISH_EVERY_MS 3000
// ---------------------------------------------------------------------------

const char* deviceId = "wokwi-esp32-1";

WiFiClient wifi;
PubSubClient mqtt(wifi);

const int DHT_PIN = 15;
const int POT_PIN = 34;

// Simple DHT22 read via the built-in Wokwi-supported library
#include <DHT.h>
DHT dht(DHT_PIN, DHT22);

void connectWifi() {
  Serial.print("WiFi connecting");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD, 6);
  while (WiFi.status() != WL_CONNECTED) {
    delay(250);
    Serial.print(".");
  }
  Serial.print(" ok, ip=");
  Serial.println(WiFi.localIP());
}

void connectMqtt() {
  while (!mqtt.connected()) {
    Serial.print("MQTT connecting...");
    String clientId = String("chainbreak-") + deviceId + "-" + String(millis());
    if (mqtt.connect(clientId.c_str())) {
      Serial.println(" ok");
    } else {
      Serial.print(" failed rc=");
      Serial.println(mqtt.state());
      delay(1500);
    }
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(POT_PIN, INPUT);
  dht.begin();
  connectWifi();
  mqtt.setServer(MQTT_BROKER, MQTT_PORT);
  connectMqtt();
}

void publishIfBound(const char* topic, float value) {
  // plain numeric payload — the backend's preferred parse
  char payload[16];
  snprintf(payload, sizeof(payload), "%.2f", value);
  mqtt.publish(topic, payload);
  Serial.printf("-> %s = %s\n", topic, payload);
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) connectWifi();
  if (!mqtt.connected()) connectMqtt();
  mqtt.loop();

  static unsigned long last = 0;
  if (millis() - last < PUBLISH_EVERY_MS) return;
  last = millis();

  float tempC = dht.readTemperature();   // degC, ~24-28 in Wokwi
  float hum   = dht.readHumidity();      // %
  int   pot   = analogRead(POT_PIN);     // 0-4095, drag the knob in Wokwi

  if (!isnan(tempC)) publishIfBound(TOPIC_TEMP, tempC);
  if (!isnan(hum))   publishIfBound(TOPIC_HUM, hum * 2.0f); // ~50% RH -> ~100,
  // so a binding baseline of 100 gives warn 120 / fail 150 for an easy demo
  publishIfBound(TOPIC_POT, (float)pot);

  // Demo tip: with the binding baseline set to the DHT's ~26 degC room value,
  // cold-start thresholds are warn 31.2 / fail 39. Heat the sensor past 39
  // (the DHT22's temperature slider) and hold it there — the node flips to
  // failed and the cascade fires, no buttons anywhere.
}
