"""
On-device YOLOv8 inference (Section III / V.B). CPU-only inference on the
Raspberry Pi 4, no hardware accelerator, per the manuscript software table. Produces the
*interpreted* detections (class, confidence, bearing, approximate distance)
that feed the fusion engine -- raw frames are never persisted or
transmitted, per the privacy-by-design principle in Section III.

DISTANCE ESTIMATION IS NOT SPECIFIED BY THE PAPER. Section V.A describes the
proof-of-concept mapping a bounding-box-height ratio onto five coarse verbal
bins (very close / close / near / moderate / far). It does NOT define a
metric distance for the full system, and no accuracy figure for vision
distance appears anywhere -- the manuscript sensor table covers the ultrasonics only. The
similar-triangles estimate below is therefore an implementation choice, and
it stays disabled until someone calibrates it: with
config.CAMERA_FOCAL_LENGTH_PX unset, every detection reports distance_m =
None, the vision proximity term drops out of the fused score, and tier 3's
2.0 m clause cannot fire. An absent distance degrades the system in a
documented way; a wrong one silently mis-ranks hazards.
"""

import logging
from dataclasses import dataclass
from typing import List

logger = logging.getLogger("blindvision.detector")

try:
    from ultralytics import YOLO
except ImportError:  # pragma: no cover
    YOLO = None

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fusion.risk_model import VisionDetection  # noqa: E402
import config  # noqa: E402

_warned_uncalibrated = False


# Nominal real-world heights (m) for the similar-triangles estimate. These
# are rough physical priors, NOT measured values from the paper. "laptop"
# previously read 0.03 m -- roughly 8x too small for an open laptop, which
# made every laptop detection resolve to a sub-metre distance and fire the
# Medium/Critical bands. Per-class heights should be replaced with measured
# values from your own dataset's annotation statistics.
_APPROX_OBJECT_HEIGHT_M = {
    "person": 1.7,
    "vehicle": 1.5,
    "bicycle": 1.1,
    "chair": 0.9,
    "door": 2.0,
    "backpack": 0.5,
    "bottle": 0.25,
    "laptop": 0.25,
    "pole": 2.0,
    "stairs": 0.20,
}
_DEFAULT_OBJECT_HEIGHT_M = 0.5


class YoloDetector:
    def __init__(self, model_path: str, confidence_threshold: float = 0.45,
                 iou_threshold: float = 0.50):
        if YOLO is None:
            raise RuntimeError("ultralytics is required: pip install ultralytics")
        self.model = YOLO(model_path)
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold

    def detect(self, image, bearing: str, timing=None) -> List[VisionDetection]:
        results = self.model.predict(
            image,
            conf=self.confidence_threshold,
            iou=self.iou_threshold,
            verbose=False,
        )
        detections: List[VisionDetection] = []
        if not results:
            return detections

        frame_height = image.shape[0] if hasattr(image, "shape") else None
        for box in results[0].boxes:
            cls_id = int(box.cls[0])
            cls_name = self.model.names.get(cls_id, str(cls_id))
            conf = float(box.conf[0])
            xyxy = box.xyxy[0].tolist()
            box_h_px = max(1.0, xyxy[3] - xyxy[1])

            distance_m = self._estimate_distance_m(cls_name, box_h_px)

            detections.append(VisionDetection(
                obj_class=cls_name,
                confidence=conf,
                bearing=bearing,
                distance_m=distance_m,
                timing=timing,
            ))
        return detections

    @staticmethod
    def _estimate_distance_m(cls_name: str, box_h_px: float):
        """Metric distance, or None while the camera is uncalibrated.

        Returning None is deliberate: the fusion engine treats a missing
        distance as a dropped term (risk_model.prox), which is the paper's
        documented degraded behaviour. Substituting a guess would put an
        unvalidated number straight into the tier thresholds.
        """
        global _warned_uncalibrated
        focal = getattr(config, "CAMERA_FOCAL_LENGTH_PX", None)
        if not focal:
            if not _warned_uncalibrated:
                logger.warning(
                    "CAMERA_FOCAL_LENGTH_PX is unset -- vision distance is "
                    "not estimated. The vision proximity term is dropped "
                    "from the fused score and tier 3's 2.0 m high-risk-class "
                    "clause is inactive. Calibrate before field use.")
                _warned_uncalibrated = True
            return None
        real_h = _APPROX_OBJECT_HEIGHT_M.get(cls_name, _DEFAULT_OBJECT_HEIGHT_M)
        return (real_h * focal) / box_h_px
