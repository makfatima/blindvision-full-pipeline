"""
Regression tests for the defects found in the first pass over this tree.

Each test names the failure mode it locks down, so a future edit that
reintroduces one fails loudly rather than silently.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "smart_goggles"))

import struct

import config
from fusion.risk_model import VisionDetection, StickReading
from fusion.arbitration import arbitrate
from ble.stick_link import StickPacket, parse_packet, StickLink, _PACKET_FORMAT


def _packet_bytes(seq=0, us=(0xFFFF,) * 5, ir=0xFFFF, down_nr=0, ir_absent=0,
                  water=0, fall=0, sos=0, fsr=0, batt=100, pitch=0, roll=0,
                  echo=0):
    return struct.pack(_PACKET_FORMAT, seq, *us, ir, down_nr, ir_absent,
                       water, fall, sos, fsr, batt, pitch, roll, echo)


# --- drop-off: the no-echo case must not be discarded ----------------------

def test_no_downward_echo_is_a_drop_off():
    """A void below returns no echo at all. That used to parse to None and
    fail the '> 0.5 m' test, so the strongest drop-off produced no alert."""
    pkt = parse_packet(_packet_bytes(down_nr=1))
    assert pkt.us_down_m is None
    assert pkt.drop_off_detected is True

    reading = StickReading(nearest_ultrasonic_m=2.0, down_distance_m=None,
                           drop_off_detected=True)
    assert arbitrate([], reading).tier == config.Tier.CRITICAL_DROPOFF


def test_absent_ir_ground_return_is_a_drop_off():
    pkt = parse_packet(_packet_bytes(ir_absent=1))
    assert pkt.drop_off_detected is True


def test_measured_dropoff_still_fires():
    reading = StickReading(nearest_ultrasonic_m=2.0, down_distance_m=0.6)
    assert arbitrate([], reading).tier == config.Tier.CRITICAL_DROPOFF


def test_normal_ground_is_not_a_drop_off():
    pkt = parse_packet(_packet_bytes(us=(0xFFFF, 0xFFFF, 0xFFFF, 0xFFFF, 30)))
    assert pkt.drop_off_detected is False


# --- packet layout ----------------------------------------------------------

def test_packet_size_matches_firmware_struct():
    """The Python format and the packed C struct must agree byte for byte;
    the docstring previously claimed 24 for a 25-byte layout."""
    assert struct.calcsize(_PACKET_FORMAT) == 31


def test_malformed_packet_is_rejected():
    try:
        parse_packet(b"\x00" * 10)
    except ValueError:
        return
    raise AssertionError("short packet should have been rejected")


# --- link reliability accounting -------------------------------------------

def test_sequence_gaps_are_counted_as_loss():
    """`seq` was transmitted and never read, so no delivery figure could be
    derived from a run at all."""
    link = StickLink("svc", "chr")
    for seq in (0, 1, 2, 5, 6):      # 3 and 4 lost
        link._account(seq)
    assert link.packets_received == 5
    assert link.packets_expected == 7
    assert link.packets_lost == 2
    assert abs(link.delivery_rate - 5 / 7) < 1e-9


def test_duplicate_sequence_is_not_double_counted():
    link = StickLink("svc", "chr")
    link._account(1)
    link._account(1)
    assert link.packets_received == 1


# --- vision distance is gated on calibration --------------------------------

def test_distance_is_none_while_uncalibrated():
    """An absent distance degrades the system in a documented way; a guessed
    one silently mis-ranks hazards."""
    assert getattr(config, "CAMERA_FOCAL_LENGTH_PX", None) is None


def test_missing_vision_distance_drops_the_proximity_term():
    from fusion.risk_model import vision_risk
    d = VisionDetection("person", confidence=1.0, bearing="front", distance_m=None)
    # Only the class-confidence term survives.
    assert abs(vision_risk(d, config.DEFAULT_WEIGHTS) - config.DEFAULT_WEIGHTS.w_vc) < 1e-9


def test_object_height_priors_are_physically_plausible():
    """`laptop` read 0.03 m, about 8x too small, which resolved every laptop
    detection to a sub-metre distance and fired the Medium/Critical bands."""
    from camera.detector import _APPROX_OBJECT_HEIGHT_M
    for name, height in _APPROX_OBJECT_HEIGHT_M.items():
        assert 0.1 <= height <= 2.5, f"{name} height {height} m is implausible"


# --- alert pacing constants exist and are ordered ---------------------------

def test_alert_pacing_is_configured():
    assert config.ALERT_MIN_REPEAT_S > 0
    assert config.ALERT_CRITICAL_MIN_REPEAT_S <= config.ALERT_MIN_REPEAT_S
    assert config.ALERT_CONFIRM_FRAMES >= 1
    assert config.DETECTION_TTL_S > 0


# --- directional association -----------------------------------------------

def test_detections_are_not_fused_across_bearings():
    """A chair seen on the left and a kerb felt on the right must not
    reinforce each other into a hazard that exists in neither direction.
    Before bearing matching, the fused score paired the nearest detection
    anywhere with the nearest ultrasonic anywhere."""
    from fusion.risk_model import fused_risk_by_bearing

    detections = [VisionDetection("chair", confidence=0.9, bearing="left",
                                  distance_m=1.0)]
    stick = StickReading(
        nearest_ultrasonic_m=0.6,
        down_distance_m=None,
        distances_by_bearing={"front": None, "left": None,
                              "right": 0.6, "rear": None},
    )
    matched, bearing = fused_risk_by_bearing(detections, stick,
                                             config.DEFAULT_WEIGHTS)
    unmatched_stick = StickReading(nearest_ultrasonic_m=0.6, down_distance_m=None)
    global_score, _ = fused_risk_by_bearing(detections, unmatched_stick,
                                            config.DEFAULT_WEIGHTS)
    assert matched < global_score


def test_same_bearing_observations_do_reinforce():
    from fusion.risk_model import fused_risk_by_bearing
    detections = [VisionDetection("chair", confidence=0.9, bearing="left",
                                  distance_m=1.0)]
    stick = StickReading(
        nearest_ultrasonic_m=0.6,
        down_distance_m=None,
        distances_by_bearing={"left": 0.6},
    )
    score, bearing = fused_risk_by_bearing(detections, stick,
                                           config.DEFAULT_WEIGHTS)
    assert bearing == "left"
    assert score > config.DEFAULT_WEIGHTS.w_vc * 0.9


def test_stale_stick_reading_is_not_associated():
    """Two observations far enough apart in time are not evidence about the
    same object."""
    from fusion.risk_model import fused_risk_by_bearing
    detections = [VisionDetection("chair", confidence=0.9, bearing="left",
                                  distance_m=1.0)]
    fresh = StickReading(nearest_ultrasonic_m=0.6, down_distance_m=None,
                         distances_by_bearing={"left": 0.6}, age_s=0.0)
    stale = StickReading(nearest_ultrasonic_m=0.6, down_distance_m=None,
                         distances_by_bearing={"left": 0.6},
                         age_s=config.ASSOCIATION_MAX_AGE_S + 1.0)
    fresh_score, _ = fused_risk_by_bearing(detections, fresh, config.DEFAULT_WEIGHTS)
    stale_score, _ = fused_risk_by_bearing(detections, stale, config.DEFAULT_WEIGHTS)
    assert stale_score < fresh_score


def test_no_bearing_data_falls_back_to_previous_behaviour():
    from fusion.risk_model import fused_risk_by_bearing, fused_risk
    detections = [VisionDetection("chair", confidence=0.6, bearing="front",
                                  distance_m=1.0)]
    stick = StickReading(nearest_ultrasonic_m=0.9, down_distance_m=None)
    score, bearing = fused_risk_by_bearing(detections, stick, config.DEFAULT_WEIGHTS)
    assert bearing is None
    assert abs(score - fused_risk(detections[0], stick,
                                  config.DEFAULT_WEIGHTS)) < 1e-9


def test_high_risk_fused_is_reachable_without_boundary_case():
    """The corrected fused tier is reachable without relying on the 0.5 m boundary.
    With vision distance unavailable, C=1 and d_stick=0.55 m gives R≈0.604."""
    detection = VisionDetection("chair", confidence=1.0, bearing="front", distance_m=None)
    stick = StickReading(nearest_ultrasonic_m=0.55, down_distance_m=None,
                         distances_by_bearing={"front": 0.55})
    alert = arbitrate([detection], stick, config.DEFAULT_WEIGHTS)
    assert alert.tier == config.Tier.HIGH_RISK_FUSED
    assert alert.risk_score >= config.HIGH_RISK_FUSED_THRESHOLD


def test_critical_obstacle_still_preempts_below_boundary():
    detection = VisionDetection("chair", confidence=1.0, bearing="front", distance_m=None)
    stick = StickReading(nearest_ultrasonic_m=0.49, down_distance_m=None,
                         distances_by_bearing={"front": 0.49})
    alert = arbitrate([detection], stick, config.DEFAULT_WEIGHTS)
    assert alert.tier == config.Tier.CRITICAL_OBSTACLE


