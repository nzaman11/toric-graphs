#!/bin/bash
# Start the n=10 Hilbert-series step detached in tmux, so it survives closing the terminal / laptop.
#   bash scripts/run_n10.sh <workers> [share]      e.g.  bash scripts/run_n10.sh 4 0/3
# Watch:  tmux attach -t n10   (detach again with Ctrl+b then d)   or   tail -f data/derived/run_n10.log
set -euo pipefail
cd "$(dirname "$0")/.."
W=${1:-$(nproc)}
SHARE=${2:-}
PY=$( [ -x .venv/bin/python ] && echo .venv/bin/python || echo python3 )
ARGS="hilbert --n 10 --workers $W --batch 500"
[ -n "$SHARE" ] && ARGS="$ARGS --share $SHARE"
tmux kill-session -t n10 2>/dev/null || true
tmux new-session -d -s n10 "$PY scripts/run_n10.py $ARGS 2>&1 | tee -a data/derived/run_n10.log"
echo "started in tmux session 'n10': $PY scripts/run_n10.py $ARGS"
