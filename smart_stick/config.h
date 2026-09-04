/*
 * Smart Stick configuration (ESP32 DevKit V1, dual-core Xtensa LX6 @ 240MHz)
 *
 * Hardware per Section III:
 *  - 5x HC-SR04 ultrasonic: front, left, right, rear (~90 deg apart) + one
 *    angled downward for near-field ground/drop-off sensing
 *  - 2x IR proximity sensors, aimed downward (edge/stair detection)
 *  - 1x resistive water-level sensor (tip)
 *  - 1x MPU9250 IMU (I2C) -- fall/knock detection
 *  - 1x FSR at the tip -- ground-contact confirmation
 *  - 1x SOS pushbutton
 *  - Outputs: vibration motor, piezo buzzer, LED safety light
 *  - Power: 3.7V 5000mAh 18650 Li-ion + TP4056 charger
 *
 * Adjust the pin numbers below for your own wiring -- these are a
 * reasonable, non-conflicting default assignment for an ESP32 DevKit V1.
 */

#ifndef BLINDVISION_STICK_CONFIG_H
#define BLINDVISION_STICK_CONFIG_H

// ---- Ultrasonic sensors (HC-SR04: trig/echo pairs) ------------------------
#define US_FRONT_TRIG_PIN   5
#define US_FRONT_ECHO_PIN   18
#define US_LEFT_TRIG_PIN    19
#define US_LEFT_ECHO_PIN    21
#define US_RIGHT_TRIG_PIN   22
#define US_RIGHT_ECHO_PIN   39   // was 23: freed for I2C. GPIO39 is input-only,
                                  // which is fine for an echo line.
#define US_REAR_TRIG_PIN    25
#define US_REAR_ECHO_PIN    26
#define US_DOWN_TRIG_PIN    27
#define US_DOWN_ECHO_PIN    14

// ---- IR proximity (downward, edge/stair) ----------------------------------
#define IR_EDGE_1_PIN       32   // analog or digital threshold output
#define IR_EDGE_2_PIN       33

// ---- Water sensor (resistive, tip) -----------------------------------------
#define WATER_SENSOR_PIN    34   // analog input

// ---- FSR (force-sensitive resistor, tip contact) ---------------------------
#define FSR_PIN             35   // analog input

// ---- SOS pushbutton (active LOW with internal pull-up) ---------------------
#define SOS_BUTTON_PIN      13

// ---- IMU (MPU9250, I2C) -----------------------------------------------------
#define IMU_SDA_PIN         4
#define IMU_SCL_PIN         23   // was 2: GPIO2 is a strapping pin AND collided
                                  // with the LED. I2C pull-ups on a strapping
                                  // pin can block boot.
#define IMU_I2C_ADDR        0x68

// ---- Outputs ----------------------------------------------------------------
#define VIBRATION_MOTOR_PIN 15
#define BUZZER_PIN          16   // was 12: GPIO12 is the MTDI strapping pin
#define LED_PIN             17   // was 2: GPIO2 collided with IMU_SCL_PIN

// VIBRATION_MOTOR_PIN sits on GPIO 15 (MTDO), which only selects whether the
// boot log is printed -- a motor driver held low at reset is harmless.
// GPIO 0, 2 and 12 are deliberately left unassigned: all three are ESP32
// strapping pins sampled at reset. GPIO 34-39 are input-only and may be used
// for echo lines and ADC inputs but never for trigger or output lines.

// ---- Battery monitoring (voltage divider into ADC) --------------------------
#define BATTERY_ADC_PIN     36
#define BATTERY_FULL_MV     4200
#define BATTERY_EMPTY_MV    3300

// ===========================================================================
// GROUP A -- values that ARE stated in the manuscript (Table I / Algorithm 1)
// ===========================================================================
#define DROPOFF_DOWN_DISTANCE_CM   50    // > this on the down sensor => drop-off
#define CRITICAL_OBSTACLE_CM       50    // < this on any forward sensor => critical

// ===========================================================================
// GROUP B -- NOT STATED ANYWHERE IN THE MANUSCRIPT. These are engineering
// defaults chosen for this implementation. They are NOT the as-tested values
// and must NOT be cited as such. Each must be replaced by a bench-measured
// value and the procedure recorded before any figure derived from this
// firmware is reported. See PROVENANCE.md.
// ===========================================================================
#define WATER_ADC_THRESHOLD        1500  // TODO(calibrate): sensor + wiring specific
#define FSR_CONTACT_ADC_THRESHOLD  200   // TODO(calibrate): FSR + pull-down specific
#define FALL_ACCEL_THRESHOLD_G     2.5   // TODO(calibrate): no value given in the paper
#define FALL_NO_RECOVERY_MS        10000 // TODO(confirm): paper says "no recovery",
                                          // gives no window length
#define FALL_MOTION_DEVIATION_G    0.30  // |a|-1g excursion that counts as movement
#define FALL_MOTION_SAMPLES_TO_CLEAR 5   // consecutive moving samples => recovered

// ---- Ultrasonic calibration --------------------------------------------------
// Coefficients recomputed from data/raw/Ultrasonic_Calibration_Raw.csv.
// The raw regression is measured = m*true + b; runtime applies (raw-b)/m.
// See data/Ultrasonic_Sensor_Calibration_Recomputed.csv.
// ---- Ultrasonic acquisition -------------------------------------------------
// 20 ms echo timeout ~= 3.4 m round trip, just past the D_smax = 3 m
// normalization ceiling used by the fusion engine. Sequential firing with a
// full timeout between transducers is what actually separates them in time;
// the previous 500 us stagger was ~17 cm of sound travel and did nothing.
#define US_ECHO_TIMEOUT_US         20000
#define US_MAX_VALID_CM            340

// ---- Timing (Section III: Core 0 polls sensors at ~10-20 Hz) ----------------
// Worst case per cycle = 5 transducers x 20 ms timeout = 100 ms, so the loop
// is driven with vTaskDelayUntil at a fixed 100 ms period => 10 Hz, the low
// end of the paper's stated 10-20 Hz range. The previous 75 ms period was
// unreachable whenever any transducer timed out, which is the normal case
// outdoors.
#define SENSOR_POLL_INTERVAL_MS    100
#define BLE_PACKET_INTERVAL_MS     100

// ---- IR edge-sensor polarity -------------------------------------------------
// Set to 1 if your IR module reads LOW when it SEES ground (the common
// reflective-module convention); 0 if it reads HIGH when it sees ground.
// Drop-off is the ABSENCE of a ground return, so this polarity determines
// whether tier 2 fires at all. TODO(confirm against the module datasheet).
#define IR_LOW_MEANS_GROUND_PRESENT 1

// ---- BLE identifiers (must match smart_goggles/config.py) -------------------
#define BLE_DEVICE_NAME       "BlindVision-Stick"
#define BLE_SERVICE_UUID      "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
#define BLE_CHAR_TX_UUID      "6e400003-b5a3-f393-e0a9-e50e24dcca9e"  // notify: sensor packet
#define BLE_CHAR_RX_UUID      "6e400002-b5a3-f393-e0a9-e50e24dcca9e"  // write: ping tokens (remote haptic write not exercised in current release)

#endif  // BLINDVISION_STICK_CONFIG_H
