# DO NOT MERGE without reading this

444 real images + real YOLO-format `stairs` labels (class 0), fetched from
`github.com/MadhanRavuru/StaircaseDetection`.

## Why this is quarantined instead of just being in `data/`

The images are **2D architectural floor-plan drawings** (sourced from the
Cubicasa5k dataset — top-down blueprint views with a stairs *symbol/icon*),
not photographs of physical staircases from a walking pedestrian's
eye-level. BlindVision's camera sees the real world at eye/chest height, not
blueprints.

Training on this alongside real-world door/pole/COCO images risks the model
learning to recognize a stairs *icon on a floor plan*, which won't transfer
to a real staircase — the domain gap is severe (line-drawing vs. photograph,
top-down vs. eye-level). This could make stairs detection worse, not better,
and if this were merged in silently it would be exactly the kind of
undisclosed-mismatch problem the rest of this project has been trying to
avoid.

## Options, if you still want to use it

- **Don't merge it.** Train on the 7 COCO classes + door now, leave stairs
  out of this run, disclose that as the scope in the manuscript, and source
  real photographic stairs images later (Roboflow links in
  `../CLASS_SOURCE_MAP.md`) before adding the stairs class.
- **Use it only as a last resort with a strong caveat**, and say so
  explicitly in the manuscript's Limitations section if you do — something
  like "the stairs class was trained on floor-plan schematic imagery rather
  than photographic data due to public dataset availability, which may limit
  real-world detection performance." Don't let this get folded into the
  same "public real-world data" description as the COCO/door subsets — it
  isn't the same kind of data and shouldn't be described as if it were.
- **Best option**: pull the Roboflow "Stairs_Detection" (601 real photos) or
  "Stair Detection Dataset" (1,809 real photos) sets — both real-world
  photographic stairs images — from `../CLASS_SOURCE_MAP.md` instead.

This folder is intentionally named so it can't be accidentally globbed into
`data/hybrid_dataset/` by a careless merge script.

License note: the source repo (MadhanRavuru/StaircaseDetection) has no
LICENSE file either — same caveat as the door subset, confirm reuse terms
before publishing.
