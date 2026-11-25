#!/usr/bin/env bash
# macOS / Linux: set up a virtual environment and run the whole pipeline.
# Usage: ./run.sh            (all steps)
#        ./run.sh --from 3   (skip download and cleaning)
set -euo pipefail
cd "$(dirname "$0")"

PY="${PYTHON:-python3}"
if ! command -v "$PY" >/dev/null 2>&1; then
  echo "Python 3 not found. Install it from https://www.python.org/downloads/ or with: brew install python"
  exit 1
fi
if [ ! -x .venv/bin/python ]; then
  echo "Creating virtual environment in .venv ..."
  "$PY" -m venv .venv
fi
.venv/bin/python -m pip install --quiet --upgrade pip
.venv/bin/python -m pip install --quiet -r requirements.txt
.venv/bin/python scripts/run_pipeline.py "$@"
