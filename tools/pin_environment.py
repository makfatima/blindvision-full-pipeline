"""
Capture the environment this device is actually running.

the manuscript software table lists a software environment. Some rows are cited to a
`requirements.txt`; others are marked "confirmed by authors", which is a
claim with nothing behind it. This script replaces the claim with a
measurement: run it ON the device, and it reports what is installed there.

It reads; it never guesses. A package that is not installed is reported as
absent rather than filled in from the manuscript.

    python3 tools/pin_environment.py                 # print to stdout
    python3 tools/pin_environment.py --out ENVIRONMENT.md
    python3 tools/pin_environment.py --requirements requirements.lock.txt

The `--requirements` output is a fully pinned `==` file, so the environment
can be rebuilt exactly rather than approximately.
"""

import argparse
import datetime
import os
import platform
import subprocess
import sys

# Packages the manuscript's software table names, so their presence or
# absence is reported explicitly rather than silently omitted.
PACKAGES_OF_INTEREST = [
    "torch", "torchvision", "ultralytics", "opencv-python", "numpy",
    "pyttsx3", "bleak", "pyserial", "fastapi", "uvicorn", "pillow",
    "pydantic", "requests",
]


def run(cmd) -> str:
    try:
        return subprocess.check_output(cmd, stderr=subprocess.DEVNULL,
                                       text=True).strip()
    except Exception:
        return ""


def installed_versions():
    """Version of every package of interest, via importlib.metadata."""
    try:
        from importlib import metadata
    except ImportError:  # pragma: no cover
        import importlib_metadata as metadata  # type: ignore

    found = {}
    for name in PACKAGES_OF_INTEREST:
        try:
            found[name] = metadata.version(name)
        except Exception:
            found[name] = None
    return found


def freeze() -> str:
    return run([sys.executable, "-m", "pip", "freeze"])


def os_release() -> str:
    if os.path.exists("/etc/os-release"):
        with open("/etc/os-release") as fh:
            for line in fh:
                if line.startswith("PRETTY_NAME="):
                    return line.split("=", 1)[1].strip().strip('"')
    return platform.platform()


def pi_model() -> str:
    for path in ("/proc/device-tree/model", "/sys/firmware/devicetree/base/model"):
        if os.path.exists(path):
            try:
                with open(path, "rb") as fh:
                    return fh.read().decode("utf-8", "ignore").strip("\x00").strip()
            except Exception:
                pass
    return ""


def git_commit() -> str:
    return run(["git", "rev-parse", "HEAD"])


def build_report() -> str:
    versions = installed_versions()
    lines = []
    add = lines.append

    add("# Environment record")
    add("")
    add("Captured from the running device by `tools/pin_environment.py`. "
        "Every row below was read from this machine. Nothing here is quoted "
        "from the manuscript, and an absent package is reported as absent "
        "rather than filled in.")
    add("")
    add(f"- Captured (UTC): {datetime.datetime.now(datetime.timezone.utc).isoformat()}")
    add(f"- Hostname: {platform.node()}")
    model = pi_model()
    if model:
        add(f"- Hardware: {model}")
    add(f"- OS: {os_release()}")
    add(f"- Kernel: {platform.release()}")
    add(f"- Architecture: {platform.machine()}")
    add(f"- Python: {platform.python_version()} ({sys.executable})")
    commit = git_commit()
    add(f"- Repository commit: {commit or 'NOT A GIT CHECKOUT — record this manually'}")
    add("")

    add("## Packages named in the manuscript's software table")
    add("")
    add("| Package | Installed version |")
    add("|---|---|")
    for name in PACKAGES_OF_INTEREST:
        version = versions.get(name)
        add(f"| {name} | {version if version else '**not installed**'} |")
    add("")

    add("## Full pip freeze")
    add("")
    add("```")
    add(freeze() or "(pip freeze unavailable)")
    add("```")
    add("")
    add("## What this does not tell you")
    add("")
    add("This is the environment **now**. If the reported experiments ran on "
        "a different image, a different Pi, or before a package upgrade, this "
        "file does not describe them. It describes the machine it ran on, on "
        "the date at the top. Capture it on the device that produced the "
        "results, or record honestly that the original environment was not "
        "captured.")
    return "\n".join(lines)


def build_lock() -> str:
    header = (
        "# Fully pinned environment, captured by tools/pin_environment.py\n"
        f"# {datetime.datetime.now(datetime.timezone.utc).isoformat()}\n"
        f"# Python {platform.python_version()} on {platform.machine()}\n")
    return header + freeze() + "\n"


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", help="write the Markdown record here")
    parser.add_argument("--requirements", help="write a pinned == file here")
    args = parser.parse_args()

    report = build_report()
    if args.out:
        with open(args.out, "w") as fh:
            fh.write(report + "\n")
        print(f"Wrote {args.out}")
    else:
        print(report)

    if args.requirements:
        with open(args.requirements, "w") as fh:
            fh.write(build_lock())
        print(f"Wrote {args.requirements}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
