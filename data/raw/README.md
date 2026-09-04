# Released participant-level navigation records

This directory contains the anonymized participant-level breakdown of the 100 full-system navigation trials reported in the manuscript's Table IX (overall: 96/100, 96.0%).

`participant_trials_breakdown.csv` contains seven rows (P01–P07) totaling 100 navigation trials and 96 successful trials. These rows are a per-tester breakdown of the same 100-trial pool reported in Table IX; they are **not** a demographic breakdown by disability status, and they are **not** the seven visually impaired (VI) participants described in the manuscript's Section VI.A/Ethics Statement.

Per Section VI.A, the manuscript's own account of who ran the trials is: the 100-trial pool underlying Tables V and IX was run predominantly by sighted project-team members, with **one** VI participant's trials included in that pool; **six** additional VI participants later completed a separate 48-trial batch (8 trials each), scored descriptively and explicitly **not** folded into Tables V/IX. Do not cite this file as evidence that all, or most, of the 100 navigation trials were run by VI participants — that would contradict Section VI.A. For the actual VI-participant cohort and its scope, see the manuscript's Section VI.A and Ethics Statement.

`participant_trial_outcomes_100.csv` contains the corresponding 100 trial-level outcome records for the same tester pool. It is not a replacement for the aggregate 20-session system count, and it is not a record of the six-VI-participant 48-trial batch described above (which is reported only descriptively in the manuscript, not as trial-level data).

The released records contain task-level outcomes and do not include identifying or sensitive personal information.

## Added raw records in this release
- `Ultrasonic_Calibration_Raw.csv` — 80 observations across U1–U5, 40–300 cm, two trials/reference distance.
- `Ultrasonic_Calibration_With_Correction_Raw.csv` — same observations plus recomputed calibration and residuals.
- `Ultrasonic_Angle_Sweep_Raw.csv` — 45 observations, five sensors × nine angles, 100 cm.
- `Ultrasonic_Material_Raw.csv` — 100 observations, five sensors × four materials × five trials, 100 cm.
- `Ultrasonic_Crosstalk_Raw.csv` — five simultaneous-firing observations at 100 cm.
- `Fusion_Weight_Sensitivity_10cases.csv` — ten recorded fusion cases.
- `Fusion_Weight_Sensitivity_Summary.csv` — baseline plus eight one-at-a-time ±20% configurations.
- `Paired_Subsystem_Ablation_Raw.csv` — 16 trial-condition rows from four paired trials.
- `Smart_Stick_Continuous_Discharge_Raw.csv` — nine logged points over 240 min to recorded cutoff.

These files were supplied for this release update and are retained as raw records. Derived summaries are calculated from them; the release editor does not independently reproduce the physical experiments.

## Additional characterization records
- `Ultrasonic_Material_Range_Raw.csv`: author-supplied material/absorption/range records; preserved as a separate raw record.
- `Ultrasonic_Temperature_Humidity_Compensation_Raw.csv`: author-supplied environmental compensation records for U1 and U2; preserved as a separate raw record.
