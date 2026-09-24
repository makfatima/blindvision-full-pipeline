# BlindVision: A Dual-Device Sensor-Fusion System for Assistive Navigation

Official implementation and experimental/result artifacts accompanying:

**BlindVision: A Dual-Device Sensor-Fusion System for Assistive Navigation — Implementation and Experimental Validation**

## Overview

BlindVision is a dual-device assistive-navigation system combining Smart Goggles for wearable vision with a Smart Stick for independent ground-level sensing. The devices exchange structured sensor/status packets over BLE. The goggles provide on-device YOLOv8n inference and sensor fusion; the stick provides independent ultrasonic, IR, water, IMU, force, and SOS sensing.

The earlier ESP32-CAM/cloud-hosted YOLOv8n validation path is retained separately from the full on-device system. It is a distinct validation stage and is not the source of the main-system ten-class evaluation.

## Data and model availability

The repository contains the implementation, configuration, evaluation utilities, tests, documentation, and experimental/result records included in the release.

A separate companion repository, [blindvision-dataset-10class](https://github.com/makfatima/blindvision-dataset-10class), provides a reproducibility release for the hybrid 10-class YOLOv8s training experiment. That release contains the 2,380-image training set, 492-image validation set, dataset configuration, training script, recorded training arguments, trained checkpoints, epoch-wise `results.csv`, and Ultralytics evaluation plots.

**Important:** the hybrid YOLOv8s release is a separately identified training experiment. Its epoch-wise metrics must not be presented as though they are the source of every ten-class metric elsewhere in this repository or manuscript. The provenance of each reported result should be stated at the experiment/table level.

The exact package-level execution environment for the hybrid run was not captured at training time. Accordingly, this repository does not claim an exact `requirements.txt` or `environment.yml` reproduction for that historical run.

## Reproduction

For system-level reproduction, install the Python dependencies listed in `requirements.txt` and consult `docs/` for hardware configuration, latency instrumentation, and evaluation procedures.

For the separate hybrid object-detection training experiment, clone the companion dataset repository and run:

~~~bash
python train_hybrid.py --data data_hybrid.yaml
~~~

The companion repository's `args.yaml` is the authoritative record of the training configuration.

## Metric reconciliation

The released ten-class confusion matrix contains 842 matched ground-truth instances, 805 diagonal classifications, and 37 inter-class confusions. A separate supplied aggregate reports 31 unmatched/background false detections. `tools/reconcile_detection_metrics.py` makes the accounting explicit: 95.61% matched-class recall and 68 combined false-positive assignments (0.097 per image). The raw prediction-level log is not included, so pooled precision/F1 and AP are not claimed as independently recomputed metrics.

Any separate CSV containing manuscript-era aggregate detection values should be treated as a supplied/derived result record unless its provenance is explicitly tied to a released prediction-level evaluation.

## Existing system sections

See the remaining repository documentation for hardware, experimental scope, power measurements, backend/security scope, remote haptic command path, supplementary material, and additional experimental records.