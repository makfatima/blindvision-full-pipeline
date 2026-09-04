"""
Real training run for the hybrid (public-dataset) approach.

Run this on a machine/Colab session with a GPU. It is NOT run in this
sandbox — no GPU, and no network access to image-dataset hosts here.

    python train_hybrid.py --data data_hybrid.yaml --epochs 60 --imgsz 640

Ultralytics will write real artifacts to runs/detect/<name>/, including:
  - weights/best.pt, weights/last.pt   <- the actual trained checkpoint
  - args.yaml                          <- exact hyperparameters used
  - results.csv                        <- per-epoch metrics
  - confusion_matrix.png / .csv-equivalent data in results

Once you have those, send me runs/detect/<name>/ (or at least args.yaml,
results.csv, and best.pt) and I'll wire the REAL numbers into the manuscript
and into tools/verify_artifacts.py / models/YOLO_Weights__Manifest.json —
I won't estimate or invent them.
"""
import argparse

from ultralytics import YOLO


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data_hybrid.yaml")
    ap.add_argument("--weights", default="yolov8n.pt", help="starting checkpoint (stock COCO pretrained)")
    ap.add_argument("--epochs", type=int, default=60)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--device", default=0)
    ap.add_argument("--name", default="blindvision_hybrid")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    model = YOLO(args.weights)
    model.train(
        data=args.data,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        seed=args.seed,
        name=args.name,
        exist_ok=False,
    )
    metrics = model.val()
    print("Validation metrics:", metrics.results_dict)


if __name__ == "__main__":
    main()
