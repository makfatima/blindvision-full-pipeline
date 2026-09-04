# Artifact provenance and recovery notes

This document describes lower-level artifacts that may be useful for deeper
reproducibility when they are not included in the current release.

The repository already contains experimental data and derived result tables
supplied for the BlindVision project. Those supplied files should be treated
as project experimental/result artifacts with the provenance documented in this
release.

Some lower-level source artifacts may still be absent, such as a binary
trained model checkpoint, complete image/label archive, or a particular
timestamped source trace. If such an artifact is later recovered, record its
original path, date, hash, and provenance before replacing or supplementing
the current release.

## Useful recovery locations

For model-training artifacts, check the original training environment for
the Ultralytics run directory, including `weights/best.pt`, `weights/last.pt`,
`args.yaml`, and `results.csv`.

For deployed hardware, preserve the original Raspberry Pi storage and ESP32
firmware before reflashing or overwriting it.

For trial records, preserve dated CSVs, spreadsheets, score sheets, and
contemporaneous logs in their original form.

## Rule

Do not recreate a missing measurement from a manuscript number. If a
lower-level artifact is unavailable, record that fact explicitly. The
experimental/result files already supplied in `data/` are not to be replaced
or numerically altered during repository cleanup.
