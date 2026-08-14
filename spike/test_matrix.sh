#!/usr/bin/env bash
# Full test matrix: every integration, every mode, with assertions.
#
#   ./test_matrix.sh          stub-house scenarios only (no Docker needed)
#   HA=1 ./test_matrix.sh     ...plus real Home Assistant and the bridge
#
# Written after the question "did you test this against multiple integrations
# and multiple scenarios?" — to which the honest answer was "not enough".
# Widening the matrix immediately found three defects that single-target runs
# could not have surfaced:
#
#   1. probe check 2 hardcoded andrews_arnold's entity prefix, so it reported a
#      false ALLOWED for matomo and icqa;
#   2. run_targets.sh overwrote HA_ARGS when HA=1, silently discarding
#      --isolate, so `HA=1 ISOLATE=1` tested no isolation at all;
#   3. relative redirects resolved against the rewritten URL rather than the
#      declared one, so an in-allowlist redirect was wrongly denied.
#
# The point of this file is that those are now regressions rather than
# discoveries.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${HERE}/../.venv/bin/python"
PASS=0
FAIL=0

ok()   { PASS=$((PASS+1)); printf '  \033[32mPASS\033[0m  %s\n' "$1"; }
bad()  { FAIL=$((FAIL+1)); printf '  \033[31mFAIL\033[0m  %s — %s\n' "$1" "$2"; }

# assert_run <label> <expected-allowed> <expected-blocked-or-"-"> <env...> -- <args...>
assert_run() {
  local label="$1" want_ops="$2" want_blocked="$3"; shift 3
  local out; out="$("$@" 2>&1)"
  local ops blocked chain
  ops="$(grep -oE '^supervisor: [0-9]+ allowed' <<<"$out" | grep -oE '[0-9]+' | head -1)"
  blocked="$(grep -c '\[BLOCKED\]' <<<"$out")"
  chain="$(grep -c 'audit chain    : OK' <<<"$out")"

  if [[ "${ops:-x}" != "$want_ops" ]]; then
    bad "$label" "allowed ops ${ops:-none}, wanted ${want_ops}"; return
  fi
  if [[ "$want_blocked" != "-" && "$blocked" != "$want_blocked" ]]; then
    bad "$label" "blocked ${blocked}, wanted ${want_blocked}"; return
  fi
  if [[ "$chain" -lt 1 ]]; then
    bad "$label" "audit chain not verified intact"; return
  fi
  ok "$label"
}

echo
echo "── egress policy (unit) ──────────────────────────────────────────"
if "${PYTHON}" "${HERE}/test_egress.py" >/dev/null 2>&1; then
  ok "egress.py policy suite"
else
  bad "egress.py policy suite" "see ./test_egress.py output"
fi

echo
echo "── seccomp filter loads and enforces ─────────────────────────────"
if "${PYTHON}" "${HERE}/syscall_filter.py" 2>/dev/null | grep -q '^PASS'; then
  ok "seccomp denies ptrace"
else
  bad "seccomp denies ptrace" "self-test did not report PASS"
fi

echo
echo "── single target, both isolation modes ───────────────────────────"
assert_run "andrews_arnold, baseline, probe 4/8" 8 4 \
  env "${HERE}/run_spike.sh" --probe --quiet
assert_run "andrews_arnold, isolated, probe 8/8" 8 8 \
  env "${HERE}/run_spike.sh" --probe --quiet --isolate
assert_run "andrews_arnold, isolated, HACS_ALLOW_INET restores 6/8" 8 6 \
  env HACS_ALLOW_INET=1 "${HERE}/run_spike.sh" --probe --quiet --isolate

echo
echo "── all three targets, stub house ─────────────────────────────────"
for spec in "andrews_arnold_quota 7" "matomo 44" "icqa 18"; do
  set -- $spec
  assert_run "$1, stub, no isolation"  "$2" - env "${HERE}/run_targets.sh" "$1"
  assert_run "$1, stub, isolated"      "$2" - env ISOLATE=1 "${HERE}/run_targets.sh" "$1"
done

echo
echo "── all three targets, probe, isolated ────────────────────────────"
for spec in "andrews_arnold_quota 8" "matomo 45" "icqa 19"; do
  set -- $spec
  assert_run "$1, isolated + probe, 8/8" "$2" 8 \
    env ISOLATE=1 PROBE=1 "${HERE}/run_targets.sh" "$1"
done

if [[ "${HA:-0}" == "1" ]]; then
  echo
  echo "── real Home Assistant ───────────────────────────────────────────"
  if [[ ! -f "${HERE}/.ha_token" ]]; then
    bad "real HA" "no .ha_token — run ./ha_docker.sh up && ./ha_onboard.py"
  else
    for spec in "andrews_arnold_quota 7 8" "matomo 44 45" "icqa 18 19"; do
      set -- $spec
      assert_run "$1, real HA, isolated"        "$2" - env HA=1 ISOLATE=1 "${HERE}/run_targets.sh" "$1"
      assert_run "$1, real HA, isolated + probe" "$3" 8 env HA=1 ISOLATE=1 PROBE=1 "${HERE}/run_targets.sh" "$1"
      assert_run "$1, real HA, bridge, isolated" "$2" - env HA=1 BRIDGE=1 ISOLATE=1 "${HERE}/run_targets.sh" "$1"
    done
  fi
else
  echo
  echo "── real Home Assistant ───────────────────────────────────────────"
  echo "  SKIP  set HA=1 (and bring up ./ha_docker.sh) to include these"
fi

echo
echo "─────────────────────────────────────────────────────────────────"
printf '  %d passed, %d failed\n\n' "$PASS" "$FAIL"
[[ "$FAIL" -eq 0 ]]
