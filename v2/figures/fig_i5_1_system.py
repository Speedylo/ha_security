#!/usr/bin/env python3
"""Interim report Figure 5.1 — the system, with plain-language labels (Younes, 2026-10-25).

Same layout as fig_9_1_system.py (the final report's Figure 9.1); only the labels are simplified
for the interim report's non-specialist reader. Writes fig_i5_1_system.svg. Run:
python3 fig_i5_1_system.py

What the figure must show, from Section 9.1: three kinds of process, and only one of them holds
authority over the house. The token to (A) is drawn where it lives, in the mediator, and nowhere
else. The supervisor is drawn inside the same process as the mediator because that is how
`confine/supervise.py` builds it (it constructs the `Mediator` itself); it is a separate
component, not a separate process.

`confine-mediator` is a Home Assistant user, not a Linux user: the mediator connects to (A)'s
WebSocket API with that user's token (F45, Section 9.4).
"""

from pathlib import Path

from svg9 import Canvas

OUT = Path(__file__).parent / "fig_i5_1_system.svg"

c = Canvas(1500, 1010)

# --- (A), the house's own instance -------------------------------------------------------
c.box(40, 130, 380, 500, fill="light", dashed=True,
      title="THE HOUSEHOLD'S HOME ASSISTANT (A)")
c.box(70, 200, 320, 120, "Bridge integration\nshows confined devices as\n"
      "ordinary devices; explains\nany stop in Repairs")
c.box(70, 400, 320, 120, "Home Assistant\ndevices · actions\nusers · automations")
c.line([(230, 320), (230, 400)], both=True)
c.label(230, 360, "devices and\ncommands")
c.box(90, 720, 280, 64, "Household\nweb interface and app")
c.line([(230, 720), (230, 520)])

# --- the framework: one unprivileged process on the host --------------------------------------
c.box(560, 130, 440, 640, fill="light", dashed=True,
      title="FRAMEWORK — RUNS AS AN ORDINARY USER")
c.box(590, 170, 380, 90, "Supervisor\nbuilds each sandbox, stops it if needed,\n"
      "starts it again when the household asks", size=12)
c.box(590, 290, 380, 450, fill="white", title="Mediator", title_size=13)
c.box(610, 330, 340, 80, "The only credential to the house,\nas an ordinary "
      "(non-administrator)\nHome Assistant user", fill="dark", size=12)
c.box(610, 430, 340, 100, "For every request: identify the sender,\ncheck "
      "its approved permissions,\nrecord, and only then act", size=12)
c.box(610, 550, 340, 80, "Network gatekeeper\nopens each permitted connection\nfor the integration",
      size=12)
c.box(610, 650, 340, 70, "Passes device updates and\nhousehold commands into a sandbox", size=12)

# The mediator speaks to (A) over one WebSocket connection, as confine-mediator.
c.line([(590, 310), (390, 310)], both=True)
c.label(490, 280, "devices;\nhousehold commands", size=11)
c.line([(590, 460), (390, 460)])
c.label(490, 430, "actions,\ndevice states", size=11)

# --- the record ---------------------------------------------------------------------------------
c.box(600, 860, 300, 90, "Audit log\ntamper-evident;\noutside every sandbox",
      fill="mid", size=12)
c.line([(750, 740), (750, 860)])
c.label(750, 812, "written before\nthe action", size=11)

# --- the sandboxes ------------------------------------------------------------------------------
SANDBOXES = [(150, "SANDBOX — electricity prices"), (370, "SANDBOX — adaptive lighting")]
for y, title in SANDBOXES:
    c.box(1110, y, 360, 190, fill="light", dashed=True, title=title)
    c.box(1130, y + 35, 320, 50, "Unmodified integration", size=12)
    c.box(1130, y + 95, 320, 80, "Minimal Home Assistant (B)\nholding only "
          "the devices\nthe integration declared", size=12)
c.box(1110, 590, 360, 110, "… one sandbox for each\ncommunity integration;\nnone holds "
      "a credential", fill="none", dashed=True, size=12)

# One channel per sandbox: the only descriptor that leaves it.
for y_from, y_to in ((370, 245), (470, 465), (520, 645)):
    c.line([(970, y_from), (1110, y_to)], both=True)
c.label(1040, 300, "one private\nchannel\neach", size=11)

# --- the networks, reached only through the broker -------------------------------------------
c.box(1110, 860, 360, 90, "Internet and home network\nreached only through the gatekeeper,\n"
      "never from a sandbox directly", fill="mid", size=12)
c.line([(950, 615), (1060, 615), (1060, 905), (1110, 905)])
c.label(1060, 790, "permitted\nconnections", size=11)

c.text(750, 40, "Only the mediator holds a credential to the house. A sandbox's only way out "
       "is its channel,\nso nothing inside it can reach the house, the log or the network "
       "except through the mediator.", size=13, italic=True)

c.save(OUT)
