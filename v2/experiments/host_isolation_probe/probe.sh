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
    echo "    (Raspberry Pi OS ships this by default)"
    echo "    fix:   add 'cgroup_enable=memory cgroup_memory=1' to the boot cmdline,"
    echo "           remove cgroup_disable=memory, reboot"
  else
    echo "    cause: not cgroup_disable=memory; check the kernel build"
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
