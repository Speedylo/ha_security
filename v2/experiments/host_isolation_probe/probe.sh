#!/usr/bin/env bash
# What isolation primitives does this host actually offer?
#
# §5.7 chooses an isolation primitive. The choice is only defensible if the primitives it
# assumes are present on the C4 target, so this probe reports what the kernel provides
# rather than what the documentation says it should. Run it on any candidate host.
#
#   ./probe.sh            human-readable
#   ./probe.sh > out.txt  record it
#
# Requires nothing but coreutils and util-linux; deliberately does not need root, because
# needing root would itself be a finding.

set -uo pipefail

say() { printf '%-38s %s\n' "$1" "$2"; }
rule() { printf '\n%s\n' "── $1 ──────────────────────────────"; }

printf 'host isolation probe — %s\n' "$(date -Iseconds)"
say "kernel" "$(uname -srm)"
say "distribution" "$(. /etc/os-release 2>/dev/null && echo "$PRETTY_NAME" || echo unknown)"
[ -e /proc/device-tree/model ] && say "board" "$(tr -d '\0' </proc/device-tree/model)"
say "memory total" "$(awk '/MemTotal/{printf "%.0f MB", $2/1024}' /proc/meminfo)"

rule "namespaces (S1, S8 — the sandbox boundary)"
say "max user namespaces" "$(cat /proc/sys/user/max_user_namespaces 2>/dev/null || echo '?')"
if unshare -Urnpf --mount-proc true 2>/dev/null; then
  inside=$(unshare -Urnpf --mount-proc sh -c 'echo "uid=$(id -u) pid=$$ ifaces=$(ip -o link | wc -l)"' 2>/dev/null)
  say "unprivileged user+net+pid ns" "YES  ($inside)"
else
  say "unprivileged user+net+pid ns" "NO — would require privilege, which is a finding"
fi
for ns in mnt uts ipc pid net user cgroup; do
  [ -e "/proc/self/ns/$ns" ] && printf '  %-12s present\n' "$ns"
done

rule "seccomp (S8 — syscall surface)"
if [ -r /proc/sys/kernel/seccomp/actions_avail ]; then
  say "actions available" "$(cat /proc/sys/kernel/seccomp/actions_avail)"
  grep -q user_notif /proc/sys/kernel/seccomp/actions_avail \
    && say "  user_notif" "YES — supervisor can decide syscalls, not only kill/deny"
else
  say "seccomp" "NOT AVAILABLE"
fi

rule "cgroup v2 (S9 — resource limits)"
say "mount type" "$(stat -fc %T /sys/fs/cgroup)"
say "controllers at root" "$(cat /sys/fs/cgroup/cgroup.controllers 2>/dev/null || echo none)"
for c in memory pids cpu io cpuset; do
  if grep -qw "$c" /sys/fs/cgroup/cgroup.controllers 2>/dev/null; then
    printf '  %-12s AVAILABLE\n' "$c"
  else
    printf '  %-12s MISSING\n' "$c"
  fi
done
if ! grep -qw memory /sys/fs/cgroup/cgroup.controllers 2>/dev/null; then
  echo
  echo "  ⚠ the memory controller is missing, so S9 cannot bound memory on this host."
  if grep -q 'cgroup_disable=memory' /proc/cmdline; then
    echo "    cause: 'cgroup_disable=memory' is on the kernel command line"
    # Where the parameter actually LIVES decides what the operator can do about it.
    # On a Pi 5 the firmware prepends its own parameters, so cgroup_disable=memory is
    # on /proc/cmdline while the file an operator would edit does not contain it.
    # Telling them to "remove it" then sends them looking for a string that is not there.
    cf=""
    for f in /boot/firmware/cmdline.txt /boot/cmdline.txt; do
      [ -r "$f" ] && { cf="$f"; break; }
    done
    if [ -n "$cf" ] && grep -q 'cgroup_disable=memory' "$cf"; then
      echo "    it is in $cf, so it can be removed there"
      echo "    fix:   remove cgroup_disable=memory from $cf, add"
      echo "           'cgroup_enable=memory cgroup_memory=1', reboot"
    elif [ -n "$cf" ]; then
      echo "    it is NOT in $cf — the firmware prepends it, so there is"
      echo "    nothing to remove. cgroup_enable is parsed after cgroup_disable,"
      echo "    so appending the enable is what overrides it."
      echo "    fix:   append 'cgroup_enable=memory cgroup_memory=1' to the single"
      echo "           line in $cf, reboot"
    else
      echo "    fix:   append 'cgroup_enable=memory cgroup_memory=1' to the boot"
      echo "           cmdline, reboot (no cmdline.txt found to inspect)"
    fi
  else
    echo "    cause: not cgroup_disable=memory; check the kernel build"
  fi
fi

# ── S9, actually enforced? ────────────────────────────────────────────────────────────
# The rest of this script reports what the kernel OFFERS. This one block tests whether the
# memory cap BITES, because "the controller is listed" and "the limit is enforced" are
# different claims and S9 needs the second. Optional by design: it needs systemd-run and
# python3, where everything above needs only coreutils and util-linux.
if grep -qw memory /sys/fs/cgroup/cgroup.controllers 2>/dev/null; then
  rule "S9 enforcement (does the cap bite?)"
  if command -v systemd-run >/dev/null && command -v python3 >/dev/null; then
    # Placed in the cgroup AT CREATION. An unprivileged process cannot migrate itself into
    # a cgroup it just made: that needs write access to the common ancestor, which is
    # root-owned. The supervisor therefore has to place the sandbox at fork time.
    if systemd-run --user --scope -q -p MemoryMax=64M -p MemorySwapMax=0 \
         python3 -c 'bytearray(192*1024*1024)' >/dev/null 2>&1; then
      say "192 MB against a 64 MB cap" "ALLOCATED — cap NOT enforced"
    else
      say "192 MB against a 64 MB cap" "KILLED — cap enforced"
    fi
    if python3 -c 'bytearray(192*1024*1024)' >/dev/null 2>&1; then
      say "same allocation, uncapped" "succeeds (so the kill above was the cap)"
    else
      say "same allocation, uncapped" "ALSO failed — machine is short of memory; test void"
    fi
    say "ran as" "$(id -un), uid $(id -u)$([ "$(id -u)" -eq 0 ] && echo ' — ROOT, not the target case')"
  else
    say "skipped" "needs systemd-run and python3"
  fi
fi

rule "verdict"
ok=1
unshare -Urnpf --mount-proc true 2>/dev/null || { echo "namespaces: NO"; ok=0; }
[ -r /proc/sys/kernel/seccomp/actions_avail ] || { echo "seccomp: NO"; ok=0; }
[ "$(stat -fc %T /sys/fs/cgroup)" = cgroup2fs ] || { echo "cgroup v2: NO"; ok=0; }
if [ "$ok" = 1 ]; then
  if grep -qw memory /sys/fs/cgroup/cgroup.controllers 2>/dev/null; then
    echo "all primitives §5.7 relies on are present"
  else
    echo "namespaces + seccomp + cgroup v2 present; MEMORY LIMITS need a boot change"
  fi
fi
