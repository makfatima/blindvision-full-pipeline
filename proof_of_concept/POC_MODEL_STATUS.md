# Proof-of-concept model status

## Status: NOT THE REPORTED FINE-TUNED MODEL

`proof_of_concept/cloud_server/app.py` instantiates the stock Ultralytics `yolov8n.pt` checkpoint. This is the cloud validation path described in the manuscript and is not the fine-tuned ten-class model reported for the main BlindVision evaluation.

The stock checkpoint (standard 80-class COCO weights, unmodified from the Ultralytics release) is bundled at `proof_of_concept/cloud_server/yolov8n.pt` so the proof-of-concept path runs offline without triggering an Ultralytics download on first launch. Its class list (`person`, `bicycle`, `car`, ... `toothbrush`) is the standard 80-class COCO ordering; it has not been fine-tuned on any BlindVision data.

The fine-tuned trained weights used for the reported results are not included in this release.
