#!/usr/bin/env python3
"""Figure 9.3 — The life of a request, as a sequence diagram, with the two inbound directions.

Writes fig_9_3_request.svg. Run:  python3 fig_9_3_request.py

Read top to bottom. The upper panel is a service call from inside the sandbox, the case Section
9.4 describes; the numbers are the mediator's five steps, and the order of steps 4 and 5 (record
before act) is the property attribution rests on. The two lower panels are the directions that
run the other way (Section 9.4, last paragraphs): a state pushed into a subscribed sandbox,
recorded once at subscription and not per delivery, and a household's command, recorded before
it is passed on. The sandbox side of the call is `Bridge._forward_service_call` in
`confine/sandbox_runtime.py`; the mediator side is `confine/mediator.py`.
"""

from pathlib import Path

from svg9 import Canvas

OUT = Path(__file__).parent / "fig_9_3_request.svg"

LANES = {  # name: (x, heading)
    "int": (140, "Integration"),
    "b": (350, "Runtime (B)"),
    "half": (560, "Bridge, sandbox half"),
    "med": (820, "Mediator"),
    "log": (1060, "Audit log"),
    "a": (1280, "Home Assistant (A)"),
}
SANDBOX = ("int", "b", "half")
TOP, BOTTOM = 110, 1240

c = Canvas(1400, 1280, text_scale=1.5, fit=True)
c.box(30, 20, 650, BOTTOM, fill="light", dashed=True, title="INSIDE THE SANDBOX")
for key, (x, heading) in LANES.items():
    c.box(x - 95, 70, 190, 44, heading, fill="white" if key in SANDBOX else "mid", size=12,
          weight="bold")
    c.line([(x, 114), (x, BOTTOM)], arrow=False, dashed=True, width=1)


def msg(a, b, y, text, dashed=False):
    """A message from lane a to lane b, its label just above the arrow."""
    xa, xb = LANES[a][0], LANES[b][0]
    c.line([(xa, y), (xb, y)], dashed=dashed)
    # The label's white ground must end above the arrow and its head (about 6 px each side of
    # the line), at the size the canvas actually draws, or it hides them.
    shown = 11 * c.text_scale
    lift = ((shown + 4) * (text.count("\n") + 1) + 4) / 2 + 8
    c.label((xa + xb) / 2, y - lift, text, size=11)


def step(lane, y, text, h=46):
    """Work a lane does itself: a box on its lifeline."""
    x = LANES[lane][0]
    c.box(x - 135, y - h / 2, 270, h, text, fill="white", size=11)


def panel(y, title):
    c.line([(30, y), (1370, y)], arrow=False, width=1)
    c.text(40, y + 18, title, size=12, weight="bold", anchor="start")


# --- a service call from the sandbox --------------------------------------------------------
panel(140, "A SERVICE CALL FROM THE INTEGRATION")
msg("int", "b", 228, "light.turn_on, as it\nwould call it unconfined")
msg("b", "half", 285, "not a service of (B):\nforward it")
msg("half", "med", 345, "service.call frame on its channel\n(four-byte length, then JSON)")
step("med", 385, "1  identity: from the channel,\nnever from the frame", h=54)
step("med", 445, "2  the manifest bound\nto that identity", h=54)
step("med", 505, "3  permit or deny, naming\nthe deciding clause", h=54)
msg("med", "log", 590, "4  record the decision,\nflushed to disk")
msg("med", "a", 650, "5  perform the call,\nwith the mediator's token")
msg("a", "med", 695, "result", dashed=True)
msg("med", "half", 745, "answer, with the deciding clause", dashed=True)
msg("half", "int", 790, "the call returns, or raises if it was denied", dashed=True)
c.label(1170, 470, "a denied call skips\nstep 5: it is recorded\nand answered, and\nnothing is performed", size=11)

# --- a state pushed into the sandbox --------------------------------------------------------
panel(810, "A DECLARED ENTITY CHANGES IN (A)")
msg("a", "med", 870, "the entity's new state")
msg("med", "half", 930, "push to each sandbox that subscribed;\nnothing recorded per delivery")
msg("half", "b", 990, "set the state in (B)")
c.label(1170, 960, "recorded once, when\nthe subscription\nwas decided", size=11)

# --- a household's command into the sandbox ---------------------------------------------------
panel(1030, "THE HOUSEHOLD OPERATES A CONFINED ENTITY")
msg("a", "med", 1088, "command, from the bridge\nintegration in (A)")
msg("med", "log", 1135, "record it")
msg("med", "half", 1182, "pass it to the owning sandbox")
msg("half", "int", 1225, "the entity's own handler runs")

c.save(OUT)
