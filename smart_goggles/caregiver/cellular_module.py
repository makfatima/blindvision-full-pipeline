"""
SIM800L GSM/GPRS module (Section III) -- the prototype-grade cellular
hardware confirmed in the as-tested unit, with phone/Wi-Fi relay available
as an alternate data path. The paper's Future Work section flags this as
prototype-grade and recommends validating a 4G LTE module (e.g. SIM7600)
for field deployment; this wrapper's AT-command interface should transfer
directly to that migration.

Used for: (a) SMS-based SOS notification to the caregiver as a fallback
when data connectivity to the backend is unavailable, and (b) posting
anonymized event metadata over GPRS when Wi-Fi is not available.
"""

import logging
import time
from typing import Optional

logger = logging.getLogger("blindvision.cellular")

try:
    import serial
except ImportError:  # pragma: no cover
    serial = None


class CellularModule:
    def __init__(self, port: str = "/dev/ttyUSB0", baudrate: int = 9600):
        self.port = port
        self.baudrate = baudrate
        self._serial = None

    def open(self):
        if serial is None:
            raise RuntimeError("pyserial is required: pip install pyserial")
        self._serial = serial.Serial(self.port, self.baudrate, timeout=2.0)
        self._at("AT")  # handshake
        logger.info("SIM800L link established on %s", self.port)

    def _at(self, command: str, wait_s: float = 1.0) -> str:
        if self._serial is None:
            self.open()
        self._serial.write((command + "\r\n").encode())
        time.sleep(wait_s)
        return self._serial.read(self._serial.in_waiting or 1).decode(errors="ignore")

    def send_sos_sms(self, phone_number: str, lat: Optional[float], lon: Optional[float]) -> bool:
        """Fallback SOS notification path -- used when the primary
        TLS-backed backend event (event_logger.EventLogger) cannot be
        delivered over Wi-Fi/GPRS in time."""
        try:
            self._at('AT+CMGF=1')  # text mode
            self._at(f'AT+CMGS="{phone_number}"', wait_s=0.5)
            if lat is not None and lon is not None:
                body = f"BlindVision SOS: user pressed SOS. Location: {lat:.6f},{lon:.6f}"
            else:
                body = "BlindVision SOS: user pressed SOS. Location unavailable."
            self._serial.write(body.encode() + b"\x1a")  # Ctrl+Z sends the SMS
            time.sleep(3.0)
            logger.info("SOS SMS dispatched to %s", phone_number)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("SOS SMS failed: %s", exc)
            return False

    def close(self):
        if self._serial:
            self._serial.close()
