"""
Per-stage latency instrumentation.

WHY THIS EXISTS
---------------
The reported 205 ms figure is the sum of four separately measured stage
means (122 + 17.5 + 9 + 56). Two things follow, and this module is built
around both:

1. A sum of stage means is not the mean of measured end-to-end trials. It
   carries no distribution, so no median, SD, 95th percentile or maximum can
   be quoted from it.

2. The four stages are not all in series on any single path. A hazard seen
   by a camera never traverses the stick -> goggles BLE hop; a hazard felt by
   the stick never traverses the detection stage. The vision path is
   capture -> inference -> fusion -> speech; the stick path is packet
   arrival -> fusion -> speech. Adding all four stages sums across two
   mutually exclusive paths.

So every record here is tagged with the path it actually travelled, and
end-to-end latency is measured from that path's own origin to speech onset,
on one clock, per event. Nothing is summed across paths.

CLOCKS
------
All goggles-side stamps come from a single monotonic clock
(`time.perf_counter`). The stick runs its own unsynchronised clock, so a
stick-originated event cannot be stamped at its true sensor-read instant
from this side. What can be measured is the BLE round trip (see
`ble.stick_link.measure_rtt`); the one-way component is RTT/2 and is
recorded as DERIVED, never as measured.
"""

import csv
import logging
import os
import threading
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional

logger = logging.getLogger("blindvision.instrumentation")

# One clock for every goggles-side stamp in this process.
CLOCK = time.perf_counter


VISION_PATH = "vision"
STICK_PATH = "stick"

# Stage names, in the order they occur on each path.
VISION_STAGES = ["capture", "detect_start", "detect_end",
                 "fusion_start", "fusion_end", "speech_onset", "speech_end"]
STICK_STAGES = ["packet_rx", "fusion_start", "fusion_end",
                "speech_onset", "speech_end"]


@dataclass
class LatencyEvent:
    """One hazard, followed from its origin to the end of the spoken alert."""

    event_id: int
    path: str                      # VISION_PATH | STICK_PATH
    bearing: Optional[str] = None  # camera bearing, vision path only
    frame_seq: Optional[int] = None
    frames_dropped_before: int = 0
    queue_depth: int = 0
    tier: Optional[str] = None
    severity: Optional[str] = None
    announced: bool = False        # False if the pacing gate suppressed it
    ble_rtt_ms: Optional[float] = None   # measured, if a ping was in flight
    stamps: Dict[str, float] = field(default_factory=dict)

    # -- recording ---------------------------------------------------------

    def mark(self, stage: str, when: Optional[float] = None):
        """Stamp a stage. First write wins, so a retry cannot overwrite the
        original instant."""
        if stage not in self.stamps:
            self.stamps[stage] = CLOCK() if when is None else when

    # -- derived intervals -------------------------------------------------

    def _delta_ms(self, a: str, b: str) -> Optional[float]:
        if a in self.stamps and b in self.stamps:
            return (self.stamps[b] - self.stamps[a]) * 1000.0
        return None

    @property
    def origin_stage(self) -> str:
        return "capture" if self.path == VISION_PATH else "packet_rx"

    @property
    def detect_ms(self) -> Optional[float]:
        return self._delta_ms("detect_start", "detect_end")

    @property
    def queue_wait_ms(self) -> Optional[float]:
        """Capture to the start of inference: how long the frame sat waiting
        for a detection worker. Invisible in a stage-mean breakdown, and the
        first thing to grow when four streams share one CPU."""
        return self._delta_ms("capture", "detect_start")

    @property
    def fusion_ms(self) -> Optional[float]:
        return self._delta_ms("fusion_start", "fusion_end")

    @property
    def alert_wait_ms(self) -> Optional[float]:
        """Fusion decision to the first sound: dispatcher queueing plus TTS
        startup."""
        return self._delta_ms("fusion_end", "speech_onset")

    @property
    def speech_ms(self) -> Optional[float]:
        """Speech onset to phrase completion. The audit asks for these two
        separately; a user has not been warned until the phrase carrying the
        direction has finished."""
        return self._delta_ms("speech_onset", "speech_end")

    @property
    def end_to_end_onset_ms(self) -> Optional[float]:
        """Path origin -> first sound. This is the number a latency claim
        should be built from."""
        return self._delta_ms(self.origin_stage, "speech_onset")

    @property
    def end_to_end_complete_ms(self) -> Optional[float]:
        return self._delta_ms(self.origin_stage, "speech_end")

    @property
    def complete(self) -> bool:
        return "speech_onset" in self.stamps

    def to_row(self) -> dict:
        row = {
            "event_id": self.event_id,
            "path": self.path,
            "bearing": self.bearing or "",
            "frame_seq": self.frame_seq if self.frame_seq is not None else "",
            "frames_dropped_before": self.frames_dropped_before,
            "queue_depth": self.queue_depth,
            "tier": self.tier or "",
            "severity": self.severity or "",
            "announced": int(self.announced),
            "ble_rtt_ms": _r(self.ble_rtt_ms),
            "queue_wait_ms": _r(self.queue_wait_ms),
            "detect_ms": _r(self.detect_ms),
            "fusion_ms": _r(self.fusion_ms),
            "alert_wait_ms": _r(self.alert_wait_ms),
            "speech_ms": _r(self.speech_ms),
            "end_to_end_onset_ms": _r(self.end_to_end_onset_ms),
            "end_to_end_complete_ms": _r(self.end_to_end_complete_ms),
        }
        for stage in set(VISION_STAGES) | set(STICK_STAGES):
            row[f"t_{stage}"] = _r(self.stamps.get(stage), 6)
        return row


