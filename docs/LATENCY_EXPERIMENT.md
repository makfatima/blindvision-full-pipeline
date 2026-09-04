# Four-camera latency experiment — run protocol

This protocol is provided for any future direct four-camera latency characterization. The manuscript's 205 ms value is a processing-path estimate obtained by summing separately measured single-stream stage means; the released four-camera result is the measured 22.8 FPS aggregate throughput.

## Before the run

1. The weights on the Pi must be **the same weights used in the navigation
   trials**. `bench_latency.py` refuses to start if
   `config.YOLO_MODEL_PATH` does not exist, but it cannot tell one `.pt`
   from another — check the SHA-256 against whatever you recorded in
   `TRACEABILITY.md`. A latency figure measured with different weights is a
   different experiment.
2. Same resolution and confidence threshold as the trials
   (`CAMERA_RESOLUTION`, `YOLO_CONFIDENCE_THRESHOLD`).
3. All four cameras connected and enumerated. Confirm the index → bearing
   map; a swapped rear and left silently reassigns every per-camera row.
4. Stick powered, advertising, and paired.
5. Record in `TRACEABILITY.md`: date, operator, location, Pi OS version,
   ambient temperature, battery state, model SHA-256.

## Running

```bash
cd smart_goggles
python3 instrumentation/bench_latency.py \
    --reps 100 \
    --out runs/latency_YYYY-MM-DD.csv
```

`--reps` is **per camera direction**, matching the measurement requirement's requirement of at
least 100 repetitions per direction. The run stays open until every bearing
reaches it, so a camera producing nothing keeps the run visibly incomplete
rather than letting the other three finish and hide it.

Walk the hazard course as in the navigation trials. Present hazards to each
bearing in turn — including the rear camera, whose worst-case latency the
protocol requires specifically and which a forward-facing course never
exercises.

Every alert becomes a row, including ones the pacing gate suppressed; those
are flagged `announced=0` so the suppression rate is visible instead of
silently shrinking the sample.

If you have to stop early, rows already written are intact and valid. Report
the actual n per bearing. Do not round it up to 100.

## Producing the numbers

```bash
python3 instrumentation/summarize.py runs/latency_YYYY-MM-DD.csv --ieee
```

Everything is recomputed from the CSV on each run, so any figure that ends
up in the paper can be regenerated from the archived raw file. Archive the
CSV alongside the manuscript and cite it in `TRACEABILITY.md`.

## What the output gives you, mapped to the measurement requirement's asks

| Audit requirement (§5) | Where it comes from |
|---|---|
| All four cameras active | The run drives the real four-stream pipeline |
| Same model and resolution as the trials | Enforced by config; verify the hash |
| Synchronized timestamps | Single `time.perf_counter` for every goggles stamp |
| ≥100 repetitions per camera direction | `--reps`, enforced per bearing |
| Median, mean, SD, p95, maximum | `summarize.py`, per stage and per path |
| Queueing delay | `queue_wait_ms` — capture to inference start |
| Dropped-frame frequency | Per-stream captured vs superseded counts |
| Audio onset vs phrase completion | `speech_onset` and `speech_end`, separate |
| Per-camera and aggregate throughput | Printed at the end of the run |
| BLE one-way vs round-trip | RTT measured by ping/echo; one-way marked DERIVED |

## Two things the output will not let you do

**It will not give you one number covering both paths.** A camera-origin
hazard never crosses the BLE hop; a stick-origin hazard never crosses the
detection stage. The summary reports the two paths separately and refuses to
add them, because adding them is the error that produced 205 ms. Report both,
or report the vision path and say so.

**It will not fill in a stage with no observations.** An empty stage prints
nothing rather than a blank row inviting a guess.

## Reporting language

Once the run exists, the abstract and conclusion can say what was measured.
Until then the measurement requirement's own suggested wording is the defensible one:

> A 205 ms processing-path estimate was obtained from single-stream stage
> means; simultaneous four-camera end-to-end latency remains to be
> characterized.
