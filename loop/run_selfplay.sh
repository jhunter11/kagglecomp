#!/usr/bin/env bash
# One-command Linux self-play on the Mac (via Docker). Needs ./cg/ present.
#   bash loop/run_selfplay.sh <agent_dir> <opponent> <games>
# e.g. bash loop/run_selfplay.sh agents/lucario random 200
set -euo pipefail
cd "$(dirname "$0")/.."

AGENT="${1:-agents/lucario}"; OPP="${2:-random}"; GAMES="${3:-200}"

if [ ! -e cg ]; then
  echo "ERROR: ./cg/ not found. Download it first (kaggle competitions download" \
       "-c pokemon-tcg-ai-battle) and extract sample_submission/cg to ./cg/." >&2
  exit 1
fi

echo "==> building Linux self-play image (amd64)"
docker build --platform linux/amd64 -t ptcg-selfplay -f loop/Dockerfile . >/dev/null

echo "==> verifying the engine loads"
docker run --platform linux/amd64 --rm -v "$PWD":/work -w /work ptcg-selfplay \
  python -c "import cg; print('cg OK')"

echo "==> $GAMES games: $AGENT vs $OPP"
docker run --platform linux/amd64 --rm -v "$PWD":/work -w /work ptcg-selfplay \
  python scripts/run_official_simulations.py --agent "$AGENT" --opponent "$OPP" --games "$GAMES"
