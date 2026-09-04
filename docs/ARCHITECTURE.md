# Architecture map: paper section -> code

| Paper section | Content | Code location |
|---|---|---|
| III, "Smart Goggles" | RPi4B, 4x USB camera, on-device YOLOv8, BLE 4.2, GPS/GSM, earbud, power bank | `smart_goggles/camera/`, `smart_goggles/ble/`, `smart_goggles/caregiver/` |
| III, "Smart Stick" | ESP32, 5x ultrasonic, 2x IR, water, MPU9250, FSR, SOS, vibration/buzzer/LED | `smart_stick/sensors.*`, `smart_stick/outputs.*` |
| III, "Backend/Caregiver Layer" | Event logging, geofencing, device health | `backend/`, `smart_goggles/caregiver/event_logger.py` |
| III, "Operation Modes" | Normal / Offline Stick / Vision-Only / Degraded | `smart_goggles/modes/mode_manager.py` |
| IV, risk formulas | `R = w_vc*C + w_vp*P + w_sp*U + w_sc*W`, `prox()` | `smart_goggles/fusion/risk_model.py` |
| IV, Algorithm 1 | 11-tier priority arbitration, top-down first-match-wins | `smart_goggles/fusion/arbitration.py` |
| IV, fallback behavior | Vision-Only term-dropping, Offline-Stick local logic, Degraded-mode term-dropping | `arbitration.py` (`mode=` param) + `smart_stick/smart_stick.ino` (`sensorTask`) |
| IV, fall watchdog | Forced SOS after no-recovery window | `smart_stick/sensors.cpp` (`sensors_fall_watchdog_expired`) + goggles-side mirror in `smart_goggles/main.py` |
| V.A, proof-of-concept | ESP32-CAM + cloud YOLOv8n, static per-class priority, 3s cooldown | `proof_of_concept/` |
| V.B, full system integration | End-to-end wiring of all subsystems | `smart_goggles/main.py`, `smart_stick/smart_stick.ino` |
| VI.E, latency stages | detection / BLE / fusion / audio | The released code contains optional timing instrumentation. The manuscript's 205 ms value is a serialized single-stream stage-sum estimate; the four-camera result is measured aggregate throughput, not direct end-to-end latency. |

## Data flow (Normal Mode)

```
[4x USB camera] --frame--> [YOLOv8 detector, per-camera thread]
                                   |
                                   v
                         VisionDetection list  ------\
                                                        \
[Smart Stick sensors] --BLE packet--> [StickLink] --StickReading--\
                                                                      v
                                                        [fusion.arbitrate()]
                                                        (Algorithm 1, top-down)
                                                                      |
                                                                      v
                                              [AlertDispatcher: TTS + local haptic]
                                                                      |
                                                                      v
                                              [EventLogger -> backend; HTTPS/TLS requires external termination]
```

## Recalibrating for your own build

- `smart_goggles/config.py`: fusion weights, distance bands, timeouts, YOLO
  thresholds, camera bearings/pins.
- `smart_stick/config.h`: pin assignments, distance thresholds, poll rate,
  BLE UUIDs (must match `smart_goggles/config.py`).
- Replace `YOLO_MODEL_PATH` with your own trained weights -- this repo does
  not ship the paper's ten-class model (Section V.A/Code Availability notes
  that model was never released either).
