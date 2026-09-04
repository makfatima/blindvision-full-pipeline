"""
Every detection metric in the paper, derived from one file.

WHY
---
This utility computes only detection quantities that are derivable from a
class-level confusion table. The release also contains a separate aggregate
count for unmatched/background false detections; `tools/reconcile_detection_metrics.py`
handles that explicit reconciliation. Average precision and mAP are not derived
from confusion counts because they require ranked prediction outputs.

INPUT
-----
A CSV with one row per class:

    class,tp,fp,fn
    person,120,4,3
    chair,84,4,6
    ...

Optionally a `support` column (ground-truth instances for that class). If
absent it is taken as tp + fn, and that identity is checked.

USAGE
-----
    python3 metrics.py confusion.csv
    python3 metrics.py confusion.csv --images 700 --ieee
    python3 metrics.py confusion.csv --check-total-gt 842
"""

import argparse
import csv
import math
import sys
from typing import Dict, List, Optional

Z_95 = 1.959963984540054   # two-sided 95%, no continuity correction


def wilson(successes: int, trials: int, z: float = Z_95):
    """Wilson score interval. Named explicitly because the method must be
    reported alongside the interval -- Wilson, Wald and Clopper-Pearson give
    visibly different bounds on the small denominators used here."""
    if trials <= 0:
        return None
    p = successes / trials
    denom = 1.0 + z * z / trials
    centre = (p + z * z / (2 * trials)) / denom
    margin = (z * math.sqrt(p * (1 - p) / trials
                            + z * z / (4 * trials * trials))) / denom
    return (max(0.0, centre - margin) * 100.0,
            min(1.0, centre + margin) * 100.0)


class ClassRow:
    def __init__(self, name: str, tp: int, fp: int, fn: int,
                 support: Optional[int] = None):
        self.name = name
        self.tp, self.fp, self.fn = tp, fp, fn
        self.support = support if support is not None else tp + fn

    @property
    def predictions(self) -> int:
        return self.tp + self.fp

    @property
    def precision(self) -> Optional[float]:
        return self.tp / self.predictions if self.predictions else None

    @property
    def recall(self) -> Optional[float]:
        gt = self.tp + self.fn
        return self.tp / gt if gt else None

    @property
    def f1(self) -> Optional[float]:
        p, r = self.precision, self.recall
        if p is None or r is None or (p + r) == 0:
            return None
        return 2 * p * r / (p + r)

    @property
    def jaccard(self) -> Optional[float]:
        """TP / (TP + FP + FN). This is what the paper's "accuracy" column
        computes. It is not classification accuracy -- there are no true
        negatives in a detection task -- so it is labelled by what it is."""
        denom = self.tp + self.fp + self.fn
        return self.tp / denom if denom else None


def load(path: str) -> List[ClassRow]:
    rows = []
    with open(path, newline="") as fh:
        reader = csv.DictReader(fh)
        required = {"class", "tp", "fp", "fn"}
        missing = required - set(h.strip() for h in reader.fieldnames or [])
        if missing:
            raise SystemExit(f"CSV is missing column(s): {sorted(missing)}")
        for row in reader:
            support = row.get("support")
            rows.append(ClassRow(
                row["class"].strip(),
                int(row["tp"]), int(row["fp"]), int(row["fn"]),
                int(support) if support not in (None, "") else None,
            ))
    return rows


def check_consistency(rows: List[ClassRow]) -> List[str]:
    """Every internal identity that can be checked, checked. A warning here
    is a real disagreement in the input, not a rounding artefact."""
    problems = []
    for row in rows:
        if row.support != row.tp + row.fn:
            problems.append(
                f"{row.name}: support={row.support} but tp+fn={row.tp + row.fn}. "
                f"One of the two is wrong; they cannot both be reported.")
        if min(row.tp, row.fp, row.fn) < 0:
            problems.append(f"{row.name}: negative count.")
    return problems


def pooled(rows: List[ClassRow]) -> ClassRow:
    return ClassRow("POOLED",
                    sum(r.tp for r in rows),
                    sum(r.fp for r in rows),
                    sum(r.fn for r in rows))


def _pct(value: Optional[float]) -> str:
    return "  --  " if value is None else f"{value * 100:6.2f}"


