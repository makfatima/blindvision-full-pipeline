# BlindVision: A Dual-Device Sensor-Fusion System for Assistive Navigation

Official implementation and experimental/result artifacts accompanying:

**BlindVision: A Dual-Device Sensor-Fusion System for Assistive Navigation — Implementation and Experimental Validation**

## Overview

BlindVision is a dual-device assistive-navigation system combining Smart Goggles for wearable vision with a Smart Stick for independent ground-level sensing. The devices exchange structured sensor/status packets over BLE. The goggles provide on-device YOLOv8n inference and sensor fusion; the stick provides independent ultrasonic, IR, water, IMU, force, and SOS sensing with local safety behavior.

The earlier ESP32-CAM/cloud-hosted YOLOv8n validation path is retained separately from the full on-device system. It is a distinct validation stage and is not the source of the main-system ten-class evaluation.

## Repository structure

```text
BlindVision/
├── smart_goggles/              # Raspberry Pi vision, fusion, alerts, and instrumentation
├── smart_stick/                # ESP32 Smart Stick firmware
├── backend/                    # Caregiver/backend components
├── data/                       # Released experimental and derived result records
├── models/                     # Model-related configuration/status
├── proof_of_concept/            # Earlier ESP32-CAM/cloud validation stage
├── docs/                       # Architecture, hardware, latency, and study documentation
├── deploy/                     # Deployment/configuration material
├── training/                   # Training-related status/documentation
├── tools/                      # Verification and evaluation utilities
└── tests/                      # Automated tests
```

## Hardware

### Smart Goggles
- Raspberry Pi 4 Model B, 4 GB RAM
- Four wide-angle USB cameras
- YOLOv8n for on-device object detection
- u-blox NEO-6M GNSS
- SIM800L GSM/GPRS
- Bluetooth audio output
- 64 GB microSDXC
- 10,000 mAh USB power bank

### Smart Stick
- ESP32 DevKit V1
- Five ultrasonic sensors
- Two downward IR sensors
- Resistive water sensor
- MPU9250 IMU
- Tip-mounted FSR
- SOS pushbutton
- Vibration motor, piezo buzzer, and LED safety light
- Separate 3.7 V nominal, 5000 mAh 18650 Li-ion cell
- TP4056 charger

## Experimental scope

The full-system evaluation reported in the manuscript comprises 20 sessions and 100 navigation trials (~2 km). The released `data/raw/` record is a per-tester breakdown of that same 100-trial pool (seven testers, 96 successful outcomes) — it is not a breakdown by disability status. Per Section VI.A of the manuscript, that 100-trial pool was run predominantly by sighted project-team members plus one visually impaired (VI) participant; six additional VI participants completed a separate 48-trial batch reported descriptively only, with no corresponding row-level file in this release. See `data/raw/README.md` for the full distinction.

Other released measurements cover ten-class detection, BLE communication, ultrasonic and water-hazard sensing, SOS detection, latency, computational performance, power, and reliability.

## Key reported results

- Overall navigation success: **96.0% (96/100)**
- BLE packet delivery: **99.0% (7920/8000)**
- Ultrasonic hazard detection: **96.7% (174/180)**
- Water-hazard detection accuracy: **98.4%**
- SOS detection: **100% (20/20)**
- Single-stream processing-path estimate: **205 ms**
- Four-camera aggregate throughput: **22.8 FPS**

The 205 ms value is a processing-path estimate obtained by summing separately measured single-stream stage means. It is not presented as a direct simultaneous four-camera end-to-end timing measurement. The 22.8 FPS figure is the measured aggregate throughput of the four-camera run.

## Power measurements

The goggles and Smart Stick use separate power domains. The released goggles-side `data/Power_Log.csv` contains five active-detection samples at approximately 5.03–5.06 V and 2.38–2.42 A, averaging **12.11 W** at the 5-V USB input. The file does not contain separate idle or maximum-load profiles, so those runtime modes are not reported as measured. Using the nominal 37 Wh power-bank rating gives a nominal-equivalent active runtime of about **3.1 h**, which is a projection rather than a depletion test. The Smart Stick runtime figure is a separate derived upper bound from its nominal 5,000 mAh cell and an assumed 575 mA average draw.

## Backend/security scope

The released FastAPI backend speaks plain HTTP locally. TLS requires an external reverse proxy/HTTPS deployment, and the endpoint does not enforce Bearer-token authentication. The caregiver smartphone application itself is not included in the release; the backend exposes APIs for a compatible client.

## Data and model availability

The release includes the implementation, configuration, evaluation utilities, tests, documentation, and the experimental/result records included in the release. The complete image/label dataset, trained weights used for the reported results, epoch-wise training logs, and raw confusion-matrix event data are not included, consistent with the manuscript's stated data-availability scope.

## Reproduction

Install the Python dependencies listed in `requirements.txt` and consult the documentation under `docs/` for hardware configuration, latency instrumentation, and evaluation procedures. Run the automated tests before modifying the experimental configuration.

## License

See `LICENSE`.

## Metric reconciliation

The released ten-class confusion matrix contains 842 matched ground-truth instances, 805 diagonal classifications, and 37 inter-class confusions. A separate supplied aggregate reports 31 unmatched/background false detections. `tools/reconcile_detection_metrics.py` makes the accounting explicit: 95.61% matched-class recall and 68 combined false-positive assignments (0.097 per image). The raw prediction-level log is not included, so pooled precision/F1 and AP are not claimed as independently recomputed metrics.

## Remote haptic command path

The goggles-side alert dispatcher records requested haptic patterns as a logging integration point. It does not issue an active BLE characteristic write for remote haptic commands in the current release; the Stick provides local sensor-driven vibration independently.

## Supplementary material

`docs/BlindVision_SUPPLEMENTARY_MATERIAL.docx` contains the secondary protocol, dataset, sensor, power, computational, ablation, comparison, and software-environment tables moved out of the main manuscript for readability and journal-length control.


## Additional experimental records
The release includes raw per-transducer ultrasonic calibration, angle/material response, simultaneous-firing cross-talk, fusion-weight sensitivity, paired subsystem ablation, and Smart Stick discharge records under `data/raw/`, with derived summaries under `data/`.
