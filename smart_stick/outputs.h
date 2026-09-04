/*
 * Output devices: vibration motor, piezo buzzer, LED safety light
 * (Section III). Haptic patterns are calibrated so increasing pulse rate
 * conveys decreasing distance, and the SOS pattern (three distinct pulses)
 * never overlaps any normal hazard signal (Section IV).
 */

#ifndef BLINDVISION_STICK_OUTPUTS_H
#define BLINDVISION_STICK_OUTPUTS_H

#include <Arduino.h>

void outputs_init();

// Named haptic patterns matching smart_goggles/audio/tts_engine.py's
// _HAPTIC_PATTERN mapping. Non-blocking: call from the main loop; each call
// advances the pattern state machine by one tick.
enum class HapticPattern {
  NONE,
  SOS_THREE_PULSE,
  CONTINUOUS,
  RAPID_PULSE,
  DOUBLE_PULSE,
  SINGLE_PULSE,
  SLOW_PULSE,
  LONG_SLOW_PULSE,
};

void outputs_set_pattern(HapticPattern pattern);
void outputs_tick();  // call every loop iteration; drives the motor/buzzer/LED

// Local (offline) haptic escalation used in Offline Stick Mode (Section III):
// vibrates faster as obstacles get closer, entirely independent of the
// goggles.
void outputs_local_proximity_feedback(uint16_t nearest_distance_cm);

#endif  // BLINDVISION_STICK_OUTPUTS_H
