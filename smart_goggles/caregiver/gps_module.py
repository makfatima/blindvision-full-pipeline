"""
u-blox NEO-6M GPS module, benchmarked outdoors in Section VI.C: 32.4 s
cold-start fix, 4.1 s warm-start fix, +-2.5 m open-sky accuracy, 1 Hz
configured update rate. Reads NMEA sentences over the Pi's serial UART and
underpins the caregiver app's geofencing layer (Section III).
"""

import logging
import time
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger("blindvision.gps")

try:
    import serial
    import pynmea2
except ImportError:  # pragma: no cover
    serial = None
    pynmea2 = None


@dataclass
class GpsFix:
    latitude: float
    longitude: float
    fix_quality: int
    num_satellites: int
    timestamp: float


class GpsModule:
    def __init__(self, port: str = "/dev/serial0", baudrate: int = 9600):
        self.port = port
        self.baudrate = baudrate
        self._serial = None

    def open(self):
        if serial is None:
            raise RuntimeError("pyserial and pynmea2 are required: "
                                "pip install pyserial pynmea2")
        self._serial = serial.Serial(self.port, self.baudrate, timeout=1.0)
        logger.info("GPS serial opened on %s @ %d baud", self.port, self.baudrate)

    def read_fix(self, timeout_s: float = 2.0) -> Optional[GpsFix]:
        if self._serial is None:
            self.open()
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            try:
                line = self._serial.readline().decode("ascii", errors="ignore").strip()
            except Exception as exc:  # noqa: BLE001
                logger.warning("GPS read error: %s", exc)
                continue
            if not line.startswith("$GPGGA") and not line.startswith("$GNGGA"):
                continue
            try:
                msg = pynmea2.parse(line)
            except pynmea2.ParseError:
                continue
            if msg.gps_qual and msg.gps_qual > 0:
                return GpsFix(
                    latitude=msg.latitude,
                    longitude=msg.longitude,
                    fix_quality=int(msg.gps_qual),
                    num_satellites=int(msg.num_sats or 0),
                    timestamp=time.time(),
                )
        return None

    def close(self):
        if self._serial:
            self._serial.close()


def haversine_m(lat1, lon1, lat2, lon2) -> float:
    """Great-circle distance in meters, used for geofence-radius checks."""
    from math import radians, sin, cos, sqrt, atan2
    r = 6371000.0
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlambda = radians(lon2 - lon1)
    a = sin(dphi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(dlambda / 2) ** 2
    return 2 * r * atan2(sqrt(a), sqrt(1 - a))


def is_within_geofence(fix: GpsFix, center_lat: float, center_lon: float,
                        radius_m: float) -> bool:
    return haversine_m(fix.latitude, fix.longitude, center_lat, center_lon) <= radius_m
