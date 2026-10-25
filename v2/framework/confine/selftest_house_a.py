"""`house_a`'s liveness test, which `stop` waits on (F69, `notes/f69_zombie_stop_prediction_20261025.md`).

A process that has exited but not been reaped is a zombie: `os.kill(pid, 0)` still succeeds on it.
An end-to-end harness is a subreaper, so an (A) it restarted becomes its child and, once stopped, its
zombie, and `stop` waited 60 s for a process that had already exited.

    Z1   a zombie is not alive; a running child is; a pid that does not exist is not

Run:  python3 -m confine.selftest_house_a
"""

from __future__ import annotations

import subprocess
import sys
import time

from . import house_a

results: list[bool] = []


def check(claim: str, condition: bool, detail: str = "") -> None:
    results.append(bool(condition))
    print(f"{'  ok  ' if condition else '  FAIL'}  {claim}{f'  — {detail}' if detail else ''}")


def main() -> int:
    alive = getattr(house_a, "alive", None)
    if alive is None:   # before the fix, `stop`'s own test
        def alive(pid: int) -> bool:
            try:
                house_a.os.kill(pid, 0)
            except ProcessLookupError:
                return False
            return True

    running = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    check("Z1 a running child is alive", alive(running.pid), str(running.pid))
    running.kill()
    running.wait()

    exited = subprocess.Popen([sys.executable, "-c", "pass"])
    time.sleep(1.0)           # it has exited; not waited for, it is a zombie
    with open(f"/proc/{exited.pid}/stat") as stat:
        state = stat.read().rpartition(")")[2].split()[0]
    check("Z1 an exited child not yet reaped is a zombie (the case)", state == "Z", state)
    check("Z1 and a zombie is not alive", not alive(exited.pid), str(exited.pid))
    exited.wait()

    check("Z1 a pid that does not exist is not alive", not alive(exited.pid))
    print(f"\n{sum(results)}/{len(results)} checks passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
