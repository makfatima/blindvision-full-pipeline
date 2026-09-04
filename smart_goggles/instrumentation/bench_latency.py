"""
Four-camera end-to-end latency experiment.

Runs the real pipeline with all four camera streams active, the same model
and resolution as the navigation trials, and the stick link connected, and
writes one CSV row per hazard event. It measures; it does not model. If the
hardware is not there, it stops rather than producing a number.

What the run produces, per path and per camera bearing: n, mean, median, SD,
95th percentile, maximum for every stage and for end-to-end latency to
speech onset and to phrase completion; the dropped-frame rate under
four-stream load; dispatcher queue depth; aggregate and per-camera
throughput; and measured BLE round trips.

    # the real thing
    python3 bench_latency.py --reps 100 --out runs/latency_2026-08-04.csv
    python3 summarize.py runs/latency_2026-08-04.csv --ieee

`--reps` is per camera direction, matching the measurement requirement's requirement of at
least 100 repetitions per direction. The run continues until every bearing
has reached it, so a camera that is producing nothing will keep the run open
rather than letting the others finish and hide it.
"""

import argparse
import asyncio
import logging
import os
import sys
import threading
import time
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
from instrumentation.timing import LatencyRecorder, VISION_PATH  # noqa: E402

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("blindvision.bench")

def run_experiment(args) -> int:
    from camera import CameraManager, YoloDetector  # noqa: F401
    from ble import run_stick_link
    from main import BlindVisionSystem

    if not os.path.exists(config.YOLO_MODEL_PATH):
        logger.error("Model weights not found at %s. A latency figure measured "
                     "with different weights than the navigation trials used "
                     "is not the same experiment.", config.YOLO_MODEL_PATH)
        return 2

    recorder = LatencyRecorder(csv_path=args.out)
    device_map = {
        "front": args.camera_front,
        "right": args.camera_right,
        "rear": args.camera_rear,
        "left": args.camera_left,
    }
    system = BlindVisionSystem(device_map, recorder=recorder)

    logger.info("Starting four-camera latency run: target %d events per "
                "bearing, writing to %s", args.reps, args.out)
    logger.info("Walk the hazard course now. Every announced alert becomes a "
                "row; suppressed ones are recorded too and flagged.")

    stop = threading.Event()

    def progress():
        while not stop.is_set():
            per_bearing = Counter(
                e.bearing for e in recorder.events
                if e.path == VISION_PATH and e.bearing)
            stick_n = sum(1 for e in recorder.events if e.path != VISION_PATH)
            done = all(per_bearing.get(b, 0) >= args.reps for b in device_map)
            logger.info("progress: %s | stick=%d | elapsed=%.0fs",
                        dict(per_bearing), stick_n, recorder.elapsed_s)
            if done:
                logger.info("Target reached on every bearing.")
                stop.set()
                return
            if args.max_seconds and recorder.elapsed_s > args.max_seconds:
                logger.warning("Time limit reached before every bearing hit "
                               "%d. The run is SHORT -- report the actual n "
                               "per bearing, do not round it up.", args.reps)
                stop.set()
                return
            stop.wait(10.0)

    threading.Thread(target=progress, daemon=True).start()

    async def main_async():
        system.cameras.start_all()
        for bearing in system.cameras.streams:
            threading.Thread(target=system._camera_worker, args=(bearing,),
                             daemon=True, name=f"detect-{bearing}").start()
        threading.Thread(target=system._fusion_loop, daemon=True,
                         name="fusion").start()

        link_task = asyncio.create_task(
            run_stick_link(system.stick_link, system._on_stick_packet))

        # Periodic BLE round-trip samples across the whole run, not a burst
        # at the start: the connection interval and channel conditions change
        # as the user moves.
        async def ping_loop():
            while not stop.is_set():
                await system.stick_link.measure_rtt()
                await asyncio.sleep(args.ping_interval_s)

        ping_task = asyncio.create_task(ping_loop())
        while not stop.is_set():
            await asyncio.sleep(0.5)
        for task in (link_task, ping_task):
            task.cancel()

    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("Interrupted -- rows already written are intact.")
    finally:
        stop.set()
        system.cameras.stop_all()
        drops = system.cameras.drop_stats()
        recorder.close()

    print()
    print("Run complete. Raw rows:", args.out)
    print("Per-stream capture/supersede counts (dropped-frame rate under load):")
    for bearing, stats in drops.items():
        captured = stats["captured"]
        superseded = stats["superseded"]
        rate = (superseded / captured * 100.0) if captured else 0.0
        thruput = captured / recorder.elapsed_s if recorder.elapsed_s else 0.0
        print(f"  {bearing:<8s} captured={captured:<7d} superseded={superseded:<7d} "
              f"({rate:.1f}%)  {thruput:.2f} fps")
    total = sum(s["captured"] for s in drops.values())
    if recorder.elapsed_s:
        print(f"  AGGREGATE across four streams: "
              f"{total / recorder.elapsed_s:.2f} fps")
    print()
    print(f"Now run:  python3 summarize.py {args.out} --ieee")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reps", type=int, default=100,
                        help="target events per camera direction (default 100)")
    parser.add_argument("--out", default="runs/latency.csv")
    parser.add_argument("--max-seconds", type=float, default=0,
                        help="stop after this long even if short (0 = no limit)")
    parser.add_argument("--ping-interval-s", type=float, default=5.0)
    parser.add_argument("--camera-front", type=int, default=0)
    parser.add_argument("--camera-right", type=int, default=1)
    parser.add_argument("--camera-rear", type=int, default=2)
    parser.add_argument("--camera-left", type=int, default=3)
    args = parser.parse_args()

    return run_experiment(args)


if __name__ == "__main__":
    sys.exit(main())
