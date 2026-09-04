/*
 * BlindVision Proof-of-Concept: ESP32-CAM (AI-Thinker, OV2640) firmware
 * (Section V.A).
 *
 * Captures a JPEG frame and posts it over Wi-Fi to a FastAPI cloud
 * detection endpoint (see ../cloud_server/app.py). On response, triggers a
 * buzzer pattern scaled to priority (3 pulses = high, 2 = medium,
 * 1 = low) and relays the spoken-guidance string to a paired phone over
 * Bluetooth (HC-05) for TTS output. A 3-second cooldown per object class
 * prevents repeated alerts for a stationary obstacle.
 */

#include "esp_camera.h"
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <SoftwareSerial.h>

// ---- Wi-Fi / server config --------------------------------------------------
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
const char* DETECTION_ENDPOINT = "http://YOUR_SERVER_HOST:8000/detect";

// ---- AI-Thinker ESP32-CAM pin map ------------------------------------------
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

// ---- HC-05 Bluetooth (to paired phone for TTS) -----------------------------
#define BT_RX_PIN  3
#define BT_TX_PIN  1
SoftwareSerial btSerial(BT_RX_PIN, BT_TX_PIN);

// ---- Buzzer -----------------------------------------------------------------
#define BUZZER_PIN 4

// ---- Per-class 3-second alert cooldown -------------------------------------
#define NUM_TRACKED_CLASSES 10
const char* TRACKED_CLASSES[NUM_TRACKED_CLASSES] = {
  "person", "door", "chair", "backpack", "laptop",
  "bottle", "pole", "vehicle", "bicycle", "stairs"
};
unsigned long lastAlertTime[NUM_TRACKED_CLASSES] = {0};
const unsigned long ALERT_COOLDOWN_MS = 3000;

static bool initCamera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size = FRAMESIZE_VGA;   // 640x480, good speed/quality tradeoff
  config.jpeg_quality = 12;
  config.fb_count = 1;

  return esp_camera_init(&config) == ESP_OK;
}

static int classIndex(const String& cls) {
  for (int i = 0; i < NUM_TRACKED_CLASSES; i++) {
    if (cls.equals(TRACKED_CLASSES[i])) return i;
  }
  return -1;
}

static void buzz(int pulses) {
  for (int i = 0; i < pulses; i++) {
    digitalWrite(BUZZER_PIN, HIGH);
    delay(150);
    digitalWrite(BUZZER_PIN, LOW);
    delay(150);
  }
}

void setup() {
  Serial.begin(115200);
  btSerial.begin(9600);
  pinMode(BUZZER_PIN, OUTPUT);

  if (!initCamera()) {
    Serial.println("Camera init failed");
  }

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWi-Fi connected: " + WiFi.localIP().toString());
}

void loop() {
  camera_fb_t* fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("Frame capture failed");
    delay(200);
    return;
  }

  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(DETECTION_ENDPOINT);
    http.addHeader("Content-Type", "image/jpeg");
    int httpCode = http.POST(fb->buf, fb->len);

    if (httpCode == 200) {
      String payload = http.getString();
      StaticJsonDocument<512> doc;
      DeserializationError err = deserializeJson(doc, payload);
      if (!err) {
        const char* cls = doc["object_class"] | "";
        const char* priority = doc["priority"] | "low";
        const char* message = doc["message"] | "";

        int idx = classIndex(String(cls));
        unsigned long now = millis();
        bool onCooldown = (idx >= 0) &&
            (now - lastAlertTime[idx] < ALERT_COOLDOWN_MS);

        if (!onCooldown) {
          int pulses = 1;
          if (strcmp(priority, "high") == 0) pulses = 3;
          else if (strcmp(priority, "medium") == 0) pulses = 2;
          buzz(pulses);

          btSerial.println(message);  // relayed to paired phone for TTS

          if (idx >= 0) lastAlertTime[idx] = now;
        }
      }
    } else {
      Serial.printf("Detection request failed: %d\n", httpCode);
    }
    http.end();
  }

  esp_camera_fb_return(fb);
  delay(300);  // pacing between capture attempts
}
