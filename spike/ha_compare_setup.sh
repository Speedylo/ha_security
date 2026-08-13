#!/usr/bin/env bash
# Arrange the same integration in Home Assistant twice, so the difference between
# a natively-loaded entity and a framework-published one can be measured rather
# than asserted.
#
#   ./ha_compare_setup.sh     install natively, configure it, then publish via the framework
#   ./registry_gap.py         report the differences
#   ./registry_gap.py --restart-test   ...including survival across an HA restart
#
# matomo is used because it configures with nothing but a URL and a token, so its
# config flow can be driven headlessly against the same stub the framework uses.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${HERE}/../.venv/bin/python"
NAME="${HA_CONTAINER:-capstone-ha}"
BASE="${HA_URL:-http://127.0.0.1:8123}"
PORT=8766

if [[ ! -f "${HERE}/.ha_token" ]]; then
  echo "no .ha_token — run ./ha_docker.sh up && ./ha_onboard.py first" >&2
  exit 2
fi
TOKEN="$(cat "${HERE}/.ha_token")"

echo "1/4  installing matomo into HA's own custom_components (the normal, unsafe way)"
mkdir -p "${HERE}/.ha_config/custom_components"
# HA runs as root in the container and leaves root-owned __pycache__ behind, which
# the host user cannot delete — so clear the old copy from inside the container.
docker exec "${NAME}" rm -rf /config/custom_components/matomo >/dev/null 2>&1 || true
rm -rf "${HERE}/.ha_config/custom_components/matomo" 2>/dev/null || true
cp -r "${HERE}/targets/matomo/custom_components/matomo" "${HERE}/.ha_config/custom_components/"
rm -rf "${HERE}/.ha_config/custom_components/matomo/__pycache__" 2>/dev/null || true

echo "2/4  restarting HA so it picks the integration up"
docker restart "${NAME}" >/dev/null
printf "     waiting"
for _ in $(seq 1 120); do
  if curl -sf -o /dev/null "${BASE}/manifest.json" 2>/dev/null; then break; fi
  printf "."
  sleep 2
done
echo " up"
sleep 8

# The stub must bind on all interfaces: HA runs in a container and reaches the
# host through host.docker.internal, not 127.0.0.1.
"${PYTHON}" "${HERE}/fake_matomo_api.py" --host 0.0.0.0 --port "${PORT}" >/dev/null 2>&1 &
STUB_PID=$!
trap 'kill ${STUB_PID} 2>/dev/null || true' EXIT
sleep 1

echo "3/4  driving its config flow headlessly, as a user clicking through the UI would"
HA_URL="${BASE}" HA_TOKEN="${TOKEN}" STUB_PORT="${PORT}" "${PYTHON}" - <<'PY'
import json, os, time, urllib.request

BASE, TOKEN = os.environ["HA_URL"], os.environ["HA_TOKEN"]
PORT = os.environ["STUB_PORT"]


def call(path, payload=None, method="GET"):
    body = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(BASE + path, data=body, method=method)
    request.add_header("Authorization", f"Bearer {TOKEN}")
    request.add_header("Content-Type", "application/json")
    raw = urllib.request.urlopen(request, timeout=30).read().decode()
    return json.loads(raw) if raw.strip() else None


existing = [e for e in call("/api/config/config_entries/entry") if e.get("domain") == "matomo"]
if existing:
    print(f"     already configured ({len(existing)} entry); leaving it in place")
else:
    flow = call("/api/config/config_entries/flow", {"handler": "matomo", "show_advanced_options": False}, "POST")
    flow_id = flow["flow_id"]
    call(f"/api/config/config_entries/flow/{flow_id}",
         {"url": f"http://host.docker.internal:{PORT}", "token_auth": "not-a-real-token"}, "POST")
    done = call(f"/api/config/config_entries/flow/{flow_id}",
                {"site_id": "1", "include_aggregate": False}, "POST")
    print(f"     created config entry: {done.get('title')}")
    time.sleep(6)
PY

echo "4/4  publishing the same integration through the framework (outside HA's process)"
"${PYTHON}" "${HERE}/supervisor.py" \
  --manifest "${HERE}/manifests/matomo.yaml" \
  --integration "${HERE}/targets/matomo/custom_components/matomo" \
  --entry-data '{"url":"https://analytics.example.org","token_auth":"not-a-real-token","site_id":1,"site_name":"example.org","include_aggregate":false}' \
  --egress-rewrite "analytics.example.org=http://127.0.0.1:${PORT}" \
  --ha-url "${BASE}" --ha-token "${TOKEN}" --quiet >/dev/null

echo
echo "both halves are in place — now run:  ./registry_gap.py"
