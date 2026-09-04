/*
 * Sensor acquisition for the Smart Stick. Runs on Core 0 (Section III):
 * "Core 0 of the ESP32 polls sensors at ~10-20 Hz and applies local safety
 * logic; Core 1 manages the BLE stack and state machine."
 */

#ifndef BLINDVISION_STICK_SENSORS_H
#define BLINDVISION_STICK_SENSORS_H

#include <stdint.h>

struct SensorSnapshot {
  uint16_t us_front_cm;   // 0xFFFF = no echo / out of range
  uint16_t us_left_cm;
  uint16_t us_right_cm;
  uint16_t us_rear_cm;
  uint16_t us_down_cm;
  uint16_t ir_edge_cm;
  // Drop-off is signalled by the ABSENCE of a ground return, so "no echo"
  // must be transmitted as its own flag rather than collapsed into the
  // 0xFFFF distance sentinel -- otherwise the strongest drop-off case is
  // discarded downstream as a missing reading.
  bool     down_no_return;
  bool     ir_ground_absent;
  bool     water_detected;
  bool     fall_detected;
  bool     sos_pressed;
  bool     fsr_contact;
  uint8_t  battery_pct;
  float    imu_pitch_deg;
  float    imu_roll_deg;
};

void sensors_init();

// Blocking read of every sensor for one cycle. WORST CASE ~100 ms: five
// ultrasonic transducers fired strictly sequentially, each allowed a full
// US_ECHO_TIMEOUT_US (20 ms) before being declared no-echo. The sequential
// full-timeout spacing is the only cross-talk mitigation present; it is an
// operational choice, NOT a characterized one -- Section VI.K records that
// per-transducer cross-talk was subsequently characterized in the added experimental record; nothing here changes
// that.
SensorSnapshot sensors_read();

// True if the on-stick fall watchdog has seen a fall with no recovery for
// longer than FALL_NO_RECOVERY_MS -- triggers a forced SOS locally, even if
// the goggles are unreachable (Section IV: "a watchdog on the stick forces
// an SOS signal if it detects a fall (via IMU) followed by no recovery").
bool sensors_fall_watchdog_expired();

#endif  // BLINDVISION_STICK_SENSORS_H