def _r(value, places: int = 3):
    return "" if value is None else round(value, places)


CSV_COLUMNS = [
    "event_id", "path", "bearing", "frame_seq", "frames_dropped_before",
    "queue_depth", "tier", "severity", "announced", "ble_rtt_ms",
    "queue_wait_ms", "detect_ms", "fusion_ms", "alert_wait_ms", "speech_ms",
    "end_to_end_onset_ms", "end_to_end_complete_ms",
] + [f"t_{s}" for s in sorted(set(VISION_STAGES) | set(STICK_STAGES))]


class LatencyRecorder:
    """Thread-safe collector. Every completed event is appended to a CSV as
    it finishes, so a run that is interrupted still leaves usable raw data.

    The CSV is the record of truth. Summary statistics are computed from it
    by `summarize.py` and never cached here, so a reported figure always has
    a file behind it.
    """

    def __init__(self, csv_path: Optional[str] = None, keep_in_memory: bool = True):
        self.csv_path = csv_path
        self.keep_in_memory = keep_in_memory
        self._events: List[LatencyEvent] = []
        self._lock = threading.Lock()
        self._next_id = 0
        self._writer = None
        self._fh = None
        self.started_at = CLOCK()
        self.started_wall = time.time()
        if csv_path:
            os.makedirs(os.path.dirname(os.path.abspath(csv_path)), exist_ok=True)
            new = not os.path.exists(csv_path) or os.path.getsize(csv_path) == 0
            self._fh = open(csv_path, "a", newline="")
            self._writer = csv.DictWriter(self._fh, fieldnames=CSV_COLUMNS)
            if new:
                self._writer.writeheader()
                self._fh.flush()

    def begin(self, path: str, **kwargs) -> LatencyEvent:
        with self._lock:
            event_id = self._next_id
            self._next_id += 1
        event = LatencyEvent(event_id=event_id, path=path, **kwargs)
        event.mark(event.origin_stage)
        return event

    def finish(self, event: LatencyEvent):
        with self._lock:
            if self.keep_in_memory:
                self._events.append(event)
            if self._writer:
                self._writer.writerow(event.to_row())
                self._fh.flush()

    @property
    def events(self) -> List[LatencyEvent]:
        with self._lock:
            return list(self._events)

    @property
    def elapsed_s(self) -> float:
        return CLOCK() - self.started_at

    def close(self):
        if self._fh:
            self._fh.close()
            self._fh = None


class NullRecorder(LatencyRecorder):
    """Zero-overhead stand-in for normal operation, so the production path
    does not pay for instrumentation it is not using."""

    def __init__(self):
        super().__init__(csv_path=None, keep_in_memory=False)

    def begin(self, path: str, **kwargs) -> LatencyEvent:
        return LatencyEvent(event_id=-1, path=path)

    def finish(self, event: LatencyEvent):
        return None
