#include "sensors.h"
#include "config.h"
#include <Arduino.h>
#include <Wire.h>
#include <MPU9250_asukiaaa.h>  // https://github.com/asukiaaa/MPU9250_asukiaaa

static MPU9250_asukiaaa imu;
static unsigned long fallDetectedAt = 0;
static bool fallActive = false;
static uint8_t movingSamples = 0;

struct UltrasonicCalib { float slope; float intercept; };

// Recomputed from the released 80-row U1-U5 calibration record
// (40-300 cm, two observations at each reference distance per sensor).
// The regression is measured = m * true + b; runtime applies the inverse.
static const UltrasonicCalib ULTRASONIC_CALIB[5] = {
  {0.99869704f,  0.51718625f}, // U1
  {1.00029776f, -0.01266986f}, // U2
  {0.99884492f,  0.30787370f}, // U3
  {0.99796163f,  0.40065947f}, // U4
  {0.99962230f,  0.22446043f}  // U5
};

static float applyUltrasonicCalibration(uint8_t sensorId, float rawCm) {
  if (sensorId < 1 || sensorId > 5) return rawCm;
  const UltrasonicCalib &c = ULTRASONIC_CALIB[sensorId - 1];
  return (rawCm - c.intercept) / c.slope;
}

static uint16_t readUltrasonicCm(uint8_t sensorId, int trigPin, int echoPin) {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  // US_ECHO_TIMEOUT_US ~= 3.4 m round trip; treat timeout as "no echo".
  long durationUs = pulseIn(echoPin, HIGH, US_ECHO_TIMEOUT_US);
  if (durationUs == 0) {
    return 0xFFFF;
  }
  float distanceCm = durationUs / 58.0f;  // speed of sound conversion
  distanceCm = applyUltrasonicCalibration(sensorId, distanceCm);
  if (distanceCm < 0.0f || distanceCm > (float) US_MAX_VALID_CM) {
    return 0xFFFF;
  }
  return (uint16_t) lroundf(distanceCm);
}

static uint8_t readBatteryPct() {
  int raw = analogRead(BATTERY_ADC_PIN);
  // Adjust the divider ratio / ADC reference for your specific wiring.
  float mv = raw * (3300.0f / 4095.0f) * 2.0f;  // assumes a 1:1 divider, 3.3V ref
  float pct = (mv - BATTERY_EMPTY_MV) * 100.0f / (BATTERY_FULL_MV - BATTERY_EMPTY_MV);
  if (pct < 0) pct = 0;
  if (pct > 100) pct = 100;
  return (uint8_t) pct;
}

void sensors_init() {
  pinMode(US_FRONT_TRIG_PIN, OUTPUT); pinMode(US_FRONT_ECHO_PIN, INPUT);
  pinMode(US_LEFT_TRIG_PIN, OUTPUT);  pinMode(US_LEFT_ECHO_PIN, INPUT);
  pinMode(US_RIGHT_TRIG_PIN, OUTPUT); pinMode(US_RIGHT_ECHO_PIN, INPUT);
  pinMode(US_REAR_TRIG_PIN, OUTPUT);  pinMode(US_REAR_ECHO_PIN, INPUT);
  pinMode(US_DOWN_TRIG_PIN, OUTPUT);  pinMode(US_DOWN_ECHO_PIN, INPUT);

  pinMode(IR_EDGE_1_PIN, INPUT);
  pinMode(IR_EDGE_2_PIN, INPUT);
  pinMode(WATER_SENSOR_PIN, INPUT);
  pinMode(FSR_PIN, INPUT);
  pinMode(SOS_BUTTON_PIN, INPUT_PULLUP);
  pinMode(BATTERY_ADC_PIN, INPUT);

  Wire.begin(IMU_SDA_PIN, IMU_SCL_PIN);
  imu.setWire(&Wire);
  imu.beginAccel();
  imu.beginGyro();
}

