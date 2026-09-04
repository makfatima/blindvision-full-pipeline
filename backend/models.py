from typing import Optional

from pydantic import BaseModel


class HazardEventIn(BaseModel):
    event_id: str
    event_type: str
    severity: str
    timestamp: float
    device_state: str
    source_sensor: str
    direction: Optional[str] = None
    distance_m: Optional[float] = None
    object_class: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class HazardEventOut(HazardEventIn):
    received_at: float


class Geofence(BaseModel):
    name: str
    center_lat: float
    center_lon: float
    radius_m: float


class DeviceHealth(BaseModel):
    battery_pct: int
    stick_link_ok: bool
    last_seen: float
