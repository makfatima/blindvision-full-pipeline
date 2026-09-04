"""
Score-level decision fusion (Section IV).

Inputs are *interpreted* class confidences, proximity estimates, and sensor
flags -- not raw or intermediate sensor features -- so this is score-level
fusion, not feature-level fusion, per the paper's explicit framing.

    R_vision = w_vc * c + w_vp * prox(d_vision, D_vmax)
    R_stick  = w_sp * prox(d_stick, D_smax) + w_sc * flag(d_stick ≤ 0.5m)
    R        = w_vc*C + w_vp*P + w_sp*U + w_sc*W
             = 0.40*C + 0.20*P + 0.25*U + 0.15*W   (tuned weights)
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

from config import FusionWeights, D_VMAX_M, D_SMAX_M, CRITICAL_OBSTACLE_M


def prox(d: Optional[float], d_max: float) -> float:
    """Linear proximity-normalization function shared by both subsystems.

    prox(d, D_max) = clip(1 - d/D_max, 0, 1)

    A missing/None reading contributes 0 risk from this term (dropped, not
    substituted with an assumed value -- Section IV, Vision-Only/Offline-Stick
    fallback description).
    """
    if d is None:
        return 0.0
    if d_max <= 0:
        raise ValueError("d_max must be positive")
    return max(0.0, min(1.0, 1.0 - (d / d_max)))


@dataclass
class VisionDetection:
    """A single YOLOv8 detection, already reduced to the interpreted
    quantities the fusion engine consumes (class, confidence, bearing,
    approximate distance) -- never raw pixels."""
    obj_class: str
    confidence: float          # c, in [0, 1]
    bearing: str                # "front" | "left" | "right" | "rear"
    distance_m: Optional[float] = None  # nearest reported distance for this class
    # Latency event for the frame this detection came from, when
    # instrumentation is enabled. Lets the alert that this detection wins be
    # stamped against its own capture instant rather than a loop tick.
    timing: Optional[object] = None


@dataclass
class StickReading:
    """One fused snapshot of the Smart Stick's sensor packet."""
    nearest_ultrasonic_m: Optional[float]
    down_distance_m: Optional[float]     # downward IR/ultrasonic reading
    # Drop-off STATE, not distance. A void below produces no echo at all, so
    # it cannot be represented as a large down_distance_m -- it arrives as
    # this flag. Tier 2 keys off this.
    drop_off_detected: bool = False
    water_detected: bool = False
    fall_detected: bool = False
    sos_pressed: bool = False
    battery_pct: Optional[int] = None

    # Per-direction ultrasonic distances, keyed by the same bearing names the
    # cameras use. Without this the fused score pairs the nearest vision
    # detection with the nearest stick reading regardless of where either one
    # is -- a chair on the left and a kerb on the right reinforce each other
    # into a hazard that exists in neither direction.
    distances_by_bearing: Optional[Dict[str, Optional[float]]] = None

    # Age of this reading, seconds, at the moment fusion runs. Used to refuse
    # association with observations too far apart in time to describe the
    # same object.
    age_s: float = 0.0


def vision_risk(detection: Optional[VisionDetection], weights: FusionWeights,
                 d_vmax: float = D_VMAX_M) -> float:
    """R_vision = w_vc*c + w_vp*prox(d_vision, D_vmax)."""
    if detection is None:
        return 0.0
    c = max(0.0, min(1.0, detection.confidence))
    p = prox(detection.distance_m, d_vmax)
    return weights.w_vc * c + weights.w_vp * p


def stick_risk(reading: Optional[StickReading], weights: FusionWeights,
                d_smax: float = D_SMAX_M) -> float:
    """R_stick = w_sp*prox(d_stick, D_smax) + w_sc*flag(d_stick ≤ 0.5m)."""
    if reading is None:
        return 0.0
    d_stick = reading.nearest_ultrasonic_m
    p = prox(d_stick, d_smax)
    flag = 1.0 if (d_stick is not None and d_stick <= CRITICAL_OBSTACLE_M) else 0.0
    return weights.w_sp * p + weights.w_sc * flag


