#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [ -f .env ]; then set -a; . ./.env; set +a; fi
PYTHONPATH="${PYTHONPATH:-$(pwd)/src}"
export PYTHONPATH
source .venv/bin/activate
: "${PAPER_MODE:=true}"
export PAPER_MODE
exec python -m runner_live
