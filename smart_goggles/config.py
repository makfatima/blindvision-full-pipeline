"""
Central configuration for the Smart Goggles (Raspberry Pi vision node).

Values in this file fall into two groups, and the distinction matters:

  GROUP A -- stated in the manuscript. Fusion weights, distance
  normalization ceilings, priority-tier thresholds, detector thresholds,
  camera count/FOV/resolution, the stick-disconnect timeout. These are
  transcribed and should not be changed without changing the paper.

  GROUP B -- NOT in the manuscript anywhere. GPIO assignments, BLE UUIDs and
  packet cadence, TTS rate, camera calibration, alert-repeat timing, backend
  endpoints. The paper does not specify them, so nothing here can be sourced
  from it. They are engineering defaults for THIS implementation and must not
  be cited as as-tested values. See PROVENANCE.md for the line-by-line trace.
"""

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Fusion weights (Section IV): R = w_vc*C + w_vp*P + w_sp*U + w_sc*W
# Reported ordering constraint from the paper: w_vc > w_sp > w_vp > w_sc
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class FusionWeights:
    w_vc: float = 0.40   # vision class-confidence weight
    w_vp: float = 0.20   # vision proximity weight
    w_sp: float = 0.25   # stick (ultrasonic) proximity weight
    w_sc: float = 0.15   # stick critical-flag weight

    def validate_ordering(self) -> bool:
        """Paper's calibration protocol fixes the *ordering*, not the exact
        decimal values: w_vc > w_sp > w_vp > w_sc."""
        return self.w_vc > self.w_sp > self.w_vp > self.w_sc


# ---------------------------------------------------------------------------
# Distance normalization ranges (Section IV)
# ---------------------------------------------------------------------------
D_VMAX_M = 8.0   # upper end of tested vision detection range (Section VI.B)
D_SMAX_M = 3.0   # upper end of tested ultrasonic range (Section VI.D)

# ---------------------------------------------------------------------------
# Priority-tier thresholds (Algorithm 1 / Table I)
# ---------------------------------------------------------------------------
DROPOFF_DOWN_DISTANCE_M = 0.5     # downward IR: no ground return within this -> drop-off
CRITICAL_OBSTACLE_M = 0.5         # nearest stick/vision distance below this -> critical
HIGH_RISK_VISION_CLASS_RANGE_M = 2.0  # high-risk visual class within this range -> critical
MEDIUM_BAND_M = 1.2               # < this (and >= critical) -> MEDIUM
LOW_BAND_M = 2.0                  # < this (and >= medium) -> LOW
HIGH_RISK_FUSED_THRESHOLD = 0.60   # post-audit corrected threshold; not used to score the pre-correction navigation trials
LOW_BATTERY_PCT = 20              # stick battery % floor -> LOW_BATTERY tier

HIGH_RISK_VISUAL_CLASSES = {"person", "vehicle", "bicycle"}

# ---------------------------------------------------------------------------
# Timeouts / fallback behavior (Section III)
# ---------------------------------------------------------------------------
STICK_LINK_TIMEOUT_S = 5.0        # no packet for this long -> Vision-Only Mode
FALL_WATCHDOG_NO_RECOVERY_S = 10.0  # IMU fall with no recovery -> forced SOS

# ---------------------------------------------------------------------------
# Alert pacing (GROUP B -- not specified in the manuscript)
# ---------------------------------------------------------------------------
# The fusion loop runs at FUSION_LOOP_HZ. Without pacing it enqueues one
# spoken alert per iteration, so a single stationary obstacle produces ~20
# utterances per second behind a blocking TTS call and the spoken output
# falls progressively further behind reality. The proof-of-concept used a
# 3 s per-class cooldown; these are its full-system equivalents.
FUSION_LOOP_HZ = 20.0
ALERT_MIN_REPEAT_S = 3.0          # same tier not re-announced sooner than this
ALERT_CONFIRM_FRAMES = 2          # consecutive frames a new tier must persist
ALERT_CRITICAL_MIN_REPEAT_S = 1.0  # tighter floor for the Emergency tiers

# Detections carry no timestamp on the wire, so a camera thread that stalls
# would otherwise leave its last detections driving alerts forever. Anything
# older than this is dropped from the fusion input.
DETECTION_TTL_S = 0.5

# Two observations further apart in time than this are not treated as
# evidence about the same object, so a stale stick reading is not associated
# with a fresh detection (or vice versa).
ASSOCIATION_MAX_AGE_S = 0.5

