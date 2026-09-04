"""
Verify recovered artifacts against what the manuscript claims.

This does not create anything. It reads artifacts you have recovered and
checks them against the numbers already in the paper, so that every C1 row
is settled by a file rather than by memory.

The useful thing most teams do not know: a YOLOv8 `.pt` checkpoint carries
its own training arguments. If `best.pt` survived but `args.yaml` did not,
the hyperparameters, epochs, image size, batch size, seed and augmentation
settings are still recoverable from inside the weights file. That single fact
settles several C1 rows on its own.

    python3 tools/verify_artifacts.py --weights runs/detect/train/weights/best.pt
    python3 tools/verify_artifacts.py --data data.yaml --expect-train 5600 \
        --expect-val 700 --expect-test 700
    python3 tools/verify_artifacts.py --args runs/detect/train/args.yaml

Whatever is absent is reported as absent. Nothing is filled in from the
manuscript -- the point of the exercise is to find out whether the artifact
agrees with the paper, which is impossible if the artifact is inferred from
the paper.
"""

import argparse
import hashlib
import json
import os
import sys
from collections import Counter

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}


def sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def human(size: int) -> str:
    for unit in ("B", "KiB", "MiB", "GiB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TiB"


# --------------------------------------------------------------------------
# Weights
# --------------------------------------------------------------------------

def inspect_weights(path: str):
    print("=" * 78)
    print("WEIGHTS")
    print("=" * 78)
    if not os.path.exists(path):
        print(f"  NOT FOUND: {path}")
        print("  Without the weights, no reported detection number can be")
        print("  reproduced or verified. See docs/ARTIFACT_RECOVERY.md.")
        return

    stat = os.stat(path)
    print(f"  Path:     {path}")
    print(f"  Size:     {human(stat.st_size)}")
    print(f"  SHA-256:  {sha256(path)}")
    print(f"  Modified: {_iso(stat.st_mtime)}")
    print()
    print("  Record the SHA-256 in TRACEABILITY.md. It is what ties every")
    print("  detection table to this specific file.")
    print()

    try:
        import torch
    except ImportError:
        print("  torch not installed here -- run this on the Pi or a machine")
        print("  with the training environment to read inside the checkpoint.")
        return

    try:
        ckpt = torch.load(path, map_location="cpu", weights_only=False)
    except Exception as exc:
        print(f"  Could not open the checkpoint: {exc}")
        return

    if not isinstance(ckpt, dict):
        print("  Checkpoint is not a dict; nothing further to read.")
        return

    print("  -- Recovered from inside the checkpoint --")
    for key in ("date", "version", "epoch", "best_fitness"):
        if key in ckpt:
            print(f"  {key}: {ckpt[key]}")

    model = ckpt.get("model")
    names = getattr(model, "names", None) if model is not None else None
    if names:
        print(f"  Classes ({len(names)}):")
        items = names.items() if isinstance(names, dict) else enumerate(names)
        for idx, name in items:
            print(f"    {idx}: {name}")
        print()
        print("  Compare this list against the manuscript's class list. The")
        print("  measurement requirement's C1 finding was partly that the public repository used")
        print("  a different class list from the one the paper describes.")
    print()

    args = ckpt.get("train_args") or ckpt.get("args")
    if args:
        print("  -- Training arguments (this settles the hyperparameter row) --")
        if not isinstance(args, dict):
            args = vars(args)
        interesting = ["model", "data", "epochs", "batch", "imgsz", "seed",
                       "optimizer", "lr0", "lrf", "momentum", "weight_decay",
                       "warmup_epochs", "patience", "device", "workers",
                       "pretrained", "hsv_h", "hsv_s", "hsv_v", "degrees",
                       "translate", "scale", "shear", "perspective",
                       "flipud", "fliplr", "mosaic", "mixup", "copy_paste"]
        for key in interesting:
            if key in args:
                print(f"    {key}: {args[key]}")
        print()
        print("  Everything above came out of the weights file. Paste it into")
        print("  the manuscript's training-configuration paragraph verbatim.")
    else:
        print("  No training arguments embedded. Look for args.yaml next to")
        print("  the weights, in the same runs/ directory.")


# --------------------------------------------------------------------------
# Dataset
# --------------------------------------------------------------------------

def _load_yaml(path: str):
    try:
        import yaml
    except ImportError:
        print("  PyYAML not installed; falling back to a naive parse.")
        return _naive_yaml(path)
    with open(path) as fh:
        return yaml.safe_load(fh)


def _naive_yaml(path: str):
    data = {}
    with open(path) as fh:
        for line in fh:
            if ":" in line and not line.strip().startswith("#"):
                key, _, value = line.partition(":")
                data[key.strip()] = value.strip()
    return data


def _count_split(root: str, split_path: str):
    """Count images and label files for one split, wherever it points."""
    candidate = split_path
    if not os.path.isabs(candidate):
        candidate = os.path.join(root, candidate)
    candidate = os.path.normpath(candidate)
    if not os.path.exists(candidate):
        return None

    images = 0
    labels = 0
    annotations = Counter()
    for dirpath, _, filenames in os.walk(candidate):
        for name in filenames:
            ext = os.path.splitext(name)[1].lower()
            if ext in IMAGE_EXTS:
                images += 1
    label_root = candidate.replace("/images", "/labels")
    if os.path.exists(label_root):
        for dirpath, _, filenames in os.walk(label_root):
            for name in filenames:
                if name.endswith(".txt"):
                    labels += 1
                    with open(os.path.join(dirpath, name)) as fh:
                        for line in fh:
                            parts = line.split()
                            if parts:
                                annotations[parts[0]] += 1
    return {"path": candidate, "images": images, "labels": labels,
            "annotations": annotations}


def inspect_data(path: str, expected: dict):
    print("=" * 78)
    print("DATASET")
    print("=" * 78)
    if not os.path.exists(path):
        print(f"  NOT FOUND: {path}")
        print("  Without the dataset configuration, the split sizes in the")
        print("  manuscript's dataset table cannot be checked.")
        return

    print(f"  Path:    {path}")
    print(f"  SHA-256: {sha256(path)}")
    print()

    # The release may contain only the split-count CSV when the original
    # image/label dataset is not distributed. Accept that evidence format
    # explicitly instead of treating it as a malformed YAML file.
    if path.lower().endswith('.csv'):
        import csv
        with open(path, newline='', encoding='utf-8-sig') as fh:
            rows = list(csv.DictReader(fh))
        if not rows or not {'Split', 'Images'}.issubset(rows[0].keys()):
            print("  ERROR: CSV must contain Split and Images columns.")
            return
        for row in rows:
            split = row['Split'].strip().lower()
            images = int(row['Images'])
            ann = row.get('Annotated Objects', '—')
            print(f"  {split}: {images} images, annotated objects: {ann}")
            want = expected.get(split)
            if want is not None:
                if images == want:
                    print(f"        matches the expected {want}")
                else:
                    print(f"        !! expected {want}, found {images}")
        print("  These are released aggregate split counts; the complete image/label")
        print("  directories are not included in this release.")
        return

    config = _load_yaml(path) or {}
    if not isinstance(config, dict):
        print("  ERROR: --data must point to a YAML dataset configuration or")
        print("  to the released split-count CSV.")
        return
    root = config.get("path") or os.path.dirname(os.path.abspath(path))
    names = config.get("names")
    if names:
        count = len(names) if not isinstance(names, str) else "?"
        print(f"  Classes declared: {count}")
        if isinstance(names, dict):
            for idx, name in names.items():
                print(f"    {idx}: {name}")
        elif isinstance(names, list):
            for idx, name in enumerate(names):
                print(f"    {idx}: {name}")
        print()

    any_counted = False
    for split in ("train", "val", "test"):
        split_path = config.get(split)
        if not split_path:
            print(f"  {split}: not declared in the YAML")
            continue
        result = _count_split(root, str(split_path))
        if result is None:
            print(f"  {split}: declared as '{split_path}' but that path does not exist here")
            continue
        any_counted = True
        print(f"  {split}: {result['images']} images, {result['labels']} label files ({result['path']})")
        want = expected.get(split)
        if want is not None:
            if result["images"] == want:
                print(f"        matches the expected {want}")
            else:
                print(f"        !! expected {want}, found {result['images']}")
        if result["annotations"]:
            total = sum(result["annotations"].values())
            print(f"        {total} annotations across {len(result['annotations'])} classes")
            for cls, n in sorted(result["annotations"].items(), key=lambda kv: int(kv[0])):
                print(f"          class {cls}: {n}")
    print()
    if any_counted:
        print("  These counts came from the dataset on disk, not from the manuscript.")
    else:
        print("  The YAML was readable but no split directory was found here.")
        print("  Run this on the machine that holds the dataset.")


# --------------------------------------------------------------------------
# args.yaml
# --------------------------------------------------------------------------

def inspect_args(path: str):
    print("=" * 78)
    print("TRAINING ARGUMENTS")
    print("=" * 78)
    if not os.path.exists(path):
        print(f"  NOT FOUND: {path}")
        print("  If best.pt survived, try --weights instead: the checkpoint")
        print("  carries a copy of these arguments.")
        return
    print(f"  Path:    {path}")
    print(f"  SHA-256: {sha256(path)}")
    print()
    config = _load_yaml(path) or {}
    for key in sorted(config):
        print(f"    {key}: {config[key]}")
    print()
    print("  This is the training-configuration paragraph, settled.")


def _iso(timestamp: float) -> str:
    import datetime
    return datetime.datetime.fromtimestamp(
        timestamp, datetime.timezone.utc).isoformat()


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--weights")
    parser.add_argument("--data")
    parser.add_argument("--args", dest="args_yaml")
    parser.add_argument("--expect-train", type=int)
    parser.add_argument("--expect-val", type=int)
    parser.add_argument("--expect-test", type=int)
    opts = parser.parse_args()

    if not any([opts.weights, opts.data, opts.args_yaml]):
        parser.error("give at least one of --weights, --data, --args")

    if opts.weights:
        inspect_weights(opts.weights)
        print()
    if opts.data:
        inspect_data(opts.data, {
            "train": opts.expect_train,
            "val": opts.expect_val,
            "test": opts.expect_test,
        })
        print()
    if opts.args_yaml:
        inspect_args(opts.args_yaml)
    return 0


if __name__ == "__main__":
    sys.exit(main())
