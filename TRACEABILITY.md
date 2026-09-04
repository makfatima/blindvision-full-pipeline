# Traceability manifest

| Reported result | Repository artifact |
|---|---|
| Ten-class dataset composition | `data/Dataset_Split.csv`, `data/Dataset_Manifest_.csv`, `data/Class_Definition.csv` |
| Held-out detection metrics | `data/Heldout_Test.csv`, `data/YOLO_Metrics.csv` |
| Per-class detection results (recomputed from Table IV's confusion matrix) | `data/Classwise_Evaluation.csv` |
| Ten-class confusion matrix | `data/Confusion_Matrix.csv` |
| Participant navigation outcomes | `data/raw/participant_trials_breakdown.csv`, `data/raw/participant_trial_outcomes_100.csv` — a per-tester (not per-disability-status) breakdown; see note below |
| Full-system aggregate counts | `data/Trial_Session__Summary.csv` |
| BLE results | `data/BLE_Trace__Summary.csv` |
| Power measurements | `data/Power_Log.csv` |
| Fusion/arbitration configuration | `data/Arbitration_Ladder_Supplied.csv`, `smart_goggles/config.py` |
| Caregiver event path | `data/Caregiver_API_Runtime_Summary.csv` |

## Note on participant data

The `data/raw/` files trace Table IX's 100-trial aggregate by tester (P01–P07), not by disability status. The manuscript's seven-visually-impaired-participant cohort (Section VI.A) is a separate accounting: one of those participants' trials fall within this 100-trial pool, and the other six ran a distinct 48-trial batch that is reported only descriptively and has no row-level file in this release. Do not cite `data/raw/` as trial-level evidence for the six-participant batch.

## Confusion-matrix accounting basis

`data/Confusion_Matrix.csv` is a closed, matched class-to-class matrix. It contains 842 ground-truth instances, 805 diagonal correct classifications, and 37 off-diagonal inter-class confusions. The matrix does not contain a background/no-detection row or column and therefore does not include unmatched/background false detections.

The released evaluation contains two aggregate accounting views: 37 inter-class confusions in the matched 10-class matrix and 31 supplied unmatched/background false detections. `tools/reconcile_detection_metrics.py` combines these only for an explicit reconciliation: 68 total false-positive assignments, 95.61% matched-class recall, 92.21% pooled precision if every inter-class confusion is counted as an FP for the predicted class, and 93.88% corresponding F1. The raw prediction-level log is unavailable, so the manuscript does not claim an independently recomputed pooled precision/F1 or AP.

## BLE timing basis

The 17.5 ms BLE value is a derived one-way estimate (RTT/2) from ping-token round-trip measurements on the Raspberry Pi. The ESP32 and Raspberry Pi do not share a synchronized clock, so it is not a direct one-way timestamp difference.

## Power provenance

`data/Power_Log.csv` contains five active-detection samples averaging 12.11 W. It does not contain the previously stated 1.48 A/1.86 A profiles or separate idle/maximum-load discharge runs. The manuscript therefore reports the released samples directly and treats the approximately 3.1 h active runtime as a nominal-equivalent projection from 37 Wh / 12.11 W.

## Caregiver/API provenance

`data/Caregiver_API_Runtime_Summary.csv` is aligned to the released backend: local HTTP, no enforced Bearer authentication, and HTTP 200 for `POST /api/v1/events`. TLS is an external deployment concern rather than a feature enforced by `backend/app.py`.

## Implementation-status notes

The released goggles-side remote haptic callback is an integration logging stub; the stick's local haptic path is implemented. Vision distance estimation remains disabled because `CAMERA_FOCAL_LENGTH_PX` is `None`; consequently the vision-proximity term and the 2 m high-risk visual-class distance clause are inactive in the released configuration. The proof-of-concept uses stock `yolov8n.pt`; the fine-tuned ten-class weights are not included.

The four-camera throughput result is measured at 22.8 FPS aggregate, while the 205 ms value is a serialized single-stream stage-sum estimate and not a direct four-camera end-to-end latency measurement. The released latency protocol is documented in `docs/LATENCY_EXPERIMENT.md`.

## Unavailable source artifacts

The complete image/label dataset, trained model weights, epoch-wise training logs, and raw confusion-matrix event data are not included in this release, consistent with the manuscript's Data Availability statement.
