#!/usr/bin/env bash
# End-to-end spike: one unmodified HACS integration, sandboxed, publishing a
# state through a permission-checked bridge.
#
#   ./run_spike.sh          setup + two polls
#   ./run_spike.sh --probe  the above, then the adversarial probe
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${HERE}/../.venv/bin/python"
PORT=8765

"${PYTHON}" "${HERE}/fake_aa_api.py" --port "${PORT}" &
VENDOR_PID=$!
trap 'kill ${VENDOR_PID} 2>/dev/null || true' EXIT

# Wait for the stub cloud to accept connections.
# Fail loudly rather than racing: a stub that is not up yet makes the
# integration fail to connect, which looks like a framework regression.
READY=0
for _ in $(seq 1 100); do
  if "${PYTHON}" -c "import socket,sys; s=socket.socket(); sys.exit(s.connect_ex(('127.0.0.1',${PORT})))" 2>/dev/null; then
    READY=1; break
  fi
  sleep 0.1
done
if [[ "${READY}" -eq 0 ]]; then
  echo "stub cloud on port ${PORT} never came up — harness failure, not a result" >&2
  exit 3
fi

echo
"${PYTHON}" "${HERE}/supervisor.py" \
  --manifest "${HERE}/manifest.yaml" \
  --integration "${HERE}/target/custom_components/andrews_arnold_quota" \
  --egress-rewrite "chaos2.aa.net.uk=http://127.0.0.1:${PORT}" \
  "$@"
