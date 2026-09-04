"""
Algorithm 1. Priority-tier alert arbitration (evaluated top-down; the first
matching tier wins). Transcribed directly from Section IV:

 1: if stick.sos_pressed then return SOS
 2: if drop-off signature then return CRITICAL_DROPOFF
       (down_distance > 0.5 m, OR no downward echo at all, OR no IR ground
        return -- the latter two are the void case and were previously lost)
 3: if nearest_stick_distance < 0.5 m or
       (vision_class in HIGH_RISK and nearest_vision_distance <= 2.0 m)
       then return CRITICAL_OBSTACLE
 4: if stick.water_detected then return WATER_HAZARD
 5: if stick.fall_detected then return FALL_ALERT
 6: R <- 0.40*C + 0.20*P + 0.25*U + 0.15*W
 7: if R >= 0.60 then return HIGH_RISK_FUSED
 8: if min(nearest_stick_distance, nearest_vision_distance) < 1.2 m then return MEDIUM
 9: if min(nearest_stick_distance, nearest_vision_distance) < 2.0 m then return LOW
10: if stick.battery_pct < 20% then return LOW_BATTERY
11: return ROUTINE

Runs in O(n) per fusion cycle (n = currently detected vision objects) to
build the candidate risk terms, then O(1) tier evaluation, per the paper's
complexity analysis. No history buffer is retained (O(1) memory).
"""

from dataclasses import dataclass
from typing import Optional, List

from config import (
    Tier, TIER_TO_SEVERITY, FusionWeights, DEFAULT_WEIGHTS,
    HIGH_RISK_VISUAL_CLASSES, CRITICAL_OBSTACLE_M, HIGH_RISK_VISION_CLASS_RANGE_M,
    DROPOFF_DOWN_DISTANCE_M, MEDIUM_BAND_M, LOW_BAND_M,
    HIGH_RISK_FUSED_THRESHOLD, LOW_BATTERY_PCT, D_VMAX_M, D_SMAX_M,
)
from .risk_model import (VisionDetection, StickReading, fused_risk,
                          fused_risk_by_bearing)


@dataclass
class Alert:
    tier: str
    severity: str
    risk_score: Optional[float] = None
    message: Optional[str] = None
    # Latency event this alert belongs to, when instrumentation is enabled.
    # Carried so the dispatcher can stamp speech onset and completion
    # against the same event the camera or BLE stage started.
    timing: Optional[object] = None


def _nearest(detections: List[VisionDetection]) -> Optional[VisionDetection]:
    candidates = [d for d in detections if d.distance_m is not None]
    if not candidates:
        return None
    return min(candidates, key=lambda d: d.distance_m)


