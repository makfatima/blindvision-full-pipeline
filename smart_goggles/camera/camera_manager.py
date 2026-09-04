"""
Four wide-angle USB cameras (1080p, 120 deg FOV), mounted at the
front-left/front-right/rear-left/rear-right corners at ~90 deg intervals
(Section III). Per the paper, the four streams are processed *concurrently*
-- one detection thread/process per camera, run in parallel rather than
round-robin -- so all four directions refresh at comparable intervals.

Geometric coverage note (Section III, explicitly flagged as a calculation,
not a remeasured field test): 4 x 120 deg FOV at 90 deg spacing sums to
480 deg against a 360 deg azimuth, giving ~30 deg of nominal overlap between
adjacent cameras -- this treats the four optical centres as co-located and
therefore neglects parallax at close range.
"""

import logging
import threading
import time
from dataclasses import dataclass
from typing import Callable, Dict, Optional

logger = logging.getLogger("blindvision.camera")

try:
    import cv2
except ImportError:  # pragma: no cover - allows import on non-RPi dev machines
    cv2 = None


@dataclass
class Frame:
    bearing: str
    image: "object"       # numpy.ndarray when cv2 is available
    timestamp: float      # time.time(), for staleness checks
    seq: int = 0          # per-stream capture counter
    capture_perf: float = 0.0  # time.perf_counter() at capture, for latency
    dropped_before: int = 0    # frames captured and superseded since the
                                # last one a consumer actually took


class CameraStream:
    """Owns one camera's capture loop on its own thread."""

    def __init__(self, bearing: str, device_index: int, resolution=(1920, 1080)):
        self.bearing = bearing
        self.device_index = device_index
        self.resolution = resolution
        self._cap = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._latest: Optional[Frame] = None
        self._lock = threading.Lock()

        # A capture loop that overwrites `_latest` silently discards every
        # frame a consumer did not get to. That discard rate is exactly the
        # dropped-frame figure a four-camera latency experiment has to
        # report, so it is counted rather than lost.
        self.frames_captured = 0
        self.frames_superseded = 0
        self._unconsumed = 0

    def start(self):
        if cv2 is None:
            raise RuntimeError("opencv-python is required on the Raspberry Pi build")
        self._cap = cv2.VideoCapture(self.device_index)
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
        if not self._cap.isOpened():
            raise RuntimeError(f"Could not open camera '{self.bearing}' "
                                f"(index {self.device_index})")
        self._running = True
        self._thread = threading.Thread(target=self._loop, name=f"cam-{self.bearing}",
                                         daemon=True)
        self._thread.start()
        logger.info("Camera stream '%s' started on index %d", self.bearing, self.device_index)

    def _loop(self):
        while self._running:
            ok, frame = self._cap.read()
            if not ok:
                logger.warning("Frame read failed on camera '%s'", self.bearing)
                time.sleep(0.05)
                continue
            captured_perf = time.perf_counter()
            with self._lock:
                if self._latest is not None:
                    # The previous frame was never taken by a consumer.
                    self.frames_superseded += 1
                    self._unconsumed += 1
                self.frames_captured += 1
                self._latest = Frame(
                    bearing=self.bearing,
                    image=frame,
                    timestamp=time.time(),
                    seq=self.frames_captured,
                    capture_perf=captured_perf,
                    dropped_before=self._unconsumed,
                )

    def latest(self) -> Optional[Frame]:
        """Take the newest frame, if one has arrived since the last call.

        Returns None rather than re-serving a frame already consumed, so a
        detection worker never re-times the same capture and inflates the
        event count.
        """
        with self._lock:
            frame = self._latest
            self._latest = None
            if frame is not None:
                self._unconsumed = 0
            return frame

    def drop_stats(self) -> Dict[str, int]:
        with self._lock:
            return {
                "captured": self.frames_captured,
                "superseded": self.frames_superseded,
            }

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
        if self._cap:
            self._cap.release()


class CameraManager:
    """Owns all four camera streams and exposes the latest frame per bearing."""

    def __init__(self, device_map: Dict[str, int], resolution=(1920, 1080)):
        """device_map: e.g. {"front": 0, "right": 1, "rear": 2, "left": 3}"""
        self.streams = {
            bearing: CameraStream(bearing, index, resolution)
            for bearing, index in device_map.items()
        }

    def start_all(self):
        for stream in self.streams.values():
            stream.start()

    def stop_all(self):
        for stream in self.streams.values():
            stream.stop()

    def latest_frames(self) -> Dict[str, Optional[Frame]]:
        return {bearing: s.latest() for bearing, s in self.streams.items()}

    def drop_stats(self) -> Dict[str, Dict[str, int]]:
        """Per-stream captured/superseded counts. `superseded` is the number
        of frames that were captured and then overwritten before any
        consumer took them -- the dropped-frame rate under load."""
        return {b: s.drop_stats() for b, s in self.streams.items()}

    def for_each_new_frame(self, callback: Callable[[Frame], None], poll_hz: float = 15.0):
        """Convenience loop for single-process use: calls `callback` whenever
        a fresher frame than last-seen is available on any stream. In
        production, prefer one detection worker per stream (see main.py)."""
        last_ts = {b: 0.0 for b in self.streams}
        period = 1.0 / poll_hz
        while True:
            for bearing, stream in self.streams.items():
                f = stream.latest()
                if f and f.timestamp > last_ts[bearing]:
                    last_ts[bearing] = f.timestamp
                    callback(f)
            time.sleep(period)
