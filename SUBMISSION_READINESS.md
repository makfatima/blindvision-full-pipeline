# Submission Readiness — BlindVision

## Current release status

This release is manuscript-synchronized and regression-tested. The manuscript in `docs/BlindVision_FINAL_MANUSCRIPT.docx` and `.pdf` is the canonical version; supplementary material is in `docs/BlindVision_SUPPLEMENTARY_MATERIAL.docx` and `.pdf`.

### Corrections made in this release

- The fused-risk threshold is `R >= 0.60`, making the fused tier reachable without relying on the exact 0.5 m boundary when camera-distance P is unavailable. This is a post-evaluation configuration correction; the 100 navigation trials are not used to estimate activation frequency of the revised tier.
- The goggles-side remote haptic path is a logging integration point rather than an active BLE write. Stick-local haptic alerts remain implemented independently. No remote-haptic success rate is claimed.
- Detector precision/F1 are reconciled from the released aggregate accounting: 92.2% precision and 93.9% F1; the original supplied 96.3%/95.9% values are retained only in source/provenance files, not as final manuscript metrics.
- Dangling table references created by table relocation have been removed or changed to the corresponding supplementary table numbers.
- The graphical abstract identifies the caregiver backend/API rather than an implemented smartphone app.
- The abstract is below 250 words and the main manuscript is 9 pages.
- Equation numbers (1)–(4) are visible in the rendered manuscript.
- The short factual AI-use acknowledgment is retained because the manuscript/code preparation history included substantive AI assistance; no claim is made that AI generated or altered experimental data.

## Evidence gaps that cannot be reconstructed from the supplied release

The evaluated YOLO weights, complete image/label dataset, raw prediction-level logs, raw BLE packet trace, and original training environment are not present in the supplied project records. These are disclosed as unavailable rather than replaced with fabricated artifacts.

Institutional ethics/exemption determination and final author metadata (names, affiliations, e-mail addresses, ORCIDs) must be supplied by the authors before submission.

## Latest experimental additions
The current release now includes per-transducer ultrasonic calibration/characterization, a limited fusion-weight sensitivity check, a trial-level paired subsystem ablation, and a single continuous Smart Stick discharge record. These are small-sample engineering validations and are not presented as comprehensive robustness or clinical evidence. The raw records are under `data/raw/` and corresponding derived summaries are under `data/`.
