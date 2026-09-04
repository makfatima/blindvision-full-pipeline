#include "outputs.h"
#include "config.h"

static HapticPattern currentPattern = HapticPattern::NONE;
static unsigned long patternStartedAt = 0;
static bool motorOn = false;

void outputs_init() {
  pinMode(VIBRATION_MOTOR_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(VIBRATION_MOTOR_PIN, LOW);
  digitalWrite(BUZZER_PIN, LOW);
  digitalWrite(LED_PIN, LOW);
}

void outputs_set_pattern(HapticPattern pattern) {
  if (pattern != currentPattern) {
    currentPattern = pattern;
    patternStartedAt = millis();
  }
}

// Simple on/off duty-cycle table per pattern, in milliseconds (on, off).
// SOS uses a distinctive 3-pulse burst with a longer pause so it is never
// mistaken for a normal hazard pattern.
static void pulse(unsigned long onMs, unsigned long offMs) {
  unsigned long t = (millis() - patternStartedAt) % (onMs + offMs);
  bool on = t < onMs;
  digitalWrite(VIBRATION_MOTOR_PIN, on ? HIGH : LOW);
  motorOn = on;
}

void outputs_tick() {
  switch (currentPattern) {
    case HapticPattern::NONE:
      digitalWrite(VIBRATION_MOTOR_PIN, LOW);
      digitalWrite(BUZZER_PIN, LOW);
      digitalWrite(LED_PIN, LOW);
      break;

    case HapticPattern::SOS_THREE_PULSE: {
      // Three short pulses, then a distinctly longer pause.
      unsigned long t = (millis() - patternStartedAt) % 2000;
      bool on = (t < 150) || (t >= 300 && t < 450) || (t >= 600 && t < 750);
      digitalWrite(VIBRATION_MOTOR_PIN, on ? HIGH : LOW);
      digitalWrite(BUZZER_PIN, on ? HIGH : LOW);
      digitalWrite(LED_PIN, on ? HIGH : LOW);
      break;
    }

    case HapticPattern::CONTINUOUS:
      digitalWrite(VIBRATION_MOTOR_PIN, HIGH);
      digitalWrite(BUZZER_PIN, HIGH);
      digitalWrite(LED_PIN, HIGH);
      break;

    case HapticPattern::RAPID_PULSE:
      pulse(100, 100);
      break;

    case HapticPattern::DOUBLE_PULSE: {
      unsigned long t = (millis() - patternStartedAt) % 900;
      bool on = (t < 150) || (t >= 300 && t < 450);
      digitalWrite(VIBRATION_MOTOR_PIN, on ? HIGH : LOW);
      break;
    }

    case HapticPattern::SINGLE_PULSE:
      pulse(150, 350);
      break;

    case HapticPattern::SLOW_PULSE:
      pulse(150, 850);
      break;

    case HapticPattern::LONG_SLOW_PULSE:
      pulse(80, 1920);
      break;
  }
}

void outputs_local_proximity_feedback(uint16_t nearest_distance_cm) {
  // Offline Stick Mode (Section III): "vibrating faster as obstacles get
  // closer." Maps distance to an on/off duty cycle without any dependency
  // on the goggles or BLE link.
  if (nearest_distance_cm == 0xFFFF) {
    outputs_set_pattern(HapticPattern::NONE);
    return;
  }
  if (nearest_distance_cm < CRITICAL_OBSTACLE_CM) {
    outputs_set_pattern(HapticPattern::CONTINUOUS);
  } else if (nearest_distance_cm < 120) {
    outputs_set_pattern(HapticPattern::RAPID_PULSE);
  } else if (nearest_distance_cm < 200) {
    outputs_set_pattern(HapticPattern::SLOW_PULSE);
  } else {
    outputs_set_pattern(HapticPattern::NONE);
  }
}
