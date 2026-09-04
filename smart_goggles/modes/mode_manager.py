"""
Operation modes (Section III):

- Normal: both goggles and stick data fuse to compute a risk score.
- Offline Stick Mode: BLE link lost or goggles battery depleted -- the stick
  continues to protect the user through its own local haptics, independent
  of the goggles (implemented on-device on the ESP32; see smart_stick/).
- Vision-Only Mode: stick disconnects or fails -- goggles continue
  announcing obstacles from the cameras alone.
- Degraded Mode: an individual sensor goes out of calibration -- the system
  continues operating using the remaining sensors (that sensor's term is
  simply omitted from the fused score, not substituted with an assumed
  value).

The fallback routines are implemented here and in the stick firmware.
Targeted fault-injection/component tests can exercise the transitions; the
general 20-session navigation records do not establish that every mode
occurred naturally during those sessions.
"""

import logging
from enum import Enum

logger = logging.getLogger("blindvision.mode")


class SystemMode(str, Enum):
    NORMAL = "normal"
    VISION_ONLY = "vision_only"
    OFFLINE_STICK = "offline_stick"   # goggles-side awareness only; stick self-manages
    DEGRADED = "degraded"


class ModeManager:
    def __init__(self, stick_link_timeout_s: float = 5.0):
        self.stick_link_timeout_s = stick_link_timeout_s
        self._mode = SystemMode.NORMAL
        self._degraded_sensors: set = set()

    @property
    def mode(self) -> SystemMode:
        return self._mode

    def update(self, stick_link_is_stale: bool, goggles_battery_ok: bool = True) -> SystemMode:
        previous = self._mode
        if not goggles_battery_ok:
            self._mode = SystemMode.OFFLINE_STICK
        elif stick_link_is_stale:
            self._mode = SystemMode.VISION_ONLY
        elif self._degraded_sensors:
            self._mode = SystemMode.DEGRADED
        else:
            self._mode = SystemMode.NORMAL

        if self._mode != previous:
            logger.info("Mode transition: %s -> %s", previous.value, self._mode.value)
        return self._mode

    def mark_sensor_degraded(self, sensor_name: str):
        self._degraded_sensors.add(sensor_name)
        logger.warning("Sensor '%s' marked degraded -- its term is dropped, "
                        "not substituted, from the fused score.", sensor_name)

    def clear_sensor_degraded(self, sensor_name: str):
        self._degraded_sensors.discard(sensor_name)

    def arbitration_mode_str(self) -> str:
        """Maps SystemMode -> the `mode` string consumed by
        fusion.arbitration.arbitrate()."""
        if self._mode in (SystemMode.VISION_ONLY,):
            return "vision_only"
        if self._mode in (SystemMode.DEGRADED,):
            return "degraded"
        return "normal"