# Camera bearings, and the stick ultrasonic that looks the same way. The
# downward transducer is deliberately absent: it belongs to the drop-off
# tier, not to the fused score.
BEARINGS = ("front", "right", "rear", "left")

# ---------------------------------------------------------------------------
# Camera geometry (Section III)
# 4x USB cameras, 1080p, 120 degree FOV, mounted at ~90 degree intervals
# ---------------------------------------------------------------------------
CAMERA_BEARINGS = ["front", "right", "rear", "left"]  # 90 deg apart
CAMERA_FOV_DEG = 120
CAMERA_RESOLUTION = (1920, 1080)
YOLO_CONFIDENCE_THRESHOLD = 0.45
YOLO_IOU_THRESHOLD = 0.50
YOLO_MODEL_PATH = "models/blindvision_yolov8.pt"  # replace with your trained weights

# Monocular distance estimation (GROUP B -- NOT in the manuscript).
# The paper reports ultrasonic distance accuracy; the latest release also includes
# how vision distance is obtained, nor any accuracy figure for it. Set this
# to a measured focal length in pixels, in the SAME units your calibration
# procedure produces, and record that procedure. While it is None the
# detector reports distance_m = None, the vision proximity term drops out of
# the fused score (documented degraded behaviour), and tier 3's 2.0 m
# high-risk-class clause cannot fire. That is the honest default: a wrong
# distance is worse than an absent one.
CAMERA_FOCAL_LENGTH_PX = None
CAMERA_CALIBRATION_NOTE = "Calibration procedure is not specified in the manuscript."

# ---------------------------------------------------------------------------
# BLE (Section III): stick uses ESP32-WROOM-32 => Bluetooth 4.2
# ---------------------------------------------------------------------------
BLE_STICK_SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"  # Nordic UART-style
BLE_STICK_CHAR_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"          # notify
BLE_STICK_COMMAND_CHAR_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"  # write
BLE_DEVICE_NAME_PREFIX = "BlindVision-Stick"

# ---------------------------------------------------------------------------
# Audio / TTS (Section III): offline-preferred engine
# ---------------------------------------------------------------------------
TTS_ENGINE = "pyttsx3"  # or "coqui"
TTS_RATE_WPM = 175

# ---------------------------------------------------------------------------
# Caregiver / backend (Section III)
# ---------------------------------------------------------------------------
GPS_SERIAL_PORT = "/dev/serial0"
GPS_BAUDRATE = 9600
GSM_SERIAL_PORT = "/dev/ttyUSB0"
GSM_BAUDRATE = 9600
import os

BACKEND_URL = os.getenv("BLINDVISION_BACKEND_URL", "")
BACKEND_TLS_MIN_VERSION = "TLSv1.2"
CAREGIVER_PHONE_NUMBER = os.getenv("BLINDVISION_CAREGIVER_PHONE", "")

# ---------------------------------------------------------------------------
# Alert priority tiers, in evaluation order (highest priority first).
# Mirrors Algorithm 1 exactly.
# ---------------------------------------------------------------------------
class Tier:
    SOS = "SOS"
    CRITICAL_DROPOFF = "CRITICAL_DROPOFF"
    CRITICAL_OBSTACLE = "CRITICAL_OBSTACLE"
    WATER_HAZARD = "WATER_HAZARD"
    FALL_ALERT = "FALL_ALERT"
    HIGH_RISK_FUSED = "HIGH_RISK_FUSED"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    LOW_BATTERY = "LOW_BATTERY"
    ROUTINE = "ROUTINE"


# Surfaced user-facing severity, per the paper's Section III mapping:
#   Critical band (tiers 1-5)      -> "Emergency"
#   Fused-score tier (tier 7)      -> "High-Risk"
#   Medium/Low bands (tiers 8-9)   -> "Caution"
#   Routine/status tiers (10-11)   -> "Safe"
TIER_TO_SEVERITY = {
    Tier.SOS: "Emergency",
    Tier.CRITICAL_DROPOFF: "Emergency",
    Tier.CRITICAL_OBSTACLE: "Emergency",
    Tier.WATER_HAZARD: "Emergency",
    Tier.FALL_ALERT: "Emergency",
    Tier.HIGH_RISK_FUSED: "High-Risk",
    Tier.MEDIUM: "Caution",
    Tier.LOW: "Caution",
    Tier.LOW_BATTERY: "Safe",
    Tier.ROUTINE: "Safe",
}

DEFAULT_WEIGHTS = FusionWeights()
