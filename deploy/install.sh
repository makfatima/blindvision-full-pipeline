#!/usr/bin/env bash
# Install the Smart Goggles node on a Raspberry Pi.
#
# This script records what it installs. The output of its final step is the
# environment the device is actually running -- which is the thing the manuscript software table
# should be quoting, rather than a list assembled by hand.

set -euo pipefail

PREFIX=${PREFIX:-/opt/blindvision}
REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

echo ">> Installing from ${REPO_ROOT} to ${PREFIX}"

if ! id blindvision >/dev/null 2>&1; then
    sudo useradd --system --create-home --shell /usr/sbin/nologin blindvision
fi
# Bluetooth and camera access.
sudo usermod -aG bluetooth,video blindvision

sudo mkdir -p "${PREFIX}"
sudo cp -r "${REPO_ROOT}/smart_goggles" "${PREFIX}/"
sudo cp -r "${REPO_ROOT}/tools" "${PREFIX}/"

sudo python3 -m venv "${PREFIX}/venv"
sudo "${PREFIX}/venv/bin/pip" install --upgrade pip
sudo "${PREFIX}/venv/bin/pip" install -r "${REPO_ROOT}/smart_goggles/requirements.txt"

sudo chown -R blindvision:blindvision "${PREFIX}"

sudo cp "${REPO_ROOT}/deploy/blindvision.service" /etc/systemd/system/
sudo systemctl daemon-reload

echo
echo ">> Installed. NOT started and NOT enabled."
echo "   The device is uncalibrated until the Group B values in"
echo "   PROVENANCE.md are set. Read that file, calibrate, then:"
echo
echo "     sudo systemctl enable --now blindvision"
echo

echo ">> Capturing the installed environment"
sudo "${PREFIX}/venv/bin/python" "${REPO_ROOT}/tools/pin_environment.py" \
    --out "${REPO_ROOT}/ENVIRONMENT.md" || true
echo "   Wrote ENVIRONMENT.md. Commit it: it is the record of what this"
echo "   device ran, captured from the device, not from memory."
