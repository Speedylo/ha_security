#!/usr/bin/env python3
"""Figure 8.1 (redrawn 2026-11-25) — Home Assistant today, with the six trust boundaries.

Writes fig_8_1_today.svg (and .png if cairosvg is installed). Run:  python3 fig_8_1_today.py

Replaces the Threat Dragon rendering (fig_4_1_current_state.svg), which Younes found too dense
to read. Same content, drawn in the Section 9 style: no crossing lines, one short label per
arrow, and each trust boundary as a small tag on the arrow that crosses it. Figure C.1
(fig_c_1_confined.py) uses the same outer layout, so the two still compare side by side.
"""

from pathlib import Path

from svg9 import Canvas

OUT = Path(__file__).parent / "fig_8_1_today.svg"


def tag(c, x, y, tb, status, w=110):
    """A boundary tag centred on (x, y): dashed when the boundary is absent, solid otherwise."""
    c.box(x - w / 2, y - 25, w, 50, f"{tb}\n{status}", fill="white",
          dashed=(status == "ABSENT"), size=10, weight="bold")


c = Canvas(1700, 1000, text_scale=1.5, fit=True)

c.text(850, 30, "Everything in the dashed box is one process, so four of the six boundaries "
       "have nowhere to be enforced.", size=13, italic=True)

# --- outside the platform ---------------------------------------------------------------------
c.box(40, 60, 260, 90, "Integration author\nand community store")
c.box(40, 600, 260, 80, "Household\nweb interface and app")
c.box(1440, 180, 240, 90, "Internet\nany address")
c.box(1440, 470, 240, 110, "Home devices\nlocks · alarms\ncameras")
c.box(300, 850, 380, 110, "Files on the host\nsecrets, configuration,\nevery stored credential",
      fill="mid")

# --- the one process ----------------------------------------------------------------------------
c.box(340, 180, 1000, 560, fill="light", dashed=True,
      title="HOME ASSISTANT: ONE PROCESS, ONE PYTHON INTERPRETER")
c.box(370, 250, 250, 150, "Platform core\nstates · services\ndevices · users")
c.box(1120, 300, 200, 120, "Integration A\n(community)")
c.box(1120, 610, 200, 120, "Integration B\n(community)")

# --- what an integration can do (lines first, tags and labels on top) ----------------------------
c.line([(300, 105), (1280, 105), (1280, 300)])                        # author -> integration
c.line([(170, 600), (170, 325), (370, 325)], both=True)               # household <-> core
c.line([(1120, 360), (620, 360)])                                     # A -> core
c.line([(1220, 420), (1220, 610)])                                    # A -> B
c.line([(1320, 360), (1390, 360), (1390, 225), (1440, 225)])          # A -> internet
c.line([(1390, 360), (1390, 525), (1440, 525)])                       # A -> devices
c.line([(1220, 730), (1220, 905), (680, 905)])                        # B -> files

c.label(560, 78, "installs and updates the code")
c.label(270, 300, "web interface", size=11)
c.label(870, 318, "calls any service, writes any state")
c.label(1150, 515, "reaches its objects\nand secrets in memory", anchor="end")
c.label(950, 878, "reads any file and every stored credential")

tag(c, 800, 105, "TB4", "EXISTS")
tag(c, 740, 360, "TB2", "EXISTS")
tag(c, 1000, 360, "TB1", "ABSENT")
tag(c, 1220, 515, "TB6", "ABSENT")
tag(c, 1390, 440, "TB3", "ABSENT", w=100)
tag(c, 1220, 790, "TB5", "ABSENT")

c.save(OUT)
