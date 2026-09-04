# BlindVision artifact status

This release contains the implementation and experimental/result artifacts described by the accompanying manuscript.

## Included

- Smart Goggles software
- Smart White Stick firmware
- sensor-fusion and arbitration implementation
- BLE communication components
- caregiver/backend components
- training/evaluation tooling and automated tests
- ten-class detection and classwise result tables
- per-tester navigation outcomes for the 100-trial aggregate (seven testers; see `data/raw/README.md` — this is not a breakdown by disability status)
- BLE and power measurements
- aggregate 20-session / 100-trial evaluation results
- the earlier ESP32-CAM/cloud YOLOv8n validation components

## Not included

Consistent with the manuscript's Data Availability statement, the complete image dataset and labels, the trained model weights used for the reported results, epoch-wise training logs, and raw confusion-matrix event data are not included in this release.

## Model status

The cloud-hosted YOLOv8n component is the earlier validation path described in the manuscript. Its stock checkpoint is not the fine-tuned ten-class model used for the reported main-system results.

## Hybrid (public-dataset) training pipeline

`training/hybrid/` contains a real, runnable pipeline to train a new detector on public data (COCO for person/chair/backpack/laptop/bottle/bicycle/vehicle, plus a supplementary source for door/pole/stairs — see `training/hybrid/CLASS_SOURCE_MAP.md`).

**Door data is already included and real**: `training/hybrid/data/door_subset/` contains 386 real images / 580 boxes fetched from the public DoorDetect-Dataset GitHub repo and filtered/remapped to BlindVision's class scheme (see its `PROVENANCE.md` for exact source and a license/citation caveat to resolve before publishing).

**Stairs data fetched but quarantined — do not merge as-is**: `training/hybrid/data/stairs_floorplan_DOMAIN_MISMATCH_DO_NOT_MERGE/` has 444 real images/labels, but they're architectural floor-plan drawings, not real-world photos, and would likely hurt rather than help detection — see the README_WARNING.md in that folder before using it.

**Pole is not fetchable from this environment at all**: the only real bounding-box pole dataset found (`github.com/TW0521/Obstacle-Dataset`) hosts its actual files on Google Drive, which isn't in this sandbox's allowed network — same wall as Roboflow.

**The COCO subset is not yet fetched** — COCO's image host isn't reachable from this preparation environment's network either. `prepare_coco_subset.py` and the Roboflow links in `CLASS_SOURCE_MAP.md` are ready to run wherever that access exists. No training has been run yet; no weights or metrics from this pipeline exist. Manuscript wording for disclosing this run once it has actually been executed is in `docs/HYBRID_DATA_DISCLOSURE.md`.

## MERGED — all 10 classes now have real data

`training/hybrid/data/hybrid_dataset/` now contains **2,380 training / 492 validation real images across all 10 BlindVision classes**: door (DoorDetect-Dataset), pole (Roboflow "PoleDetection", CC BY 4.0), stairs (Roboflow "Stairs_Detection", MIT), and person/chair/backpack/laptop/bottle/vehicle/bicycle (COCO 2017, fetched via FiftyOne, capped at 1,200 train/150 val images). Full box counts, per-class license info, and an honest note on class imbalance (person has ~40x more boxes than laptop/bicycle) are in `training/hybrid/data/hybrid_dataset/MANIFEST.md` — read that before writing up results, especially the imbalance section.

`data_hybrid.yaml`'s `nc: 10` now matches real data in every class. No training has been run yet — `train_hybrid.py` is ready to go on a GPU. Manuscript disclosure wording for this hybrid-data run is in `docs/HYBRID_DATA_DISCLOSURE.md`.
