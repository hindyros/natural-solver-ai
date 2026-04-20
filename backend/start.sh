#!/usr/bin/env bash
set -e

DEPS=/opt/render/project/src/backend/py_packages
REQS=/opt/render/project/src/optimate/requirements-deploy.txt

echo "[start.sh] Installing Python dependencies to $DEPS..."
pip3 install --quiet --target="$DEPS" -r "$REQS"
echo "[start.sh] Python deps ready. Starting server..."

exec node server.js