def arbitrate(detections: List[VisionDetection],
              stick: Optional[StickReading],
              weights: FusionWeights = DEFAULT_WEIGHTS,
              mode: str = "normal") -> Alert:
    """
    mode: "normal" | "vision_only" | "offline_stick" | "degraded"

    - "normal": full ladder, both modalities available.
    - "vision_only": stick disconnected >5s (Section III). Tiers 2, 4, 5, 10
      become unavailable; tier 3 retains only its high-risk-visual-class
      clause; U and W terms drop from line 6; tiers 8-9 use vision distance
      alone.
    - "offline_stick": goggles powered off / unreachable. Only tiers 1-5 are
      evaluated, using the stick's own local thresholds; caller should
      instead run this logic on-device on the ESP32 (see smart_stick
      firmware) -- this branch is provided for test parity.
    - "degraded": an individual sensor is out of calibration; its term is
      dropped from the weighted sum rather than substituted with an assumed
      value. Caller achieves this simply by passing None for the affected
      reading/detection field.
    """
    nearest_vision = _nearest(detections)
    nearest_vision_d = nearest_vision.distance_m if nearest_vision else None
    nearest_stick_d = stick.nearest_ultrasonic_m if stick else None

    # Tier 1: SOS
    if stick and stick.sos_pressed:
        return Alert(Tier.SOS, TIER_TO_SEVERITY[Tier.SOS],
                     message="SOS pressed -- caregiver notified with location.")

    if mode != "vision_only":
        # Tier 2: critical drop-off
        _measured_dropoff = (stick is not None
                             and stick.down_distance_m is not None
                             and stick.down_distance_m > DROPOFF_DOWN_DISTANCE_M)
        if stick and (stick.drop_off_detected or _measured_dropoff):
            return Alert(Tier.CRITICAL_DROPOFF, TIER_TO_SEVERITY[Tier.CRITICAL_DROPOFF],
                         message="Drop-off detected ahead -- stop.")

    # Tier 3: critical obstacle
    high_risk_vision_hit = (
        nearest_vision is not None
        and nearest_vision.obj_class in HIGH_RISK_VISUAL_CLASSES
        and nearest_vision_d is not None
        and nearest_vision_d <= HIGH_RISK_VISION_CLASS_RANGE_M
    )
    stick_critical_hit = (
        mode != "vision_only"
        and nearest_stick_d is not None
        and nearest_stick_d < CRITICAL_OBSTACLE_M
    )
    if stick_critical_hit or high_risk_vision_hit:
        return Alert(Tier.CRITICAL_OBSTACLE, TIER_TO_SEVERITY[Tier.CRITICAL_OBSTACLE],
                     message=_describe_critical(nearest_vision, nearest_stick_d))

    if mode != "vision_only":
        # Tier 4: water hazard
        if stick and stick.water_detected:
            return Alert(Tier.WATER_HAZARD, TIER_TO_SEVERITY[Tier.WATER_HAZARD],
                         message="Water hazard detected underfoot.")
        # Tier 5: fall alert
        if stick and stick.fall_detected:
            return Alert(Tier.FALL_ALERT, TIER_TO_SEVERITY[Tier.FALL_ALERT],
                         message="Fall detected -- checking for recovery.")

    # Tier 6/7: fused score.
    #
    # Computed per direction and maximised over directions. Fusing the
    # nearest detection anywhere with the nearest ultrasonic reading anywhere
    # combines observations of different objects: a chair on the left and a
    # kerb on the right would reinforce each other into a score neither
    # direction earns. With no per-bearing data on the reading this reduces
    # exactly to the previous global behaviour.
    r, r_bearing = fused_risk_by_bearing(detections, stick, weights, mode=mode)

    if r >= HIGH_RISK_FUSED_THRESHOLD:
        where = f" to the {r_bearing}" if r_bearing else ""
        return Alert(Tier.HIGH_RISK_FUSED, TIER_TO_SEVERITY[Tier.HIGH_RISK_FUSED],
                     risk_score=r,
                     message=f"High-risk fused event{where} -- stop.")

    # Tiers 8/9: medium / low, using min(stick, vision) unless vision-only
    if mode == "vision_only":
        nearest = nearest_vision_d
    else:
        candidates = [d for d in (nearest_stick_d, nearest_vision_d) if d is not None]
        nearest = min(candidates) if candidates else None

    if nearest is not None and nearest < MEDIUM_BAND_M:
        return Alert(Tier.MEDIUM, TIER_TO_SEVERITY[Tier.MEDIUM], risk_score=r,
                     message="Obstacle ahead -- caution.")
    if nearest is not None and nearest < LOW_BAND_M:
        return Alert(Tier.LOW, TIER_TO_SEVERITY[Tier.LOW], risk_score=r,
                     message="Obstacle nearby -- caution.")

    # Tier 10: low battery (unavailable in vision-only mode -- stick offline)
    if mode != "vision_only" and stick and stick.battery_pct is not None \
            and stick.battery_pct < LOW_BATTERY_PCT:
        return Alert(Tier.LOW_BATTERY, TIER_TO_SEVERITY[Tier.LOW_BATTERY],
                     message="Stick battery low -- please recharge soon.")

    # Tier 11: routine
    return Alert(Tier.ROUTINE, TIER_TO_SEVERITY[Tier.ROUTINE], risk_score=r)


def _describe_critical(nearest_vision: Optional[VisionDetection],
                        nearest_stick_d: Optional[float]) -> str:
    if nearest_stick_d is not None and nearest_stick_d < CRITICAL_OBSTACLE_M:
        return f"Critical obstacle {nearest_stick_d:.1f} m ahead -- stop."
    if nearest_vision is not None:
        return (f"{nearest_vision.obj_class.capitalize()} {nearest_vision.bearing} "
                f"{nearest_vision.distance_m:.1f} m -- closing fast, stop.")
    return "Critical obstacle detected -- stop."
