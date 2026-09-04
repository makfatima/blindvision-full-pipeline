# Hybrid dataset — per-class source mapping

This documents, class by class, where real images/annotations for a NEW training
run can legitimately come from, using BlindVision's class scheme
(`0 person, 1 door, 2 chair, 3 backpack, 4 laptop, 5 bottle, 6 pole, 7 vehicle,
8 bicycle, 9 stairs` — from `data/Class_Definition.csv`).

This is a plan for a **second, new training run on different data**. It is not
a way to reconstruct the original 5,600-image dataset, and it will not
reproduce the originally reported numbers. Treat any results from it as a
distinct experiment.

## Directly covered by COCO (auto-downloadable, no manual sourcing needed)

| BlindVision class | COCO class | COCO id |
|---|---|---|
| person | person | 0 |
| chair | chair | 56 |
| backpack | backpack | 24 |
| laptop | laptop | 63 |
| bottle | bottle | 39 |
| bicycle | bicycle | 1 |
| vehicle | car (+ optionally truck, bus) | 2 (+7, 5) |

`prepare_coco_subset.py` pulls these seven classes straight out of COCO
train2017/val2017 via Ultralytics' own auto-download, so this part needs no
extra dataset hunting — just bandwidth and disk.

## NOT in COCO — need a second source

COCO has no `door`, `pole`, or `stairs` category. Confirmed real, currently
live sources (checked Sep 2026) for each:

- **door** — **DoorDetect Dataset**, `github.com/MiguelARD/DoorDetect-Dataset`.
  1,213 images, already labeled with a `door` class (plus handle/cabinet
  door/fridge door — drop those), built from Open Images V4 + MCIndoor20000,
  YOLO-style `.txt` labels out of the box. `git clone` it, no API key.
  For more volume, pull Open Images V6's native `Door` class via
  `pip install fiftyone` then
  `foz.load_zoo_dataset("open-images-v6", classes=["Door"], label_types=["detections"])`.
- **stairs** — Roboflow Universe, "Stairs_Detection" (601 images, plain
  `stairs` class): `universe.roboflow.com/yolo-datasets-f9og9/stairs_detection-9av4i-lyswf-orcim-duw1m`.
  Larger option (1,809 images): "Stair Detection Dataset" at
  `universe.roboflow.com/siavash-mahmoudi/stair-detection-sb2fk`.
  (Skip the DataCluster Labs "Stairs Image Dataset" — CC-BY but the bulk of
  it is paywalled/license-restricted, not a clean free pull.)
- **pole** — Roboflow Universe, "PoleDetection" (602 images, plain `pole`
  class): `universe.roboflow.com/yolo-detections-self-learning/poledetection-pxxqj`.
  Alternative: "Utility Pole" by Yue-Hung (511 images):
  `universe.roboflow.com/yue-hung/utility-pole-5j6dp`. A larger 7,546-image
  set exists (`pole-data-q98xs`) but mixes in transformer/wire/crossarm/
  streetlight classes — usable if you filter the export down to just the
  `pole` boxes. Also real (checked): `github.com/TW0521/Obstacle-Dataset` —
  a 15-class real street-obstacle set including `pole`, ~7,900 images total,
  VOC+YOLO format — but its actual image files are hosted on Google Drive
  (linked from that repo's README), not in the git repo itself.

For the Roboflow ones: `pip install roboflow`, then each project page's
"Download Dataset" button gives you the exact
`roboflow.download_dataset(dataset_url=..., model_format="yolov8")` snippet
— already in YOLO format, no manual conversion.

I found these via web search, not by fetching them myself — my sandbox's
network is restricted to package registries (PyPI, npm, GitHub), not
image-dataset hosts, so pulling the actual files has to happen on your
machine or Colab.

## Two honest options once you have (or don't have) door/pole/stairs data

1. **7-class run now, 10-class later** — train on just the COCO-coverable
   seven, report it explicitly as a 7-class subset evaluation, and note
   door/pole/stairs remain untrained pending supplementary data. This is the
   fastest path to a real, defensible number.
2. **10-class run** — source door/pole/stairs per above first, merge into one
   `data.yaml`, then train the full ten. Slower, but matches the manuscript's
   original class count.

Either is fine to report, as long as the manuscript says which one you did.
