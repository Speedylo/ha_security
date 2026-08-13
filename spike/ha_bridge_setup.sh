#!/usr/bin/env bash
# Install and configure the sandbox_bridge integration inside the running HA.
#
#   ./ha_bridge_setup.sh
#   HA=1 BRIDGE=1 ./run_targets.sh
#
# The bridge is the *trusted* half of the framework: a small native integration
# that owns a config entry and a device, and creates registry-backed entities on
# behalf of integrations running outside Home Assistant. No untrusted code is
# loaded into HA by this — the sandboxed integrations still run in their own
# process behind the supervisor's manifest checks.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${HERE}/../.venv/bin/python"
NAME="${HA_CONTAINER:-capstone-ha}"
BASE="${HA_URL:-http://127.0.0.1:8123}"

if [[ ! -f "${HERE}/.ha_token" ]]; then
  echo "no .ha_token — run ./ha_docker.sh up && ./ha_onboard.py first" >&2
  exit 2
fi
TOKEN="$(cat "${HERE}/.ha_token")"

echo "1/3  installing the bridge into HA's custom_components"
mkdir -p "${HERE}/.ha_config/custom_components"
docker exec "${NAME}" rm -rf /config/custom_components/sandbox_bridge >/dev/null 2>&1 || true
rm -rf "${HERE}/.ha_config/custom_components/sandbox_bridge" 2>/dev/null || true
cp -r "${HERE}/bridge_integration/sandbox_bridge" "${HERE}/.ha_config/custom_components/"

echo "2/3  restarting HA"
docker restart "${NAME}" >/dev/null
printf "     waiting"
for _ in $(seq 1 120); do
  if curl -sf -o /dev/null "${BASE}/manifest.json" 2>/dev/null; then break; fi
  printf "."
  sleep 2
done
echo " up"
sleep 8

echo "3/3  creating its config entry"
HA_URL="${BASE}" HA_TOKEN="${TOKEN}" "${PYTHON}" - <<'PY'
import json, os, sys, time, urllib.request

BASE, TOKEN = os.environ["HA_URL"], os.environ["HA_TOKEN"]


def call(path, payload=None, method="GET"):
    body = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(BASE + path, data=body, method=method)
    request.add_header("Authorization", f"Bearer {TOKEN}")
    request.add_header("Content-Type", "application/json")
    raw = urllib.request.urlopen(request, timeout=30).read().decode()
    return json.loads(raw) if raw.strip() else None


existing = [e for e in call("/api/config/config_entries/entry") if e.get("domain") == "sandbox_bridge"]
if existing:
    print("     already configured")
else:
    result = call("/api/config/config_entries/flow",
                  {"handler": "sandbox_bridge", "show_advanced_options": False}, "POST")
    if result.get("type") != "create_entry":
        sys.exit(f"     flow did not complete: {json.dumps(result)[:400]}")
    print(f"     created config entry: {result.get('title')}")
    time.sleep(4)

services = {s["domain"]: set(s.get("services", {})) for s in call("/api/services")}
if "publish" in services.get("sandbox_bridge", set()):
    print("     service sandbox_bridge.publish is available")
else:
    sys.exit("     bridge did not register its service — check: ./ha_docker.sh logs")
PY

echo
echo "bridge ready — now run:  HA=1 BRIDGE=1 ./run_targets.sh"
