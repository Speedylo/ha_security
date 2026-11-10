#!/usr/bin/env python3
"""Figure 9.2 — One sandbox: the layers that enclose a confined integration.

Writes fig_9_2_sandbox.svg. Run:  python3 fig_9_2_sandbox.py

Nesting follows what each layer applies to. The cgroup slice bounds everything the sandbox
runs; the seven namespaces decide what it can see (files, processes, network); the seccomp filter
sits on the interpreter's system-call edge, inside the namespaces. Each fact is from the code:
the seven namespaces from `confine/namespaces.py`, the default limits from `confine/cgroup.py`,
the deny-list groups from `confine/seccomp.py`, and what the integration sees from the
self-test's view from inside (Section 9.2).
"""

from pathlib import Path

from svg9 import Canvas

OUT = Path(__file__).parent / "fig_9_2_sandbox.svg"

c = Canvas(1400, 760, text_scale=1.5, fit=True)

c.box(40, 40, 1000, 680, fill="light", dashed=True, stroke=2,
      title="CGROUP V2 SLICE — bounds by default: 640 MB of memory · 64 processes · "
            "64 MB of private /tmp")
c.box(80, 90, 920, 600, fill="white", dashed=True, stroke=2,
      title="SEVEN NAMESPACES — user · mount · pid · network · ipc · uts · cgroup")
c.box(120, 140, 840, 170, fill="light", dashed=True, stroke=2,
      title="SECCOMP FILTER — a deny-list: kernel modules, ptrace, mount, bpf, unshare, setns "
            "… fail with EPERM")
c.box(160, 190, 760, 100, "One Python interpreter: the unmodified integration, inside "
      "runtime (B),\nwith the bridge's sandbox half and the egress shim", fill="white")

# What the namespaces leave in view.
c.box(120, 340, 400, 320, fill="white", title="Filesystem view (mount namespace)")
FILES = [("The integration's own directory", "read-only"),
         ("/sandbox/data", "writable"),
         ("/tmp", "private, within the slice"),
         ("secrets.yaml", "absent"),
         ("The configuration store (.storage)", "absent")]
for i, (path, state) in enumerate(FILES):
    y = 390 + i * 52
    c.box(140, y, 360, 42, fill="mid" if state == "absent" else "white")
    c.text(155, y + 21, path, size=12, anchor="start")
    c.text(485, y + 21, state, size=12, weight="bold", anchor="end")

c.box(560, 340, 400, 140, "Network (network namespace)\na loopback interface, with multicast "
      "on\nloopback only, and no route anywhere", size=12)
c.box(560, 500, 400, 160, "Identity and processes\nroot inside, an unprivileged\nuser outside; one process;\nno shared memory, host name\nor cgroup position", size=12)

# The one descriptor that leaves.
c.box(1160, 200, 200, 80, "Mediator\n(outside the sandbox)", fill="mid")
c.line([(920, 240), (1160, 240)], both=True, width=2.2)
c.label(1175, 130, "the channel: one end of a\nUnix socket pair, the only\ndescriptor "
        "that leaves", size=12)
c.line([(1100, 158), (1100, 234)], arrow=False, dashed=True, width=1)

c.save(OUT)
