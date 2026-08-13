#!/usr/bin/env bash
# Run a real, stock Home Assistant in Docker for the supervisor to sit behind.
#
#   ./ha_docker.sh up        start it (and wait until the API answers)
#   ./ha_docker.sh down      stop and remove the container
#   ./ha_docker.sh logs      follow its log
#   ./ha_docker.sh status    is it up?
#
# Deliberately the official published image with no modifications, no custom
# components mounted, and no patches: the claim being tested is that the
# framework works against Home Assistant *as shipped*.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NAME="${HA_CONTAINER:-capstone-ha}"
PORT="${HA_PORT:-8123}"
IMAGE="${HA_IMAGE:-ghcr.io/home-assistant/home-assistant:2026.8.1}"
CONFIG_DIR="${HERE}/.ha_config"

case "${1:-up}" in
  up)
    if docker ps --format '{{.Names}}' | grep -qx "${NAME}"; then
      echo "already running: ${NAME} on :${PORT}"
      exit 0
    fi
    docker rm -f "${NAME}" >/dev/null 2>&1 || true
    mkdir -p "${CONFIG_DIR}"
    echo "starting ${IMAGE} as ${NAME} on :${PORT}"
    # No --network host: the container gets its own stack, and the supervisor
    # reaches it over the published port exactly as any REST client would.
    docker run -d --name "${NAME}" \
      -p "127.0.0.1:${PORT}:8123" \
      -v "${CONFIG_DIR}:/config" \
      -e TZ="${TZ:-Africa/Casablanca}" \
      "${IMAGE}" >/dev/null

    printf "waiting for the API"
    for _ in $(seq 1 180); do
      if curl -sf -o /dev/null "http://127.0.0.1:${PORT}/manifest.json" 2>/dev/null; then
        echo " — up at http://127.0.0.1:${PORT}"
        exit 0
      fi
      printf "."
      sleep 2
    done
    echo
    echo "timed out; last 40 log lines:" >&2
    docker logs --tail 40 "${NAME}" >&2
    exit 1
    ;;
  down)
    docker rm -f "${NAME}" >/dev/null 2>&1 && echo "removed ${NAME}" || echo "not running"
    ;;
  logs)
    docker logs -f "${NAME}"
    ;;
  status)
    if docker ps --format '{{.Names}}' | grep -qx "${NAME}"; then
      echo "running on :${PORT}"
      curl -s "http://127.0.0.1:${PORT}/manifest.json" >/dev/null && echo "API answering" || echo "API not answering yet"
    else
      echo "not running"
    fi
    ;;
  *)
    echo "usage: $0 {up|down|logs|status}" >&2
    exit 2
    ;;
esac
