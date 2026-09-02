"""The same hostile integration, with no sandbox at all. §7.5's S8 pairing.

S8's criterion is not "the attack is blocked". §3.5 fixed it before any implementation existed:

    "the 2021 file-theft pattern is reproduced against a baseline installation **and** shown
     to be blocked under the framework."

Blocking an attack that would not have worked anyway proves nothing, so the unconfined arm is
not optional — it is half of the evidence. `selftest_adversary` supplies the confined half; this
supplies the half that makes it mean something.

**The attack code is shared, not copied.** `ATTACKS`, the canaries and `build_config` are
imported from `selftest_adversary`, so both arms run the same payload against the same
configuration layout. §7.9 requires the measurement be held fixed while confinement varies, and
the baseline arm of §7.12 established the pattern: a copy that drifted would satisfy the
requirement in appearance only.

**The verdict is inverted, and deliberately so.** This arm PASSES when the canaries leak. If the
2021 pattern fails to steal `secrets.yaml` from an ordinary process, the harness is broken, the
canaries are misplaced, or the attack no longer reproduces — and in every one of those cases the
confined result is worthless. A green light here is what licenses the green light there.

**One attack is not run**, and the omission is reported rather than silent: the unbounded
filesystem read. Confined, the cgroup bounds it and its death is the S9 result. Unconfined there
is nothing to bound it, so it would read the host into memory until the machine died — a
demonstration of T16 that costs the test hardware and settles nothing in dispute.

Run:  python3 -m confine.selftest_adversary_baseline
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from .selftest_adversary import (ATTACKS, CANARY_SECRET, CANARY_TOKEN, build_config)


def main() -> int:
    root = Path(tempfile.mkdtemp(prefix="confine-adversary-baseline-"))
    try:
        layout = build_config(root)
        script = (f"CONFIG_ROOT = {json.dumps(str(root))}\n"
                  "def _raise():\n"
                  "    import ctypes, os\n"
                  "    raise OSError(ctypes.get_errno(), os.strerror(ctypes.get_errno()))\n"
                  + ATTACKS)

        # No SandboxSpec, no cgroup, no namespaces, no seccomp, no mediator and no channel.
        # An ordinary subprocess with the invoking user's authority — which is exactly what an
        # integration has today, since §5.2 establishes it runs inside the platform's own
        # process. `cwd` is the integration's directory so the relative traversals in the
        # attack list start where they would start in a real installation.
        env = {**os.environ, "CONFINE_ADVERSARY_SKIP_UNBOUNDED": "1"}
        env.pop("CONFINE_CHANNEL_FD", None)
        proc = subprocess.run([sys.executable, "-c", script],
                              capture_output=True, text=True, timeout=900,
                              env=env, cwd=str(layout["own"]))
        text = proc.stdout
        diagnostic = proc.stderr
    finally:
        shutil.rmtree(root, ignore_errors=True)

    report = [json.loads(line) for line in text.splitlines() if line.startswith("{")]
    if not report:
        print("the unconfined adversary reported nothing at all.")
        if diagnostic:
            print("  said: " + "\n        ".join(diagnostic.splitlines()[-20:]))
        return 1
    return render_baseline(report)


def render_baseline(report: list[dict]) -> int:
    print("S8 paired baseline — the same hostile integration, with no sandbox\n")
    families: dict[str, list[dict]] = {}
    for entry in report:
        families.setdefault(entry["family"], []).append(entry)

    for family, entries in families.items():
        print(f"  {family}")
        for entry in entries:
            # The marks are inverted against the confined arm on purpose. Here a LEAK is the
            # expected outcome and a block is the surprise, so reading this output with the
            # other one's vocabulary would invert its meaning.
            mark = {"LEAKED": "LEAK", "PERMIT": "LEAK"}.get(entry["outcome"], "    ")
            print(f"    {mark}  {entry['outcome']:<10} {entry['attack']:<38} "
                  f"{entry['detail'][:46]}")
        print()

    blob = json.dumps(report)
    leaked = [e for e in report if e["outcome"] == "LEAKED"]
    canaries = [c for c in (CANARY_SECRET, CANARY_TOKEN) if c in blob]
    traversals = [e for e in report
                  if e["family"] == "2021 traversal" and e["outcome"] == "LEAKED"]

    counts: dict[str, int] = {}
    for entry in report:
        counts[entry["outcome"]] = counts.get(entry["outcome"], 0) + 1
    print("  " + "   ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    print()
    print(f"  canaries recovered           {len(canaries)}/2")
    print(f"  attacks that returned data   {len(leaked)}")
    print(f"  2021 traversals that worked  {len(traversals)}")
    print()

    # Inverted verdict. This arm exists to prove the attack is real.
    if len(canaries) < 2:
        print("FAILED — the unconfined adversary did not recover both canaries.")
        print("         S8's pairing is not established, and the confined result cannot be")
        print("         read as evidence: an attack that does not work unconfined proves")
        print("         nothing when it is blocked confined.")
        return 1
    if not traversals:
        print("FAILED — no 2021-pattern traversal succeeded unconfined.")
        return 1

    print("PASS — the 2021 file-theft pattern reproduces against an unconfined installation.")
    print("       Both canaries recovered. S8's baseline half is established, and the")
    print("       confined arm's block is now a comparison rather than an assertion.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
