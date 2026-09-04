"""
Merge a downloaded single-class Roboflow dataset (e.g. the pole sets) into
BlindVision's hybrid_dataset tree, remapping its class id to the correct
BlindVision id along the way.

Usage:
    python merge_single_class_download.py \
        --src /path/to/PoleDetection-1 \
        --src-class-id 0 \
        --bv-class-id 6 \
        --out ../data/hybrid_dataset

`--src` must contain train/images, train/labels, valid/images, valid/labels
(the standard Roboflow YOLOv8 export layout). If your download used
different split folder names (e.g. "test" instead of "valid"), pass
--src-train-dir / --src-val-dir to override.

Every label line's first token is checked against --src-class-id; lines that
don't match are DROPPED (so a multi-class export gets safely filtered down
to just the one class you want), and matching lines are rewritten with
--bv-class-id. Filenames are prefixed with the source dataset name to avoid
collisions when merging multiple sources into the same folder.
"""
import argparse
import shutil
from pathlib import Path


def merge_split(src_img_dir: Path, src_lbl_dir: Path, out_img_dir: Path, out_lbl_dir: Path,
                 src_class_id: str, bv_class_id: str, prefix: str):
    out_img_dir.mkdir(parents=True, exist_ok=True)
    out_lbl_dir.mkdir(parents=True, exist_ok=True)

    n_images = 0
    n_boxes = 0
    for lbl_file in sorted(src_lbl_dir.glob("*.txt")):
        lines = lbl_file.read_text().strip().splitlines()
        kept = []
        for line in lines:
            parts = line.split()
            if not parts:
                continue
            if parts[0] == src_class_id:
                parts[0] = bv_class_id
                kept.append(" ".join(parts))
        if not kept:
            continue  # skip images with no instance of the target class

        img_matches = list(src_img_dir.glob(lbl_file.stem + ".*"))
        img_matches = [p for p in img_matches if p.suffix.lower() in (".jpg", ".jpeg", ".png")]
        if not img_matches:
            continue
        img_src = img_matches[0]

        new_stem = f"{prefix}_{lbl_file.stem}"
        shutil.copy2(img_src, out_img_dir / (new_stem + img_src.suffix))
        (out_lbl_dir / (new_stem + ".txt")).write_text("\n".join(kept) + "\n")
        n_images += 1
        n_boxes += len(kept)

    return n_images, n_boxes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="Path to the extracted Roboflow download")
    ap.add_argument("--src-class-id", required=True, help="Class id for the target class IN THE SOURCE dataset (check its data.yaml)")
    ap.add_argument("--bv-class-id", required=True, help="BlindVision class id to remap to (e.g. 6 for pole, 1 for door)")
    ap.add_argument("--out", default="../data/hybrid_dataset")
    ap.add_argument("--src-train-dir", default="train")
    ap.add_argument("--src-val-dir", default="valid")
    ap.add_argument("--prefix", default=None, help="Filename prefix to avoid collisions (default: source folder name)")
    args = ap.parse_args()

    src = Path(args.src)
    out = Path(args.out)
    prefix = args.prefix or src.name.replace(" ", "_")

    total_img, total_box = 0, 0
    for split, src_sub, out_sub in (
        ("train", args.src_train_dir, "train"),
        ("val", args.src_val_dir, "val"),
    ):
        src_img_dir = src / src_sub / "images"
        src_lbl_dir = src / src_sub / "labels"
        if not src_img_dir.exists():
            print(f"[skip] {src_img_dir} not found")
            continue
        n_i, n_b = merge_split(
            src_img_dir, src_lbl_dir,
            out / "images" / out_sub, out / "labels" / out_sub,
            args.src_class_id, args.bv_class_id, prefix,
        )
        print(f"[{split}] merged {n_i} images, {n_b} boxes (class {args.src_class_id} -> {args.bv_class_id})")
        total_img += n_i
        total_box += n_b

    print(f"Total: {total_img} images, {total_box} boxes merged into {out}")


if __name__ == "__main__":
    main()
