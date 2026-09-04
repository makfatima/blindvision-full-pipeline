# Door subset — real data, actually fetched (not a placeholder)

## What this is

386 real images (580 door bounding boxes) filtered out of the public
**DoorDetect Dataset** (github.com/MiguelARD/DoorDetect-Dataset, commit
cloned 2026-09-03), keeping only instances of its `door` class (dropping
`handle`, `cabinet door`, `refrigerator door`) and remapping the class id
from DoorDetect's `0` to BlindVision's `1` (per `data/Class_Definition.csv`).

Source images are themselves drawn from Open Images V4 and MCIndoor20000
(per the DoorDetect README) — this is a filtered re-export of that dataset,
not new photography.

`DOOR_SUBSET_MANIFEST.csv` lists every image filename and its door-box count
so this is traceable back to source.

## License / citation — check before publishing

The DoorDetect-Dataset GitHub repo does **not** include a LICENSE file. Its
README asks that its paper be cited if it helps your research:

> Arduengo, M., Torras, C. & Sentis, L. Robust and adaptive door operation
> with a mobile robot. *Intelligent Service Robotics* (2021).
> https://doi.org/10.1007/s11370-021-00366-7

Because there's no explicit license, and the underlying images come from
Open Images (CC-BY 2.0 per-image, sometimes with individual attribution
requirements) and MCIndoor20000 (has its own license terms), you or your
supervisor should confirm the reuse/redistribution terms are acceptable for
your thesis/publication before shipping this subset in a public release —
I filtered and copied the files, but I can't clear licensing on your behalf.
Citing the DoorDetect paper in your manuscript's dataset description covers
the attribution the authors explicitly asked for.

## What's still missing

Pole and stairs still need to come from Roboflow Universe (see
`../CLASS_SOURCE_MAP.md`) — Roboflow's domain isn't reachable from this
sandbox's network, so those weren't fetched here. The COCO subset for the
other 7 classes also wasn't fetched here for the same reason (COCO's image
host isn't in the sandbox's allowed domains) — `prepare_coco_subset.py` is
ready for you to run wherever you do have that access.
