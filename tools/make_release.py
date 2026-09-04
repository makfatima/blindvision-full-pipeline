"""
Assemble the C1 traceability release, and refuse to call it done early.

The audit lists ten items a release must contain. This script checks for all
ten, hashes what is present, and exits non-zero listing what is not. It will
not produce a "complete" release with gaps in it, because a release that
looks complete and is not is worse than an obviously partial one.

    python3 tools/make_release.py --check
    python3 tools/make_release.py --out release/ --tag v1.0.0-experimental

Paths are configured in `release_manifest.json` next to this script, or
passed on the command line. Anything not found is reported as not found --
nothing is substituted, and no stand-in file is ever written.
"""

import argparse
import datetime
import hashlib
import json
import os
import shutil
import sys

# The measurement requirement's ten required items. `required` marks the ones without which the
# release cannot support the manuscript's claims at all.
ITEMS = [
    ("weights", "Trained weights used for every reported result", True),
    ("dataset_yaml", "Dataset YAML / class configuration", True),
    ("split_counts", "Per-split image and annotation counts", True),
    ("train_script", "Training script", True),
    ("eval_script", "Validation and test scripts", True),
    ("train_args", "Hyperparameters, seed, epochs, image size, augmentation", True),
    ("pi_code", "Deployed Raspberry Pi code, as run", True),
    ("firmware", "ESP32 firmware image, as flashed", True),
    ("fusion_config", "Fusion configuration used in the 100 navigation trials", True),
    ("log_manifest", "Table to code to raw-log mapping", True),
]

DEFAULT_MANIFEST = {key: "" for key, _, _ in ITEMS}


def sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dir_digest(path: str):
    """Hash of a directory: every file's relative path and content, sorted, so
    the digest is stable across machines."""
    digest = hashlib.sha256()
    count = 0
    for dirpath, dirnames, filenames in os.walk(path):
        dirnames.sort()
        for name in sorted(filenames):
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, path)
            digest.update(rel.encode())
            with open(full, "rb") as fh:
                for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                    digest.update(chunk)
            count += 1
    return digest.hexdigest(), count


def load_manifest(path: str) -> dict:
    if os.path.exists(path):
        with open(path) as fh:
            return json.load(fh)
    return dict(DEFAULT_MANIFEST)


def check(manifest: dict):
    present, missing = [], []
    for key, label, required in ITEMS:
        location = (manifest.get(key) or "").strip()
        if not location:
            missing.append((key, label, "no path configured"))
            continue
        if not os.path.exists(location):
            missing.append((key, label, f"path does not exist: {location}"))
            continue
        if os.path.isdir(location):
            digest, count = dir_digest(location)
            present.append((key, label, location, digest, f"{count} files"))
        else:
            size = os.path.getsize(location)
            present.append((key, label, location, sha256(location),
                            f"{size} bytes"))
    return present, missing


def report(present, missing):
    print("=" * 78)
    print("C1 TRACEABILITY RELEASE — readiness check")
    print("=" * 78)
    print(f"Present: {len(present)} of {len(ITEMS)}")
    print()
    if present:
        for key, label, location, digest, extra in present:
            print(f"  [ok]      {label}")
            print(f"            {location}  ({extra})")
            print(f"            sha256 {digest}")
        print()
    if missing:
        print("MISSING — the release is not complete:")
        for key, label, why in missing:
            print(f"  [absent]  {label}")
            print(f"            {why}")
        print()
        print("None of these can be written from the manuscript. Each is a")
        print("record of something that already happened; see")
        print("docs/ARTIFACT_RECOVERY.md for where they usually survive.")
        print()
        print("If an item is genuinely unrecoverable, say so in the paper's")
        print("Code and Data Availability statement. An honest gap is")
        print("defensible; a missing artifact must not be represented as the source artifact.")
    else:
        print("All ten items present. The release can be tagged.")
    return len(missing)


def assemble(manifest, present, out_dir: str, tag: str):
    os.makedirs(out_dir, exist_ok=True)
    lines = [
        "# Release manifest",
        "",
        f"Tag: `{tag}`",
        f"Assembled (UTC): {datetime.datetime.now(datetime.timezone.utc).isoformat()}",
        "",
        "Every artifact below was copied from the path recorded here and",
        "hashed at assembly time. The hashes are what tie the manuscript's",
        "tables to these specific files.",
        "",
        "| Item | Source path | SHA-256 | Size |",
        "|---|---|---|---|",
    ]
    for key, label, location, digest, extra in present:
        target = os.path.join(out_dir, key)
        if os.path.isdir(location):
            shutil.copytree(location, target, dirs_exist_ok=True)
        else:
            os.makedirs(os.path.dirname(target) or ".", exist_ok=True)
            shutil.copy2(location, target + os.path.splitext(location)[1])
        lines.append(f"| {label} | `{location}` | `{digest}` | {extra} |")
    lines += ["", "## Not included", ""]
    included = {key for key, _, _, _, _ in present}
    for key, label, _ in ITEMS:
        if key not in included:
            lines.append(f"- **{label}** — not recovered.")
    lines += [
        "",
        "Anything listed as not recovered is a real gap. It has not been",
        ", and no substitute has been put in its place.",
        "",
    ]
    manifest_path = os.path.join(out_dir, "RELEASE_MANIFEST.md")
    with open(manifest_path, "w") as fh:
        fh.write("\n".join(lines))
    print(f"Wrote {manifest_path}")


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--manifest", default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "release_manifest.json"))
    parser.add_argument("--check", action="store_true",
                        help="report readiness and exit")
    parser.add_argument("--out", help="assemble the release here")
    parser.add_argument("--tag", default="UNTAGGED")
    parser.add_argument("--allow-incomplete", action="store_true",
                        help="assemble anyway, with the gaps listed in the "
                             "manifest")
    opts = parser.parse_args()

    manifest = load_manifest(opts.manifest)
    present, missing = check(manifest)
    n_missing = report(present, missing)

    if opts.out:
        if n_missing and not opts.allow_incomplete:
            print()
            print("Refusing to assemble an incomplete release. Pass")
            print("--allow-incomplete to build one anyway; the manifest will")
            print("name every gap.")
            return 1
        assemble(manifest, present, opts.out, opts.tag)

    return 1 if n_missing else 0


if __name__ == "__main__":
    sys.exit(main())
