"""
Turn a raw latency CSV into the statistics the audit asks for.

Reads only the CSV. Every number printed here is recomputed from the file on
each run, so a figure quoted in the paper can always be regenerated from the
archived raw data by re-running this script.

Reports, per path and per camera bearing:
    n, mean, median, SD, 95th percentile, max

for each stage and for end-to-end latency to speech onset and to phrase
completion, plus dropped-frame rate and aggregate throughput.

Usage:
    python3 summarize.py runs/latency_2026-08-04.csv
    python3 summarize.py runs/*.csv --ieee
"""

import argparse
import csv
import math
import statistics
import sys
from collections import defaultdict
from typing import Dict, List, Optional

STAGE_COLUMNS = [
    ("queue_wait_ms", "Capture to inference start (queue wait)"),
    ("detect_ms", "YOLOv8 inference"),
    ("fusion_ms", "Score fusion + arbitration"),
    ("alert_wait_ms", "Arbitration to speech onset"),
    ("speech_ms", "Speech onset to completion"),
    ("end_to_end_onset_ms", "END-TO-END: origin to speech onset"),
    ("end_to_end_complete_ms", "END-TO-END: origin to phrase completion"),
]


def percentile(values: List[float], q: float) -> Optional[float]:
    """Linear-interpolation percentile. Stated explicitly because the method
    changes the number and the audit asks for the method to be reported."""
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    pos = (len(ordered) - 1) * q
    lower = math.floor(pos)
    upper = math.ceil(pos)
    if lower == upper:
        return ordered[int(pos)]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (pos - lower)


def describe(values: List[float]) -> Optional[dict]:
    if not values:
        return None
    return {
        "n": len(values),
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "sd": statistics.stdev(values) if len(values) > 1 else float("nan"),
        "p95": percentile(values, 0.95),
        "max": max(values),
    }


def load(paths: List[str]) -> List[dict]:
    rows = []
    for path in paths:
        with open(path, newline="") as fh:
            for row in csv.DictReader(fh):
                rows.append(row)
    return rows


def _floats(rows: List[dict], column: str) -> List[float]:
    out = []
    for row in rows:
        raw = row.get(column, "")
        if raw not in ("", None):
            out.append(float(raw))
    return out


def _fmt(stats: Optional[dict]) -> str:
    if not stats:
        return "        --          (no observations)"
    sd = "  n/a" if math.isnan(stats["sd"]) else f"{stats['sd']:6.1f}"
    return (f"n={stats['n']:<5d} mean={stats['mean']:7.1f}  "
            f"median={stats['median']:7.1f}  sd={sd}  "
            f"p95={stats['p95']:7.1f}  max={stats['max']:7.1f}")


def report(rows: List[dict]):
    if not rows:
        print("No rows. Nothing to report.")
        return

    by_path = defaultdict(list)
    for row in rows:
        by_path[row["path"]].append(row)

    print("=" * 78)
    print("LATENCY SUMMARY — all values in milliseconds")
    print("=" * 78)
    print(f"Total events recorded: {len(rows)}")
    print("Percentile method: linear interpolation between order statistics.")
    print()
    print("Paths are reported separately and are NEVER summed. A vision-origin")
    print("hazard does not traverse the BLE hop; a stick-origin hazard does not")
    print("traverse the detection stage. There is no single figure that covers")
    print("both, and any claim of one is a sum over mutually exclusive paths.")
    print()

    for path in sorted(by_path):
        path_rows = by_path[path]
        print("-" * 78)
        print(f"PATH: {path}   (n = {len(path_rows)} events)")
        print("-" * 78)
        for column, label in STAGE_COLUMNS:
            values = _floats(path_rows, column)
            if not values:
                continue
            print(f"  {label:<42s} {_fmt(describe(values))}")
        print()

        if path == "vision":
            by_bearing = defaultdict(list)
            for row in path_rows:
                by_bearing[row["bearing"] or "(unknown)"].append(row)
            print("  Per-camera end-to-end to speech onset:")
            for bearing in sorted(by_bearing):
                values = _floats(by_bearing[bearing], "end_to_end_onset_ms")
                print(f"    {bearing:<12s} {_fmt(describe(values))}")

            dropped = sum(int(r["frames_dropped_before"] or 0) for r in path_rows)
            print()
            print(f"  Frames captured but superseded before inference: {dropped}")
            if dropped + len(path_rows) > 0:
                rate = dropped / (dropped + len(path_rows)) * 100.0
                print(f"  Drop rate: {rate:.1f}% of captured frames")
            queues = [int(r["queue_depth"] or 0) for r in path_rows]
            if queues:
                print(f"  Dispatcher queue depth at arbitration: "
                      f"mean {statistics.fmean(queues):.2f}, max {max(queues)}")
            print()

        if path == "stick":
            rtts = _floats(path_rows, "ble_rtt_ms")
            if rtts:
                stats = describe(rtts)
                print(f"  BLE round trip (MEASURED)                  {_fmt(stats)}")
                print(f"  BLE one-way (DERIVED as RTT/2, not measured): "
                      f"median {stats['median'] / 2:.1f}")
            else:
                print("  BLE round trip: no ping/echo pairs recorded in this run.")
            print()

    announced = sum(1 for r in rows if r.get("announced") == "1")
    print("-" * 78)
    print(f"Events announced: {announced} of {len(rows)} "
          f"({announced / len(rows) * 100:.1f}%). The remainder were "
          f"suppressed by the")
    print("alert pacing gate (confirm-frames / repeat interval) and did not "
          "reach the user.")
    print("-" * 78)


def ieee_rows(rows: List[dict]):
    """Paste-ready table rows. Only stages with observations are emitted —
    an empty stage prints nothing rather than a blank row inviting a guess.
    """
    print()
    print("IEEE table rows (tab-separated: Stage / n / Mean / Median / SD / "
          "p95 / Max, ms)")
    print()
    by_path = defaultdict(list)
    for row in rows:
        by_path[row["path"]].append(row)
    for path in sorted(by_path):
        print(f"# path: {path}")
        for column, label in STAGE_COLUMNS:
            stats = describe(_floats(by_path[path], column))
            if not stats:
                continue
            sd = "n/a" if math.isnan(stats["sd"]) else f"{stats['sd']:.1f}"
            print(f"{label}\t{stats['n']}\t{stats['mean']:.1f}\t"
                  f"{stats['median']:.1f}\t{sd}\t{stats['p95']:.1f}\t"
                  f"{stats['max']:.1f}")
        print()


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("csv", nargs="+", help="raw latency CSV file(s)")
    parser.add_argument("--ieee", action="store_true",
                        help="also print paste-ready IEEE table rows")
    args = parser.parse_args()

    rows = load(args.csv)
    report(rows)
    if args.ieee:
        ieee_rows(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
