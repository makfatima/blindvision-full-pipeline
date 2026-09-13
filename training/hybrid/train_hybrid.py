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

AUTOMATIC GITHUB CHECKPOINTING (works on Kaggle too, no manual "Save Version"
needed): pass --checkpoint-repo/--checkpoint-token/--checkpoint-every to push
weights/last.pt, args.yaml, and results.csv to a GitHub repo every N epochs,
on top of whatever --project already saves locally:

    python train_hybrid.py --data data_hybrid.yaml --epochs 80 \
        --project /kaggle/working/runs --name blindvision_hybrid \
        --checkpoint-repo makfatima/blindvision-checkpoints \
        --checkpoint-token ghp_xxx --checkpoint-every 10

The target repo must already exist (create it empty on GitHub first). Each
push overwrites the same file paths in that repo, so it's always just the
latest checkpoint, not a growing history.

DATASET PATH: data_hybrid.yaml's `path:` is a relative path that only
resolves correctly if the dataset happens to sit at that exact relative
location, which it usually won't on a fresh clone (the dataset now lives in
a separate repo, e.g. blindvision-dataset-10class). Pass --dataset-root to
have this script rewrite the yaml's path automatically before training or
validating, instead of hand-editing the yaml every session:

    python train_hybrid.py --data data_hybrid.yaml --dataset-root /kaggle/working/BlindVision_data ...
"""
import argparse
import os
import re
import shutil
import subprocess


def push_checkpoint(save_dir, repo, token, tag=""):
    """Copy weights/last.pt + args.yaml + results.csv from save_dir into a
    freshly-cloned copy of `repo` and push. Best-effort: prints and returns
    on any failure rather than crashing the training run."""
    try:
        workdir = "/tmp/_checkpoint_push"
        shutil.rmtree(workdir, ignore_errors=True)
        subprocess.run(
            ["git", "clone", "--depth", "1", f"https://{token}@github.com/{repo}.git", workdir],
            check=True, capture_output=True, text=True,
        )
        for fname in ("weights/last.pt", "args.yaml", "results.csv"):
            src = os.path.join(save_dir, fname)
            if os.path.exists(src):
                dst = os.path.join(workdir, os.path.basename(fname))
                shutil.copy2(src, dst)
        subprocess.run(["git", "-C", workdir, "add", "-A"], check=True)
        subprocess.run(
            ["git", "-C", workdir, "-c", "user.email=checkpoint@bot.local",
             "-c", "user.name=checkpoint-bot", "commit", "-m", f"checkpoint{tag}"],
            check=False, capture_output=True, text=True,  # ok if nothing changed
        )
        subprocess.run(
            ["git", "-C", workdir, "push", f"https://{token}@github.com/{repo}.git", "HEAD:main"],
            check=True, capture_output=True, text=True,
        )
        print(f"[checkpoint] pushed to {repo}{tag}")
    except Exception as e:
        print(f"[checkpoint] push failed (continuing training): {e}")


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
    ap.add_argument("--checkpoint-repo", default=None, help="owner/repo to push periodic checkpoints to")
    ap.add_argument("--checkpoint-token", default=None, help="GitHub token with repo scope for checkpoint pushes")
    ap.add_argument("--checkpoint-every", type=int, default=10, help="push a checkpoint every N epochs")
    ap.add_argument("--dataset-root", default=None, help="absolute path to the dataset folder (images/labels); rewrites --data's yaml path: line automatically")
    args = ap.parse_args()

    if args.dataset_root:
        content = open(args.data).read()
        content = re.sub(r"path:.*", f"path: {args.dataset_root}", content)
        open(args.data, "w").write(content)
        print(f"[dataset-root] rewrote {args.data} path: -> {args.dataset_root}")

    if args.resume:
        model = YOLO(args.resume)
    else:
        model = YOLO(args.weights)

    if args.checkpoint_repo and args.checkpoint_token:
        def on_epoch_end(trainer):
            ep = trainer.epoch + 1
            if ep % args.checkpoint_every == 0:
                push_checkpoint(str(trainer.save_dir), args.checkpoint_repo, args.checkpoint_token, tag=f" (epoch {ep})")
        model.add_callback("on_fit_epoch_end", on_epoch_end)

    if args.resume:
        model.train(resume=True)
    else:
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

    # final push regardless of --checkpoint-every, so the finished run is captured too
    if args.checkpoint_repo and args.checkpoint_token:
        push_checkpoint(str(model.trainer.save_dir), args.checkpoint_repo, args.checkpoint_token, tag=" (final)")

    metrics = model.val(data=args.data)
    print("Validation metrics:", metrics.results_dict)


if __name__ == "__main__":
    main()
