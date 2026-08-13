#!/usr/bin/env bash
# Run every target integration end-to-end under the shim + supervisor.
#
#   ./run_targets.sh              all three
#   ./run_targets.sh matomo       just one
#
# Each target is an unmodified HACS integration, its hand-written manifest, and
# a stub of its vendor cloud. run_spike.sh remains the single-target entry point
# for andrews_arnold_quota and the adversarial probe.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${HERE}/../.venv/bin/python"

# name | integration dir | manifest | stub script | port | declared host | entry data
TARGETS=(
"andrews_arnold_quota|${HERE}/target/custom_components/andrews_arnold_quota|${HERE}/manifest.yaml|fake_aa_api.py|8765|chaos2.aa.net.uk|{\"username\": \"sandbox@example.org\", \"password\": \"not-a-real-password\"}"
"matomo|${HERE}/targets/matomo/custom_components/matomo|${HERE}/manifests/matomo.yaml|fake_matomo_api.py|8766|analytics.example.org|{\"url\":\"https://analytics.example.org\",\"token_auth\":\"not-a-real-token\",\"site_id\":1,\"site_name\":\"example.org\",\"include_aggregate\":false}"
"icqa|${HERE}/targets/icqa/custom_components/icqa|${HERE}/manifests/icqa.yaml|fake_icqa_api.py|8767|www.gencat.cat|{\"station_id\":\"8019004\"}"
)

WANTED="${1:-all}"
FAILED=0

for spec in "${TARGETS[@]}"; do
  IFS='|' read -r name dir manifest stub port host entry <<<"${spec}"
  if [[ "${WANTED}" != "all" && "${WANTED}" != "${name}" ]]; then
    continue
  fi

  echo
  echo "════════════════════════════════════════════════════════════════"
  echo "  ${name}"
  echo "════════════════════════════════════════════════════════════════"

  "${PYTHON}" "${HERE}/${stub}" --port "${port}" >/dev/null 2>&1 &
  STUB_PID=$!
  trap 'kill ${STUB_PID} 2>/dev/null || true' EXIT

  for _ in $(seq 1 50); do
    if "${PYTHON}" -c "import socket,sys; s=socket.socket(); sys.exit(s.connect_ex(('127.0.0.1',${port})))" 2>/dev/null; then
      break
    fi
    sleep 0.1
  done

  if "${PYTHON}" "${HERE}/supervisor.py" \
      --manifest "${manifest}" \
      --integration "${dir}" \
      --entry-data "${entry}" \
      --egress-rewrite "${host}=http://127.0.0.1:${port}" \
      --quiet; then
    :
  else
    echo "  ${name}: FAILED"
    FAILED=$((FAILED + 1))
  fi

  kill ${STUB_PID} 2>/dev/null || true
  wait ${STUB_PID} 2>/dev/null || true
  trap - EXIT
done

echo
if [[ ${FAILED} -eq 0 ]]; then
  echo "all requested targets ran"
else
  echo "${FAILED} target(s) failed"
fi
exit ${FAILED}
