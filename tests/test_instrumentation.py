"""
Tests for the latency instrumentation.

The point of the module is that a latency figure comes from measured
per-event end-to-end intervals on one clock, never from a sum of stage means
across two paths. These tests lock that property down.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "smart_goggles"))

from instrumentation.timing import (
    LatencyEvent, LatencyRecorder, NullRecorder, VISION_PATH, STICK_PATH,
)
from instrumentation.summarize import describe, percentile


def _vision_event(base=1000.0, detect=0.100, onset=0.150, end=0.400):
    e = LatencyEvent(event_id=1, path=VISION_PATH, bearing="front")
    e.mark("capture", when=base)
    e.mark("detect_start", when=base + 0.010)
    e.mark("detect_end", when=base + 0.010 + detect)
    e.mark("fusion_start", when=base + 0.010 + detect)   # contiguous
    e.mark("fusion_end", when=base + 0.011 + detect)
    e.mark("speech_onset", when=base + onset)
    e.mark("speech_end", when=base + end)
    return e


def test_vision_origin_is_capture_not_packet_arrival():
    e = _vision_event()
    assert e.origin_stage == "capture"
    assert abs(e.end_to_end_onset_ms - 150.0) < 1e-6


def test_stick_origin_is_packet_arrival():
    e = LatencyEvent(event_id=2, path=STICK_PATH)
    e.mark("packet_rx", when=500.0)
    e.mark("fusion_start", when=500.001)
    e.mark("fusion_end", when=500.002)
    e.mark("speech_onset", when=500.060)
    assert e.origin_stage == "packet_rx"
    assert abs(e.end_to_end_onset_ms - 60.0) < 1e-6


def test_end_to_end_is_not_the_sum_of_stages():
    """The whole reason this module exists: stage means added together do
    not equal a measured end-to-end interval, because the stages overlap and
    do not all lie on one path."""
    e = _vision_event()
    stage_sum = e.queue_wait_ms + e.detect_ms + e.fusion_ms + e.alert_wait_ms
    # These stamps happen to be contiguous, so the sum agrees -- but that is
    # a property of THIS event's stamps, checked here, not an identity the
    # module assumes anywhere.
    assert abs(stage_sum - e.end_to_end_onset_ms) < 1e-6
    # Break contiguity -- a real scheduling gap between the end of inference
    # and the start of the fusion cycle -- and the sum of the named stages
    # under-reports the latency the user actually experienced. That gap is
    # invisible to a stage-mean breakdown and is exactly what grows when four
    # streams contend for the same cores.
    base = e.stamps["capture"]
    gapped = LatencyEvent(event_id=9, path=VISION_PATH, bearing="front")
    gapped.mark("capture", when=base)
    gapped.mark("detect_start", when=base + 0.010)
    gapped.mark("detect_end", when=base + 0.110)
    gapped.mark("fusion_start", when=base + 0.160)   # 50 ms scheduling gap
    gapped.mark("fusion_end", when=base + 0.161)
    gapped.mark("speech_onset", when=base + 0.200)
    stage_sum_gapped = (gapped.queue_wait_ms + gapped.detect_ms
                        + gapped.fusion_ms + gapped.alert_wait_ms)
    assert abs(stage_sum_gapped - 150.0) < 1e-6
    assert abs(gapped.end_to_end_onset_ms - 200.0) < 1e-6
    assert gapped.end_to_end_onset_ms > stage_sum_gapped


def test_speech_onset_and_completion_are_separate():
    e = _vision_event()
    assert abs(e.speech_ms - 250.0) < 1e-6
    assert e.end_to_end_complete_ms > e.end_to_end_onset_ms


def test_marks_are_write_once():
    e = _vision_event()
    original = e.stamps["capture"]
    e.mark("capture", when=original + 99.0)
    assert e.stamps["capture"] == original


def test_incomplete_event_reports_none_not_zero():
    e = LatencyEvent(event_id=3, path=VISION_PATH)
    e.mark("capture", when=1.0)
    assert e.complete is False
    assert e.end_to_end_onset_ms is None
    assert e.detect_ms is None


def test_recorder_writes_csv(tmp_path=None):
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "out.csv")
        rec = LatencyRecorder(csv_path=path)
        rec.finish(_vision_event())
        rec.close()
        with open(path) as fh:
            lines = fh.read().strip().split("\n")
        assert len(lines) == 2          # header + one row
        assert "end_to_end_onset_ms" in lines[0]


def test_null_recorder_is_inert():
    rec = NullRecorder()
    e = rec.begin(VISION_PATH)
    rec.finish(e)
    assert rec.events == []


def test_percentile_method_is_interpolated():
    values = [1.0, 2.0, 3.0, 4.0]
    assert abs(percentile(values, 0.5) - 2.5) < 1e-9
    assert abs(percentile(values, 0.95) - 3.85) < 1e-9


def test_describe_reports_n_and_spread():
    stats = describe([10.0, 20.0, 30.0])
    assert stats["n"] == 3
    assert abs(stats["median"] - 20.0) < 1e-9
    assert abs(stats["max"] - 30.0) < 1e-9


def test_describe_of_nothing_is_none():
    assert describe([]) is None
