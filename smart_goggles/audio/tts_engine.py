"""
Delivers alerts via the Bluetooth earbud using an offline-preferred TTS
engine (pyttsx3 or Coqui TTS) to minimize cloud dependence (Section III),
with a backup speaker/buzzer path, and drives the stick's vibration motor
for haptic feedback via a command sent back over the same BLE link.

Alerts are kept unambiguous: the SOS pattern (three distinct pulses) never
overlaps with any normal hazard signal (Section IV).
"""

import logging
import queue
import threading
from typing import Optional

from fusion.arbitration import Alert
from config import Tier

logger = logging.getLogger("blindvision.audio")

try:
    import pyttsx3
except ImportError:  # pragma: no cover
    pyttsx3 = None


# Haptic pattern names sent to the stick's vibration motor over BLE.
# The stick firmware maps these to pulse counts/intensities (see
# smart_stick/outputs.cpp). SOS uses a distinct three-pulse pattern that
# never overlaps a normal hazard signal.
_HAPTIC_PATTERN = {
    Tier.SOS: "sos_three_pulse",
    Tier.CRITICAL_DROPOFF: "continuous",
    Tier.CRITICAL_OBSTACLE: "continuous",
    Tier.WATER_HAZARD: "rapid_pulse",
    Tier.FALL_ALERT: "rapid_pulse",
    Tier.HIGH_RISK_FUSED: "double_pulse",
    Tier.MEDIUM: "single_pulse",
    Tier.LOW: "slow_pulse",
    Tier.LOW_BATTERY: "long_slow_pulse",
    Tier.ROUTINE: None,
}


class AlertDispatcher:
    """Serializes spoken alerts (one at a time, SOS pre-empts the queue) and
    forwards a haptic-pattern command for the stick's vibration motor."""

    def __init__(self, rate_wpm: int = 175,
                 haptic_send: Optional[callable] = None,
                 on_speech_onset: Optional[callable] = None,
                 on_speech_end: Optional[callable] = None):
        self.engine = pyttsx3.init() if pyttsx3 else None
        if self.engine:
            self.engine.setProperty("rate", rate_wpm)
        self._queue: "queue.Queue[Alert]" = queue.Queue()
        self._haptic_send = haptic_send  # callable(pattern: str) -> None
        # Onset and completion are reported separately: the user has not
        # actually been warned until the phrase carrying the direction has
        # finished, and the gap between the two is the whole utterance.
        self._on_speech_onset = on_speech_onset
        self._on_speech_end = on_speech_end
        self._worker = threading.Thread(target=self._run, daemon=True)
        self._worker.start()

    @property
    def queue_depth(self) -> int:
        """Utterances waiting behind the current one. Non-zero here means
        spoken output is already behind the world."""
        return self._queue.qsize()

    def dispatch(self, alert: Alert):
        if alert.tier == Tier.SOS:
            # SOS pre-empts: clear anything queued and speak immediately.
            with self._queue.mutex:
                self._queue.queue.clear()
        self._queue.put(alert)

    def _run(self):
        while True:
            alert = self._queue.get()
            self._speak(alert)
            self._haptic(alert)

    def _speak(self, alert: Alert):
        text = alert.message or f"{alert.severity}: {alert.tier}"
        logger.info("ALERT[%s/%s] %s", alert.tier, alert.severity, text)
        if self._on_speech_onset:
            self._on_speech_onset(alert)
        if self.engine:
            self.engine.say(text)
            self.engine.runAndWait()
        if self._on_speech_end:
            self._on_speech_end(alert)

    def _haptic(self, alert: Alert):
        pattern = _HAPTIC_PATTERN.get(alert.tier)
        if pattern and self._haptic_send:
            self._haptic_send(pattern)
