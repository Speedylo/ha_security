#!/usr/bin/env python3
"""Figure C.1 (redrawn 2026-11-25) — the confined design, on the layout of Figure 8.1.

Writes fig_c_1_confined.svg (and .png if cairosvg is installed). Run:  python3 fig_c_1_confined.py

Replaces the Threat Dragon rendering (fig_8_2_confined.svg). The outer elements (author,
household, internet, home devices, host files) sit where Figure 8.1 puts them, so the difference
between the two figures is the design: each integration in its own sandbox, every request through
the mediator, every decision recorded. TB2 is NARROWED, not closed: the mediator acts as an
ordinary Home Assistant user but can still operate every device (residual risk R3). TB4 is
unchanged. TB5 and TB6 are crossed by no line at all, which is the point.
"""

from pathlib import Path

from svg9 import Canvas

OUT = Path(__file__).parent / "fig_c_1_confined.svg"


def tag(c, x, y, tb, status, w=110):
    """A boundary tag centred on (x, y), as in Figure 8.1; every boundary here exists."""
    c.box(x - w / 2, y - 25, w, 50, f"{tb}\n{status}", fill="white", size=10, weight="bold")


c = Canvas(1700, 1000, text_scale=1.5, fit=True)

c.text(850, 30, "Each integration is its own process and reaches the house only through the "
       "mediator, which records every decision.", size=13, italic=True)

# --- outside, as in Figure 8.1 ---------------------------------------------------------------------
c.box(40, 60, 260, 90, "Integration author\nand community store")
c.box(40, 600, 260, 80, "Household\nweb interface and app")
c.box(1440, 180, 240, 90, "Internet\ngranted hosts only")
c.box(1440, 470, 240, 110, "Home devices\nonly if the home\nnetwork is granted")
c.box(300, 850, 380, 110, "Files on the host\nsecrets, configuration,\nevery stored credential",
      fill="mid")

# --- Home Assistant ------------------------------------------------------------------------------
c.box(340, 180, 280, 560, fill="light", dashed=True, title="HOME ASSISTANT")
c.box(355, 250, 250, 150, "Platform core\nstates · services\ndevices · users")
c.box(355, 470, 250, 120, "Repairs panel\nthe administrator\napproves the grant shown")

# --- the framework ---------------------------------------------------------------------------------
c.box(740, 180, 260, 560, fill="light", dashed=True, title="FRAMEWORK")
c.box(755, 230, 230, 110, "Supervisor\nbuilds each sandbox\nbefore its code runs", size=12)
c.box(755, 380, 230, 320, "Mediator\nholds the only token,\nas an ordinary user;\ndecides each request\n"
      "against the manifest;\nrecords it, then acts", size=12)

# --- one sandbox per integration -----------------------------------------------------------------
c.box(1100, 250, 240, 190, fill="light", dashed=True, title="SANDBOX A")
c.box(1120, 300, 200, 120, "Integration A\n(community)")
c.box(1100, 560, 240, 190, fill="light", dashed=True, title="SANDBOX B")
c.box(1120, 610, 200, 120, "Integration B\n(community)")

c.box(740, 850, 260, 110, "Audit record\nevery decision,\nhash-chained", fill="mid")

# --- flows (lines first, tags and labels on top) ---------------------------------------------------
c.line([(300, 105), (1280, 105), (1280, 300)])                        # author -> integration
c.line([(170, 600), (170, 325), (355, 325)], both=True)               # household <-> core
c.line([(170, 530), (355, 530)])                                      # household -> approval
c.line([(605, 530), (755, 530)])                                      # approval -> mediator
c.line([(755, 370), (605, 370)])                                      # mediator -> core
c.line([(1120, 400), (985, 400)], both=True)                          # channel A
c.line([(1120, 670), (985, 670)], both=True)                          # channel B
c.line([(985, 465), (1390, 465), (1390, 225), (1440, 225)])           # mediator -> internet
c.line([(1390, 465), (1390, 525), (1440, 525)])                       # mediator -> devices
c.line([(870, 700), (870, 850)])                                      # mediator -> record

c.label(560, 78, "installs and updates the code")
c.label(262, 300, "web interface", size=11)
c.label(262, 505, "approves", size=11)
c.label(1220, 465, "permitted connections only", size=11)
c.label(870, 790, "written before\nthe act", size=11)

tag(c, 800, 105, "TB4", "UNCHANGED", w=130)
tag(c, 680, 370, "TB2", "NARROWED", w=118)
tag(c, 1042, 400, "TB1", "EXISTS", w=100)
tag(c, 1042, 670, "TB1", "EXISTS", w=100)
tag(c, 1220, 515, "TB6", "EXISTS")
tag(c, 1390, 340, "TB3", "EXISTS", w=100)
tag(c, 490, 795, "TB5", "EXISTS")

c.save(OUT)
