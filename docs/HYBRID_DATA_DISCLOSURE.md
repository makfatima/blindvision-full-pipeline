# Manuscript wording — hybrid dataset disclosure

Paste/adapt into the manuscript once a real hybrid run has been completed.
Fill in the [bracketed] values from your actual `results.csv`/`args.yaml` —
do not carry over the original Table III/V numbers here; this is a
different model trained on different data.

## For Section III (Methodology) or a new subsection "Supplementary Training Run"

> In addition to the originally reported training run, whose weights and
> raw training logs are no longer available (see Data Availability), a
> second detector was trained as part of manuscript revision using a
> combination of the public COCO dataset (person, chair, backpack, laptop,
> bottle, bicycle, vehicle classes) and [supplementary source(s) for
> door/pole/stairs, e.g. "a door subset drawn from Open Images V6"]. This
> hybrid-source model is reported separately from the original evaluation
> and is not presented as a reconstruction of it; the two runs used
> different images, different splits, and in general different sample
> counts per class.

## For the Data/Code Availability statement (replaces or supplements the
## existing "weights not included" line)

> The weights and dataset used for the results in Tables III/V are not
> available (see above). A separate model, trained on public data (COCO
> plus [supplementary source]) as described in [Section reference], is
> included in this release at `training/hybrid/` together with the dataset
> preparation scripts, exact training configuration (`args.yaml`), and
> per-epoch training log (`results.csv`) for that specific run, so that run
> — and only that run — is independently reproducible.

## For a Limitations paragraph

> Because the original training artifacts could not be recovered, results
> from the original evaluation and results from the supplementary
> hybrid-data run should not be directly compared as if measuring the same
> model; differences between them may reflect dataset composition rather
> than a change in method.

## What NOT to write

Don't reuse any phrasing that implies the hybrid run "confirms," "validates,"
or "reproduces" the original Table III/V figures — a different dataset can
corroborate the *method* but cannot corroborate the *specific reported
numbers*, and claiming otherwise is the thing that would actually create an
ethics problem, not the substitution of data itself (which your supervisor
has already sanctioned and which this document exists to keep clearly
labeled).
