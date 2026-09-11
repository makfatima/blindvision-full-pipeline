"""
Real training run for the hybrid (public-dataset) approach.

Run this on a machine/Colab session with a GPU. It is NOT run in this
sandbox — no GPU, and no network access to image-dataset hosts here.

    python train_hybrid.py --data data_hybrid.yaml --epochs 60 --imgsz 640

Ultralytics will write real artifacts to <project>/<name>/, including:
  - weights/best.pt, weights/last.pt   <- the actual trained checkpoint
  - args.yaml                          <- exact hyperparameters used
  - results.csv                        <- per-epoch metrics
  - confusion_matrix.png / .csv-equivalent data in results

Once you have those, send me <project>/<name>/ (or at least args.yaml,
results.csv, and best.pt) and I'll wire the REAL numbers into the manuscript
and into tools/verify_artifacts.py / models/YOLO_Weights__Manifest.json —
I won't estimate or invent them.

SURVIVING A COLAB DISCONNECT:
Colab's /content/ is wiped on any session loss (quota cutoff, idle timeout,
crash). To survive that, point --project at a mounted Google Drive folder
instead of the default local runs/ dir — Ultralytics writes weights/last.pt
after EVERY epoch, so whatever epoch completed before a disconnect is
already safe on Drive, not lost:

    from google.colab import drive
    drive.mount('/content/drive')

    python train_hybrid.py --data data_hybrid.yaml --epochs 80 \
        --project /content/drive/MyDrive/blindvision_runs --name blindvision_hybrid

If a disconnect happens mid-run, reconnect, remount Drive, then RESUME
instead of restarting from epoch 0 (this continues from last.pt with the
same optimizer state, not just re-initializing from the base checkpoint):

    python train_hybrid.py --resume /content/drive/MyDrive/blindvision_runs/blindvision_hybrid/weights/last.pt
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
    ap.add_argument("--project", default=None, help="output dir root, e.g. a mounted Drive path to survive disconnects")
    ap.add_argument("--name", default="blindvision_hybrid")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--resume", default=None, help="path to a last.pt to resume an interrupted run from")
    args = ap.parse_args()

    if args.resume:
        model = YOLO(args.resume)
        model.train(resume=True)
    else:
        model = YOLO(args.weights)
        model.train(
            data=args.data,
            epochs=args.epochs,
            imgsz=args.imgsz,
            batch=args.batch,
            device=args.device,
            seed=args.seed,
            project=args.project,
            name=args.name,
            exist_ok=False,
        )
    metrics = model.val()
    print("Validation metrics:", metrics.results_dict)


if __name__ == "__main__":
    main()
