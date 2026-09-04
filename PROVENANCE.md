# BlindVision provenance

The repository contains the BlindVision implementation together with the experimental and derived result artifacts used to document the reported evaluation.

## Reported configuration

| Item | Value |
|---|---|
| Fusion weights | 0.40, 0.20, 0.25, 0.15 |
| Weight ordering | `w_vc > w_sp > w_vp > w_sc` |
| Vision range ceiling | 8 m |
| Ultrasonic range ceiling | 3 m |
| Drop-off threshold | 0.5 m |
| Critical obstacle threshold | 0.5 m |
| High-risk visual range | 2.0 m |
| Fused-risk threshold | 0.60 |
| Detection confidence threshold | 0.45 |
| IoU threshold | 0.50 |

## Experimental records

The release includes the reported ten-class detection results, participant-level navigation outcomes, BLE results, power measurements, arbitration configuration, and aggregate trial/session results.

The `data/raw/` files are a per-tester breakdown (seven testers) of the full-system 100-trial navigation aggregate, with 96 successful outcomes — not a breakdown by disability status. Per Section VI.A, that 100-trial pool was run predominantly by sighted project-team members plus one visually impaired (VI) participant; six additional VI participants completed a separate 48-trial batch reported descriptively only and not represented as row-level data here. The full-system aggregate contains 20 sessions and 100 navigation trials.

## Source-artifact boundaries

The complete image/label dataset, trained model weights, epoch-wise training logs, and raw confusion-matrix event data are not included in this release, consistent with the manuscript's Data Availability statement. Aggregate results are retained separately from unavailable lower-level source artifacts.