SensorSnapshot sensors_read() {
  SensorSnapshot s{};

  // Transducers are fired strictly sequentially. Each read either returns an
  // echo or blocks for the full US_ECHO_TIMEOUT_US, so consecutive firings
  // are separated by at least one echo window -- that separation, not an
  // added microsecond delay, is what keeps them from hearing each other.
  s.us_front_cm = readUltrasonicCm(1, US_FRONT_TRIG_PIN, US_FRONT_ECHO_PIN);
  s.us_left_cm  = readUltrasonicCm(2, US_LEFT_TRIG_PIN, US_LEFT_ECHO_PIN);
  s.us_right_cm = readUltrasonicCm(3, US_RIGHT_TRIG_PIN, US_RIGHT_ECHO_PIN);
  s.us_rear_cm  = readUltrasonicCm(4, US_REAR_TRIG_PIN, US_REAR_ECHO_PIN);
  s.us_down_cm  = readUltrasonicCm(5, US_DOWN_TRIG_PIN, US_DOWN_ECHO_PIN);

  // A downward transducer that hears nothing is the strongest drop-off
  // signal there is (void below, or a surface that absorbs the ping). Flag
  // it explicitly instead of letting it vanish into the 0xFFFF sentinel.
  s.down_no_return = (s.us_down_cm == 0xFFFF);

  // IR edge sensors. Drop-off = no ground return, so the polarity define
  // decides the sense of this test. ir_edge_cm keeps the legacy distance
  // slot (0 = ground seen at the tip, 0xFFFF = nothing seen).
  int ir1 = digitalRead(IR_EDGE_1_PIN);
  int ir2 = digitalRead(IR_EDGE_2_PIN);
#if IR_LOW_MEANS_GROUND_PRESENT
  bool groundSeen = (ir1 == LOW) || (ir2 == LOW);
#else
  bool groundSeen = (ir1 == HIGH) || (ir2 == HIGH);
#endif
  s.ir_ground_absent = !groundSeen;
  s.ir_edge_cm = groundSeen ? 0 : 0xFFFF;

  int waterRaw = analogRead(WATER_SENSOR_PIN);
  s.water_detected = waterRaw > WATER_ADC_THRESHOLD;

  int fsrRaw = analogRead(FSR_PIN);
  s.fsr_contact = fsrRaw > FSR_CONTACT_ADC_THRESHOLD;

  s.sos_pressed = (digitalRead(SOS_BUTTON_PIN) == LOW);

  imu.accelUpdate();
  imu.gyroUpdate();
  float ax = imu.accelX(), ay = imu.accelY(), az = imu.accelZ();
  float mag = sqrtf(ax * ax + ay * ay + az * az);  // in g, per library convention
  bool spike = mag > FALL_ACCEL_THRESHOLD_G;

  if (spike && !fallActive) {
    fallActive = true;
    fallDetectedAt = millis();
    movingSamples = 0;
  }

  // Recovery must be MOVEMENT, not stillness. A person lying motionless on
  // the ground reads ~1 g, so the previous "mag < 1.3g => recovered" test
  // cleared the flag within a few hundred milliseconds of every fall and
  // made the no-recovery watchdog unreachable. Require several consecutive
  // samples with a real excursion away from 1 g before declaring recovery.
  if (fallActive) {
    if (fabsf(mag - 1.0f) > FALL_MOTION_DEVIATION_G) {
      if (movingSamples < 255) movingSamples++;
    } else {
      movingSamples = 0;
    }
    if (movingSamples >= FALL_MOTION_SAMPLES_TO_CLEAR) {
      fallActive = false;
      movingSamples = 0;
    }
  }
  s.fall_detected = fallActive;

  s.imu_pitch_deg = atan2f(ay, az) * 180.0f / PI;
  s.imu_roll_deg  = atan2f(ax, az) * 180.0f / PI;

  s.battery_pct = readBatteryPct();

  return s;
}

bool sensors_fall_watchdog_expired() {
  if (!fallActive) return false;
  return (millis() - fallDetectedAt) > FALL_NO_RECOVERY_MS;
}

// Calibration coefficients are documented in data/Ultrasonic_Sensor_Calibration_Recomputed.csv.