def fused_risk(detection: Optional[VisionDetection],
                reading: Optional[StickReading],
                weights: FusionWeights,
                d_vmax: float = D_VMAX_M,
                d_smax: float = D_SMAX_M) -> float:
    """
    R = w_vc*C + w_vp*P + w_sp*U + w_sc*W

    Implemented as vision_risk + stick_risk so that a missing modality's
    terms drop out of the sum rather than being substituted with an assumed
    value (Section IV, Degraded Mode description).
    """
    return vision_risk(detection, weights, d_vmax) + stick_risk(reading, weights, d_smax)


def _nearest_detection(detections: List[VisionDetection]) -> Optional[VisionDetection]:
    """Nearest detection by estimated distance. Detections with no distance
    (the uncalibrated-camera case) sort last rather than being treated as
    zero-distance."""
    if not detections:
        return None
    with_distance = [d for d in detections if d.distance_m is not None]
    if with_distance:
        return min(with_distance, key=lambda d: d.distance_m)
    return max(detections, key=lambda d: d.confidence)


def fused_risk_by_bearing(detections: List[VisionDetection],
                          stick: Optional[StickReading],
                          weights: FusionWeights,
                          mode: str = "normal",
                          max_association_age_s: float = None):
    """Fused risk computed per direction, then maximised over directions.

    The paper's eq. (1) is written for one obstacle. Applying it to the
    global minima -- nearest detection anywhere, nearest ultrasonic anywhere
    -- silently fuses observations of different objects: a chair seen on the
    left and a kerb felt on the right reinforce each other into a score
    neither direction earns. Matching by bearing first is what makes the
    equation mean what it says.

    Association rules:
      * a vision detection is paired with the stick reading from the SAME
        bearing, or with nothing;
      * an unpaired detection keeps its own terms and drops U (the paper's
        documented missing-term behaviour), it does not borrow another
        direction's reading;
      * a stick reading older than `max_association_age_s` is not associated
        with anything, because two observations far enough apart in time are
        not evidence about the same object;
      * the "down" reading is never associated with a camera bearing -- it
        belongs to tier 2, not to the fused score.

    Returns (best_score, best_bearing). With no per-bearing data available
    this falls back to the global behaviour, so a stick that does not report
    per-direction distances behaves exactly as before.
    """
    import config

    if max_association_age_s is None:
        max_association_age_s = getattr(config, "ASSOCIATION_MAX_AGE_S", 0.5)

    usable_stick = stick
    if stick is not None and stick.age_s > max_association_age_s:
        usable_stick = None

    by_bearing = None
    if usable_stick is not None:
        by_bearing = usable_stick.distances_by_bearing

    nearest_vision = _nearest_detection(detections)

    if not by_bearing:
        # No directional data: keep the previous global behaviour rather than
        # inventing an association.
        stick_for_global = None if mode == "vision_only" else usable_stick
        return fused_risk(nearest_vision, stick_for_global, weights), None

    best_score = 0.0
    best_bearing = None

    bearings = set(by_bearing) | {d.bearing for d in detections}
    for bearing in bearings:
        local_detection = _nearest_detection(
            [d for d in detections if d.bearing == bearing])
        if mode == "vision_only":
            local_stick = None
        else:
            local_stick = StickReading(
                nearest_ultrasonic_m=by_bearing.get(bearing),
                down_distance_m=None,
                drop_off_detected=False,
                water_detected=usable_stick.water_detected,
                fall_detected=usable_stick.fall_detected,
                sos_pressed=usable_stick.sos_pressed,
                battery_pct=usable_stick.battery_pct,
            )
        score = fused_risk(local_detection, local_stick, weights)
        if score > best_score:
            best_score = score
            best_bearing = bearing

    return best_score, best_bearing
