# Data reconciliation

The per-tester summary in `data/raw/participant_trials_breakdown.csv` contains seven tester rows (P01–P07) that together account for the full 100-trial, 96-success aggregate below — i.e., this file is the per-tester breakdown of the aggregate itself, not a separate participant subset, and not the seven VI participants described in Section VI.A. See `data/raw/README.md` for the distinction between this tester pool and the manuscript's VI-participant cohort.

The corresponding trial-level record is `data/raw/participant_trial_outcomes_100.csv`. It contains 100 trial records, 96 `SUCCESS` outcomes, and four `PARTIAL_SUCCESS` outcomes, for that same tester pool.

The full-system aggregate remains 20 sessions and 100 navigation trials, with 96 successful navigation trials, as reported in the manuscript. Per Section VI.A, that pool was run predominantly by sighted project-team members with one VI participant included; the six additional VI participants' separate 48-trial batch is reported descriptively only and has no corresponding row-level file in this release.

The ten-class detection result tables are retained separately from the navigation outcomes.

Lower-level artifacts identified as unavailable by the manuscript remain outside this release.
