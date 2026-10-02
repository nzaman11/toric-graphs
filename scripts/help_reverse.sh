#!/bin/bash
# On a machine that has finished its own n=10 share: wait until tmux session n10 ends, then help with
# another share from its far end (results append to this machine's fail10_hilbert.tsv; merge later).
#   bash scripts/help_reverse.sh "1,2/3" 4
set -euo pipefail
cd "$(dirname "$0")/.."
SHARE=${1:-1,2/3}
W=${2:-$(nproc)}
PY=$( [ -x .venv/bin/python ] && echo .venv/bin/python || echo python3 )
tmux kill-session -t =helper 2>/dev/null || true
# "=n10" = exact name (a bare "n10" would prefix-match other sessions and wait forever)
tmux new-session -d -s helper "while tmux has-session -t =n10 2>/dev/null; do sleep 60; done;$PY scripts/run_n10.py hilbert --n 10 --workers $W --batch 200 --share $SHARE --reverse 2>&1 | tee -a data/derived/run_n10b.log"
echo "helper armed in tmux session n10b (share $SHARE, reverse, $W workers)"