def report(rows: List[ClassRow], images: Optional[int],
           check_total_gt: Optional[int]):
    problems = check_consistency(rows)
    if problems:
        print("!! INPUT INCONSISTENCIES -- fix these before quoting anything:")
        for p in problems:
            print("   " + p)
        print()

    total = pooled(rows)
    gt = total.tp + total.fn

    print("=" * 78)
    print("DETECTION METRICS — all derived from one confusion table")
    print("=" * 78)
    print(f"Classes: {len(rows)}")
    print(f"Ground-truth instances (TP + FN): {gt}")
    print(f"Predictions made (TP + FP):       {total.predictions}")
    print(f"TP {total.tp} / FP {total.fp} / FN {total.fn}")
    if images:
        print(f"Images: {images}   FP per image: {total.fp / images:.4f}")
    print()

    if check_total_gt is not None and gt != check_total_gt:
        print(f"!! Ground-truth total is {gt}, but {check_total_gt} was "
              f"expected. Every recall and F1 in the paper rests on this "
              f"denominator.")
        print()

    header = (f"{'class':<12}{'TP':>6}{'FP':>6}{'FN':>6}{'GT':>6}"
              f"{'Prec':>8}{'Rec':>8}{'F1':>8}{'TP/(TP+FP+FN)':>15}")
    print(header)
    print("-" * len(header))
    for row in rows:
        print(f"{row.name:<12}{row.tp:>6}{row.fp:>6}{row.fn:>6}"
              f"{row.tp + row.fn:>6}{_pct(row.precision):>8}"
              f"{_pct(row.recall):>8}{_pct(row.f1):>8}"
              f"{_pct(row.jaccard):>15}")
    print("-" * len(header))
    print(f"{'POOLED':<12}{total.tp:>6}{total.fp:>6}{total.fn:>6}"
          f"{gt:>6}{_pct(total.precision):>8}{_pct(total.recall):>8}"
          f"{_pct(total.f1):>8}{_pct(total.jaccard):>15}")
    print()

    print("Pooled figures with 95% Wilson intervals:")
    for label, successes, trials in (
            ("Recall     TP/(TP+FN)", total.tp, gt),
            ("Precision  TP/(TP+FP)", total.tp, total.predictions),
            ("TP/(TP+FP+FN)        ", total.tp,
             total.tp + total.fp + total.fn)):
        ci = wilson(successes, trials)
        point = successes / trials * 100 if trials else float("nan")
        print(f"  {label}  {point:6.2f}%  "
              f"({successes}/{trials})  CI {ci[0]:.2f}–{ci[1]:.2f}")
    print()
    print("Interval method: Wilson score, z = 1.95996, no continuity")
    print("correction. Report the method with the interval.")
    print()

    print("NOT DERIVABLE FROM THIS INPUT — do not fill these from memory:")
    print("  * classwise AP, AP50, mAP50-95 — need ranked detections with")
    print("    scores and IoU matches, not counts. Export them from the")
    print("    evaluation run that produced this table.")
    print("  * specificity and false-positive rate — need true negatives,")
    print("    which do not exist in a detection task. Report FP per image")
    print("    and 1 - precision instead.")
    print("  * per-condition breakdowns (lighting, occlusion) — need a")
    print("    confusion table per stratum. Produce one file per stratum and")
    print("    run this script on each.")


def ieee(rows: List[ClassRow], images: Optional[int]):
    print()
    print("IEEE table rows (tab-separated)")
    print("Class\tTP\tFP\tFN\tPrecision\tRecall\tF1")
    for row in rows:
        print(f"{row.name}\t{row.tp}\t{row.fp}\t{row.fn}\t"
              f"{_pct(row.precision).strip()}\t{_pct(row.recall).strip()}\t"
              f"{_pct(row.f1).strip()}")
    total = pooled(rows)
    print(f"Pooled\t{total.tp}\t{total.fp}\t{total.fn}\t"
          f"{_pct(total.precision).strip()}\t{_pct(total.recall).strip()}\t"
          f"{_pct(total.f1).strip()}")


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("csv")
    parser.add_argument("--images", type=int, default=None,
                        help="image count, for FP per image")
    parser.add_argument("--check-total-gt", type=int, default=None,
                        help="assert the ground-truth total equals this")
    parser.add_argument("--ieee", action="store_true")
    args = parser.parse_args()

    rows = load(args.csv)
    report(rows, args.images, args.check_total_gt)
    if args.ieee:
        ieee(rows, args.images)
    return 0


if __name__ == "__main__":
    sys.exit(main())
