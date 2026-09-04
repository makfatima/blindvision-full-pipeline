"""
Backend/Caregiver Layer (Section III).

"The backend stores anonymized geotagged events and exposes event, geofence, and device-health APIs. A compatible caregiver client may consume these APIs; no smartphone application is included in this release. Local execution uses plain HTTP; HTTPS/TLS requires external termination.

This service accepts anonymized HazardEvent payloads from the Smart
Goggles (smart_goggles/caregiver/event_logger.py), stores them in memory,
evaluates geofence conditions, and exposes a simple API intended for a
compatible caregiver client. No smartphone application, Bearer-token
authentication, or TLS termination is included in this release.

Deploy behind TLS 1.2+ termination (e.g. nginx/Caddy) -- this app itself
speaks plain HTTP for local development.
"""

import time
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from models import HazardEventIn, HazardEventOut, Geofence, DeviceHealth

app = FastAPI(title="BlindVision Caregiver Backend")

# In-memory stores for the current implementation; replace with a persistent database for production.
_events: List[HazardEventOut] = []
_geofences: List[Geofence] = []
_device_health = DeviceHealth(battery_pct=100, stick_link_ok=True, last_seen=time.time())


def _haversine_m(lat1, lon1, lat2, lon2) -> float:
    from math import radians, sin, cos, sqrt, atan2
    r = 6371000.0
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlambda = radians(lon2 - lon1)
    a = sin(dphi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(dlambda / 2) ** 2
    return 2 * r * atan2(sqrt(a), sqrt(1 - a))


@app.post("/api/v1/events", response_model=HazardEventOut)
async def ingest_event(event: HazardEventIn):
    out = HazardEventOut(**event.dict(), received_at=time.time())
    _events.append(out)

    if event.severity == "Emergency" and event.latitude is not None:
        for fence in _geofences:
            distance = _haversine_m(event.latitude, event.longitude,
                                     fence.center_lat, fence.center_lon)
            if distance > fence.radius_m:
                # Integration point for an SMS/push notification to the
                # caregiver's phone would be triggered.
                pass

    return out


@app.get("/api/v1/events", response_model=List[HazardEventOut])
async def list_events(limit: int = 50, severity: Optional[str] = None):
    items = _events
    if severity:
        items = [e for e in items if e.severity == severity]
    return list(reversed(items))[:limit]


@app.post("/api/v1/geofences", response_model=Geofence)
async def create_geofence(fence: Geofence):
    _geofences.append(fence)
    return fence


@app.get("/api/v1/geofences", response_model=List[Geofence])
async def list_geofences():
    return _geofences


@app.get("/api/v1/device-health", response_model=DeviceHealth)
async def get_device_health():
    return _device_health


@app.post("/api/v1/device-health", response_model=DeviceHealth)
async def update_device_health(health: DeviceHealth):
    global _device_health
    _device_health = health
    return _device_health


@app.get("/health")
async def health():
    return {"status": "ok"}
