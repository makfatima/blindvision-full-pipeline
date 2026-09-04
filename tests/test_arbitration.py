import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "smart_goggles"))

from config import Tier, DEFAULT_WEIGHTS
from fusion.risk_model import VisionDetection, StickReading
from fusion.arbitration import arbitrate


def test_sos_preempts_everything():
    stick = StickReading(nearest_ultrasonic_m=0.1, down_distance_m=0.6,
                          water_detected=True, fall_detected=True, sos_pressed=True)
    alert = arbitrate([], stick, DEFAULT_WEIGHTS)
    assert alert.tier == Tier.SOS
    assert alert.severity == "Emergency"


def test_dropoff_beats_lower_tiers():
    stick = StickReading(nearest_ultrasonic_m=2.0, down_distance_m=0.6,
                          water_detected=True, fall_detected=False, sos_pressed=False)
    alert = arbitrate([], stick, DEFAULT_WEIGHTS)
    assert alert.tier == Tier.CRITICAL_DROPOFF


def test_paper_worked_example_person_and_close_stick_reading():
    """Section IV test case: an approaching person 4m ahead (c=0.8)
    and a car 10m ahead (c=0.9); the stick's forward ultrasound reads 0.4m,
    inside the critical band. The test case states this must resolve to
    CRITICAL_OBSTACLE, ahead of the fused HIGH_RISK_FUSED tier the car
    would otherwise trigger once close enough."""
    detections = [
        VisionDetection("person", confidence=0.8, bearing="front", distance_m=4.0),
        VisionDetection("vehicle", confidence=0.9, bearing="front", distance_m=10.0),
    ]
    stick = StickReading(nearest_ultrasonic_m=0.4, down_distance_m=None,
                          water_detected=False, fall_detected=False, sos_pressed=False)

    alert = arbitrate(detections, stick, DEFAULT_WEIGHTS)
    assert alert.tier == Tier.CRITICAL_OBSTACLE


def test_high_risk_vision_class_within_2m_is_critical_even_without_stick():
    detections = [VisionDetection("vehicle", confidence=0.9, bearing="front", distance_m=1.5)]
    stick = StickReading(nearest_ultrasonic_m=2.9, down_distance_m=None,
                          water_detected=False, fall_detected=False, sos_pressed=False)
    alert = arbitrate(detections, stick, DEFAULT_WEIGHTS)
    assert alert.tier == Tier.CRITICAL_OBSTACLE


def test_water_hazard_tier():
    stick = StickReading(nearest_ultrasonic_m=2.5, down_distance_m=None,
                          water_detected=True, fall_detected=False, sos_pressed=False)
    alert = arbitrate([], stick, DEFAULT_WEIGHTS)
    assert alert.tier == Tier.WATER_HAZARD


def test_fall_alert_tier():
    stick = StickReading(nearest_ultrasonic_m=2.5, down_distance_m=None,
                          water_detected=False, fall_detected=True, sos_pressed=False)
    alert = arbitrate([], stick, DEFAULT_WEIGHTS)
    assert alert.tier == Tier.FALL_ALERT


def test_routine_when_nothing_nearby():
    stick = StickReading(nearest_ultrasonic_m=2.9, down_distance_m=None,
                          water_detected=False, fall_detected=False, sos_pressed=False,
                          battery_pct=80)
    alert = arbitrate([], stick, DEFAULT_WEIGHTS)
    assert alert.tier == Tier.ROUTINE


def test_low_battery_tier():
    stick = StickReading(nearest_ultrasonic_m=2.9, down_distance_m=None,
                          water_detected=False, fall_detected=False, sos_pressed=False,
                          battery_pct=15)
    alert = arbitrate([], stick, DEFAULT_WEIGHTS)
    assert alert.tier == Tier.LOW_BATTERY


def test_vision_only_mode_ignores_stick_terms():
    """Section III: if the stick disconnects, tiers 2/4/5/10 become
    unavailable and the U/W terms drop from the fused score."""
    detections = [VisionDetection("chair", confidence=0.6, bearing="front", distance_m=1.0)]
    # A stick reading that would otherwise trigger CRITICAL_DROPOFF/WATER
    # must be ignored entirely in vision_only mode.
    stick = StickReading(nearest_ultrasonic_m=0.1, down_distance_m=0.9,
                          water_detected=True, fall_detected=True, sos_pressed=False)
    alert = arbitrate(detections, stick, DEFAULT_WEIGHTS, mode="vision_only")
    assert alert.tier not in (Tier.CRITICAL_DROPOFF, Tier.WATER_HAZARD, Tier.FALL_ALERT)
