#!/usr/bin/env python3
"""Figure 12.1 — Device states one integration can read, unconfined and confined.

Writes fig_12_1_states.svg. Run:  python3 fig_12_1_states.py

One square per device of the test home. The counts are read from the second final rerun's
selftest_reads log, so the drawing cannot drift from the measurement.
"""

import re
from pathlib import Path

from svg9 import Canvas

HERE = Path(__file__).parent
LOG = (HERE.parent / "experiments/verify/results/final2_20261101/chunkA_step01/suites_1"
       / "selftest_reads.log")
OUT = HERE / "fig_12_1_states.svg"

log = LOG.read_text()
un_all, total, co_all, _ = map(int, re.search(
    r"entities present to it\s+(\d+)/(\d+)\s+(\d+)/(\d+)", log).groups())
un_pres, pres, co_pres, _ = map(int, re.search(
    r"of those, occupancy or presence\s+(\d+)/(\d+)\s+(\d+)/(\d+)", log).groups())
assert (un_all, total, co_all, un_pres, pres, co_pres) == (36, 36, 1, 20, 20, 0)

CELL, GAP, COLS = 36, 7, 6
c = Canvas(760, 430)


def panel(x0, title, sub, dark, mid):
    c.text(x0 + 129, 28, title, size=17, weight="bold")
    c.text(x0 + 129, 54, sub, size=15)
    for i in range(total):
        x = x0 + (i % COLS) * (CELL + GAP)
        y = 78 + (i // COLS) * (CELL + GAP)
        fill = "dark" if i < dark else "light" if i < dark + mid else "white"
        c.box(x, y, CELL, CELL, fill=fill, stroke=1.2 if i < dark + mid else 0.6)


panel(70, "Unconfined", f"{un_all} of {total} readable", un_pres, un_all - un_pres)
panel(432, "Confined", f"{co_all} of {total} readable", co_pres, co_all - co_pres)

for x, fill, label in ((40, "dark", "Readable, shows if someone is home"),
                       (340, "light", "Readable"), (480, "white", "Not visible")):
    c.box(x, 370, 22, 22, fill=fill, stroke=1.2)
    c.text(x + 32, 381, label, size=15, anchor="start")

c.save(OUT)
