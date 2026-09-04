"""
Proof-of-concept cloud detection API (Section V.A).

"The endpoint runs YOLOv8n inference at a 0.45 confidence threshold and
returns the detected object, its horizontal position (left/center/right,
from the bounding-box center relative to image thirds), an estimated
relative distance (very close/close/near/moderate/far, from the
bounding-box-height-to-image-height ratio), and a priority classified from
a static per-class lookup (person, vehicle, and bicycle = high; chair,
stairs, door, and backpack = medium; bottle, laptop, and pole = low).
Detections are sorted by priority, and a natural-language message for the
highest-priority detection is returned as JSON."
"""

import io
import logging
from typing import Optional

from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from PIL import Image
from ultralytics import YOLO

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("blindvision.poc.server")

app = FastAPI(title="BlindVision Proof-of-Concept Detection API")

CONFIDENCE_THRESHOLD = 0.45
IOU_THRESHOLD = 0.50

# Static per-class priority lookup, exactly as specified in Section V.A.
PRIORITY_LOOKUP = {
    "person": "high", "vehicle": "high", "bicycle": "high",
    "chair": "medium", "stairs": "medium", "door": "medium", "backpack": "medium",
    "bottle": "low", "laptop": "low", "pole": "low",
}
PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}

# Replace with your fine-tuned ten-class weights (Section V.A / Table II);
# stock yolov8n.pt only gives COCO classes, several of which (e.g. "stairs")
# do not exist in the base model and require custom training.
model = YOLO("yolov8n.pt")


class Detection(BaseModel):
    object_class: str
    horizontal_position: str   # "left" | "center" | "right"
    relative_distance: str      # "very close" | "close" | "near" | "moderate" | "far"
    priority: str                # "high" | "medium" | "low"
    confidence: float
    message: str


def _horizontal_position(box_center_x: float, image_width: int) -> str:
    third = image_width / 3.0
    if box_center_x < third:
        return "left"
    if box_center_x < 2 * third:
        return "center"
    return "right"


def _relative_distance(box_height: float, image_height: int) -> str:
    ratio = box_height / image_height
    if ratio > 0.66:
        return "very close"
    if ratio > 0.45:
        return "close"
    if ratio > 0.28:
        return "near"
    if ratio > 0.14:
        return "moderate"
    return "far"


def _message(cls: str, position: str, distance: str) -> str:
    return f"{cls.capitalize()} {position}, {distance}."


@app.post("/detect")
async def detect(request: Request):
    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="Empty request body")

    try:
        image = Image.open(io.BytesIO(body)).convert("RGB")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Invalid image: {exc}")

    results = model.predict(image, conf=CONFIDENCE_THRESHOLD, iou=IOU_THRESHOLD,
                             verbose=False)
    width, height = image.size

    detections = []
    if results:
        for box in results[0].boxes:
            cls_id = int(box.cls[0])
            cls_name = model.names.get(cls_id, str(cls_id))
            conf = float(box.conf[0])
            xyxy = box.xyxy[0].tolist()
            cx = (xyxy[0] + xyxy[2]) / 2.0
            box_h = xyxy[3] - xyxy[1]

            priority = PRIORITY_LOOKUP.get(cls_name, "low")
            position = _horizontal_position(cx, width)
            distance = _relative_distance(box_h, height)

            detections.append(Detection(
                object_class=cls_name,
                horizontal_position=position,
                relative_distance=distance,
                priority=priority,
                confidence=conf,
                message=_message(cls_name, position, distance),
            ))

    if not detections:
        return {"object_class": None, "priority": "low", "message": "", "detections": []}

    detections.sort(key=lambda d: (PRIORITY_RANK[d.priority], -d.confidence))
    top = detections[0]

    return {
        "object_class": top.object_class,
        "horizontal_position": top.horizontal_position,
        "relative_distance": top.relative_distance,
        "priority": top.priority,
        "confidence": top.confidence,
        "message": top.message,
        "detections": [d.dict() for d in detections],
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
