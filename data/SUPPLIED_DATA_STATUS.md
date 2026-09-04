# Experimental data status

The `data/` directory contains the experimental measurements and derived result tables accompanying the BlindVision evaluation.

The per-tester summary under `data/raw/participant_trials_breakdown.csv` contains seven tester rows (P01–P07) totaling the same 100 navigation trials and 96 successful trials reported in the manuscript's Table IX. This is a per-tester breakdown of that trial pool, not a breakdown by disability status; per Section VI.A, that 100-trial pool was run predominantly by sighted project-team members plus one visually impaired (VI) participant, and is distinct from the six additional VI participants' separate 48-trial batch reported descriptively in the manuscript (not included as trial-level data in this release). See `data/raw/README.md` for the full distinction.

The corresponding trial-level record under `data/raw/participant_trial_outcomes_100.csv` contains 100 trial outcomes for that same tester pool, including 96 successful and four partial-success outcomes.

The complete image/label dataset, trained weights, epoch-wise training logs, and raw confusion-matrix event data are not included in this release.
