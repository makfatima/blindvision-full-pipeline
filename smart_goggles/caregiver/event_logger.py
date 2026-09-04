"""
Privacy-by-design event logging (Section III / FR-SYS-005): raw
images/audio are never stored or transmitted -- only typed metadata (object
type, direction, distance, hazard flags, timestamp, device state, source
sensor, and location where available) is logged locally and relayed to the
configured backend. TLS must be provided by an HTTPS endpoint or external
reverse proxy; this client does not itself enforce TLS 1.2 or authentication.
"""

import json
import logging
import time
import uuid
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger("blindvision.events")

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None


@dataclass
class HazardEvent:
    event_id: str
    event_type: str            # tier name, e.g. "CRITICAL_OBSTACLE"
    severity: str               # "Emergency" | "High-Risk" | "Caution" | "Safe"
    timestamp: float
    device_state: str           # SystemMode value at time of event
    source_sensor: str          # "vision" | "stick" | "fused"
    direction: Optional[str] = None
    distance_m: Optional[float] = None
    object_class: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    def to_dict(self):
        return asdict(self)


class EventLogger:
    def __init__(self, backend_url: str, local_log_path: str = "logs/events.jsonl",
                 tls_min_version: str = "TLSv1.2"):
        self.backend_url = backend_url
        self.local_log_path = Path(local_log_path)
        self.local_log_path.parent.mkdir(parents=True, exist_ok=True)
        self.tls_min_version = tls_min_version

    def log(self, event: HazardEvent):
        # Always persist locally first -- local safety/audit trail must not
        # depend on connectivity.
        with self.local_log_path.open("a") as f:
            f.write(json.dumps(event.to_dict()) + "\n")

        if requests is None:
            logger.warning("requests not installed -- event kept local-only")
            return
        try:
            requests.post(self.backend_url, json=event.to_dict(), timeout=3.0)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Backend event relay failed (kept locally): %s", exc)

    @staticmethod
    def new_event_id() -> str:
        return str(uuid.uuid4())
