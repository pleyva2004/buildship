#!/usr/bin/env bash
# Run the buildship experiments LOCALLY — needs network, so run this in your own
# terminal (Terminal.app / iTerm), NOT through Claude Code (its proxy blocks
# Nebius/Tavily/Composio). Outputs are written to *.out in the repo so Claude can
# read them directly and take the next step (no copy-paste needed).
#
#   ./run_experiments.sh
#
# Loop it (re-run every N seconds) with:  WATCH=300 ./run_experiments.sh
set -uo pipefail
cd "$(dirname "$0")"
PY="${PY:-/opt/homebrew/opt/python@3.12/bin/python3.12}"

run_once() {
  echo "===== run @ $(date -u +%FT%TZ) ====="

  echo "== preflight: DNS/network to Nebius + Tavily =="
  if ! uv run --python "$PY" python -c "import socket; [socket.getaddrinfo(h, 443) for h in ('api.studio.nebius.ai', 'api.tavily.com')]" 2>/dev/null; then
    echo "!! No network/DNS to Nebius/Tavily — connect to the internet and re-run (the last run died here: socket.gaierror)." >&2
    return 1
  fi
  echo "   network OK"

  echo "== offline tests =="
  uv run --python "$PY" -m pytest -q 2>&1 | tee tests.out

  echo "== ablation (6 arms x3) =="
  uv run --python "$PY" -m buildship.eval ablation 3 2>&1 | tee eval_ablation.out

  echo "== chain-reaction demo =="
  uv run --python "$PY" demo_chain.py 2>&1 | tee demo_chain.out

  echo "done -> tests.out, eval_ablation.out, demo_chain.out"
}

if [[ -n "${WATCH:-}" ]]; then
  while true; do run_once; echo "sleeping ${WATCH}s…"; sleep "${WATCH}"; done
else
  run_once
fi
