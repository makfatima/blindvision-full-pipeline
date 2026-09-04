/*
 * BlindVision Smart Stick firmware (ESP32 DevKit V1)
 *
 * "Core 0 of the ESP32 polls sensors at ~10-20 Hz and applies local safety
 *  logic; Core 1 manages the BLE stack and state machine. The stick
 *  continuously streams a structured sensor packet to the goggles over
 *  BLE." (Section III)
 *
 * This sketch runs the sensor+safety loop on Core 0 (via a FreeRTOS task
 * pinned to core 0) and lets the Arduino main loop (Core 1 on the ESP32
 * Arduino core) drive BLE notification and command handling, matching that
 * split.
 *
 * Local safety logic (works even if the goggles are unreachable --
 * Offline Stick Mode, Section III):
 *   - critical-distance / drop-off / water / SOS haptic escalation, driven
 *     entirely from on-stick sensor readings
 *   - fall watchdog: forces SOS if a fall is detected with no recovery
 *     within FALL_NO_RECOVERY_MS (Section IV)
 */

#include "config.h"
#include "sensors.h"
#include "outputs.h"
#include "ble_peripheral.h"

static SensorSnapshot latestSnapshot;
static portMUX_TYPE snapshotMux = portMUX_INITIALIZER_UNLOCKED;
static uint32_t packetSeq = 0;
static TaskHandle_t sensorTaskHandle = nullptr;

// ---- Core 0 task: sensor polling + local safety logic ---------------------
void sensorTask(void* param) {
  (void) param;
  TickType_t lastWake = xTaskGetTickCount();
  for (;;) {
    SensorSnapshot snapshot = sensors_read();

    portENTER_CRITICAL(&snapshotMux);
    latestSnapshot = snapshot;
    portEXIT_CRITICAL(&snapshotMux);

    // Local (offline-capable) safety logic, mirroring Algorithm 1 tiers
    // 1-5, evaluated top-down, so it degrades gracefully even without the
    // goggles:
    if (snapshot.sos_pressed || sensors_fall_watchdog_expired()) {
      outputs_set_pattern(HapticPattern::SOS_THREE_PULSE);
    } else if (snapshot.down_no_return || snapshot.ir_ground_absent ||
               (snapshot.us_down_cm != 0xFFFF &&
                snapshot.us_down_cm > DROPOFF_DOWN_DISTANCE_CM)) {
      // Three drop-off signatures, all of which mean "no ground where there
      // should be": nothing heard below, no IR ground return, or a measured
      // down-distance past the nominal ground plane. The first two used to
      // be discarded.
      outputs_set_pattern(HapticPattern::CONTINUOUS);
    } else if (snapshot.water_detected) {
      outputs_set_pattern(HapticPattern::RAPID_PULSE);
    } else if (snapshot.fall_detected) {
      outputs_set_pattern(HapticPattern::RAPID_PULSE);
    } else {
      uint16_t nearest = snapshot.us_front_cm;
      nearest = min(nearest, snapshot.us_left_cm);
      nearest = min(nearest, snapshot.us_right_cm);
      nearest = min(nearest, snapshot.us_rear_cm);
      outputs_local_proximity_feedback(nearest);
    }

    // Fixed-rate scheduling: sensors_read() itself can take most of the
    // period when transducers time out, so delay to an absolute wake time
    // rather than adding a fixed sleep on top of a variable read.
    vTaskDelayUntil(&lastWake, pdMS_TO_TICKS(SENSOR_POLL_INTERVAL_MS));
  }
}

// ---- BLE haptic-command callback (goggles -> stick) ------------------------


void setup() {
  Serial.begin(115200);

  sensors_init();
  outputs_init();
  ble_peripheral_init();

  // Pin the sensor/safety task to Core 0, matching Section III's split.
  xTaskCreatePinnedToCore(
      sensorTask, "sensorTask", 4096, nullptr, 1, &sensorTaskHandle, 0);

  Serial.println("BlindVision Smart Stick ready.");
}

void loop() {
  // Core 1 (Arduino main loop context): drive outputs' non-blocking pattern
  // state machine and stream the latest snapshot over BLE.
  outputs_tick();

  if (ble_peripheral_is_connected()) {
    SensorSnapshot snapshot;
    portENTER_CRITICAL(&snapshotMux);
    snapshot = latestSnapshot;
    portEXIT_CRITICAL(&snapshotMux);

    ble_peripheral_send_snapshot(snapshot, packetSeq++);
  }

  delay(BLE_PACKET_INTERVAL_MS);
}
