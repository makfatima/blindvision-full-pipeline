"""
Build a YOLO-format subset of COCO for the 7 BlindVision classes that COCO
actually covers (person, chair, backpack, laptop, bottle, bicycle, vehicle).

This is a REAL data-preparation script meant to be run by the user on a
machine with disk space (~20GB for full COCO train2017+val2017) and network
access to the COCO S3 bucket. It is not run here — this sandbox has no access
to image-dataset hosts.

What it does:
  1. Uses pycocotools + the COCO annotation JSON (downloaded by `ultralytics`
     on first use, or manually from https://cocodataset.org/#download) to
     find every image containing at least one instance of a target class.
  2. Copies those images into data/coco_subset/images/{train,val}/.
  3. Writes YOLO-format label .txt files with BOXES REMAPPED to BlindVision's
     class ids (not COCO's), so they line up with door/pole/stairs once those
     are added from another source.
  4. Emits a manifest CSV of exactly which COCO image ids and license info
     went in, so provenance is traceable.

Usage:
    python prepare_coco_subset.py --coco-root /path/to/coco --out ../../data/coco_subset

Requires: pycocotools, tqdm, pillow  (pip install pycocotools tqdm pillow)
"""
import argparse
import csv
import json
import shutil
from pathlib import Path

# COCO category name -> BlindVision class id (see CLASS_SOURCE_MAP.md)
COCO_TO_BV = {
    "person": 0,
    "chair": 2,
    "backpack": 3,
    "laptop": 4,
    "bottle": 5,
    "car": 7,
    "truck": 7,
    "bus": 7,
    "bicycle": 8,
}


def build_split(coco_root: Path, split: str, out_root: Path, manifest_rows: list):
    ann_path = coco_root / "annotations" / f"instances_{split}2017.json"
    img_dir = coco_root / f"{split}2017"
    if not ann_path.exists():
        print(f"[skip] {ann_path} not found — did you download COCO {split}2017 annotations?")
        return

    from pycocotools.coco import COCO  # imported lazily so --help works without it

    coco = COCO(str(ann_path))
    cat_ids = coco.getCatIds(catNms=list(set(COCO_TO_BV.keys())))
    catid_to_name = {c["id"]: c["name"] for c in coco.loadCats(coco.getCatIds())}

    img_ids = set()
    for cid in cat_ids:
        img_ids.update(coco.getImgIds(catIds=[cid]))

    out_img_dir = out_root / "images" / split
    out_lbl_dir = out_root / "labels" / split
    out_img_dir.mkdir(parents=True, exist_ok=True)
    out_lbl_dir.mkdir(parents=True, exist_ok=True)

    for img_id in sorted(img_ids):
        info = coco.loadImgs(img_id)[0]
        src = img_dir / info["file_name"]
        if not src.exists():
            continue
        dst = out_img_dir / info["file_name"]
        shutil.copy2(src, dst)

        w, h = info["width"], info["height"]
        ann_ids = coco.getAnnIds(imgIds=img_id, catIds=cat_ids, iscrowd=False)
        anns = coco.loadAnns(ann_ids)
        lines = []
        for a in anns:
            name = catid_to_name[a["category_id"]]
            bv_cls = COCO_TO_BV.get(name)
            if bv_cls is None:
                continue
            x, y, bw, bh = a["bbox"]  # COCO: top-left x,y,width,height (pixels)
            cx = (x + bw / 2) / w
            cy = (y + bh / 2) / h
            nw = bw / w
            nh = bh / h
            lines.append(f"{bv_cls} {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}")

        (out_lbl_dir / (Path(info["file_name"]).stem + ".txt")).write_text(
            "\n".join(lines) + ("\n" if lines else "")
        )
        manifest_rows.append(
            {
                "split": split,
                "coco_image_id": img_id,
                "file_name": info["file_name"],
                "coco_license_id": info.get("license"),
                "n_boxes": len(lines),
            }
        )

    print(f"[{split}] wrote {len(img_ids)} images, {sum(m['n_boxes'] for m in manifest_rows if m['split']==split)} boxes")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--coco-root", required=True, help="Path containing annotations/ and train2017/ val2017/")
    ap.add_argument("--out", default="../../data/coco_subset")
    args = ap.parse_args()

    coco_root = Path(args.coco_root)
    out_root = Path(args.out)
    manifest_rows = []

    for split in ("train", "val"):
        build_split(coco_root, split, out_root, manifest_rows)

    manifest_path = out_root / "COCO_SUBSET_MANIFEST.csv"
    with open(manifest_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["split", "coco_image_id", "file_name", "coco_license_id", "n_boxes"])
        w.writeheader()
        w.writerows(manifest_rows)
    print(f"Wrote manifest: {manifest_path} ({len(manifest_rows)} images)")
    print("NOTE: this covers person/chair/backpack/laptop/bottle/vehicle/bicycle only.")
    print("door/pole/stairs are NOT in COCO — see CLASS_SOURCE_MAP.md.")


if __name__ == "__main__":
    main()
