# Changes in final revision

- Reconciled the held-out detector accounting using the released confusion matrix plus the supplied unmatched-FP aggregate; removed unsupported pooled precision/F1 claims from the manuscript.
- Corrected the HIGH_RISK_FUSED threshold to 0.60 so it is reachable without relying on the 0.5 m boundary when vision distance is unavailable; added a non-boundary regression test and documented that the correction postdates the navigation evaluation.
- Documented the goggles-to-stick remote haptic path as a logging integration point; no active BLE haptic write or quantitative remote-haptic success claim is made.
- Added close IEEE Sensors Journal prior art: Chang et al. (2020) and Feng et al. (2025).
- Corrected the graphical abstract caregiver label to “Caregiver Backend/API”.
- Moved detailed secondary tables to a separate supplementary document; main manuscript renders to 9 pages.
- Kept author/ORCID placeholders as requested.
- Equation numbering is retained visibly as (1)–(4).

## Latest release update — raw experimental records and calibration
- Preserved all existing manuscript figures/images (five embedded manuscript images) and all previously released data files.
- Added author-supplied raw five-transducer ultrasonic calibration (80 rows) and recomputed the regression coefficients from those rows.
- Updated ESP32 ultrasonic acquisition to apply the inverse per-transducer calibration at runtime.
- Added raw incidence-angle, target-material, and simultaneous-firing cross-talk records and derived summaries.
- Added the ten-case ±20% fusion-weight sensitivity record and summary.
- Added trial-level paired subsystem ablation (four trials × four conditions).
- Added the 240-minute Smart Stick continuous discharge record.
- Updated manuscript and supplementary material to describe these experiments and their limitations without deleting the earlier aggregate measurements.

## Expanded transducer characterization
- Added the supplied material/absorption/range raw record without deleting earlier material data.
- Added the supplied temperature/humidity compensation raw record for U1–U2.
- Expanded Section III with beam/angular response, recalibrated distance correction, material/range, and environmental compensation characterization.
- Preserved all five existing manuscript images and all prior raw experimental artifacts.
