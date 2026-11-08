#!/usr/bin/env python3
"""Figure 12.2 — Sandboxes that fit on the device, against the average installation's need.

Writes fig_12_2_capacity.svg. Run:  python3 fig_12_2_capacity.py

The budget is 60% of the 4,050 MB the device reports (depth logs of the second final rerun);
fractions are dropped, as the depth tool does. Memory figures are Table 12.4's reported ones.
"""

from pathlib import Path

from svg9 import Canvas, INK

OUT = Path(__file__).parent / "fig_12_2_capacity.svg"
BUDGET, MEAN = 2430, 4.02
ROWS = (("No platform\ncomponents", 56.5), ("Two\ncomponents", 92.3), ("All ten\ncomponents", 135.6))
fits = [int(BUDGET // mb) for _, mb in ROWS]
assert fits == [43, 26, 17]

c = Canvas(760, 330)
X0, W, SCALE = 170, 520, 11.0  # px per sandbox
for i, ((label, mb), n) in enumerate(zip(ROWS, fits)):
    y = 40 + i * 78
    c.text(X0 - 14, y + 24, label, size=15, anchor="end")
    c.box(X0, y, n * SCALE, 48, fill="mid", stroke=1.2)
    c.text(X0 + n * SCALE + 10, y + 24, f"{n}", size=17, weight="bold", anchor="start")

x = X0 + MEAN * SCALE
c.line([(x, 24), (x, 268)], arrow=False, dashed=True, width=2)
c.line([(X0, 24), (X0, 268)], arrow=False, width=1.2)
c.text(x + 8, 291, "Average installation: 4.02 community integrations", size=15, anchor="start")
c.line([(x + 6, 291), (x, 268)], arrow=False, width=1)
c.save(OUT)
