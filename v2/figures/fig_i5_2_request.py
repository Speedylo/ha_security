"""Interim report Figure 5.2 — the life of a request, with plain-language labels (Younes,
2026-10-25). Same layout as fig_9_3_request.py (the final report's Figure 9.3); only the labels
are simplified. Writes fig_i5_2_request.svg. Run:  python3 fig_i5_2_request.py
"""

from pathlib import Path

from svg9 import Canvas

OUT = Path(__file__).parent / "fig_i5_2_request.svg"

LANES = {  # name: (x, heading)
    "int": (140, "Integration"),
    "b": (350, "Minimal copy (B)"),
    "half": (560, "Bridge (sandbox side)"),
    "med": (820, "Mediator"),
    "log": (1060, "Audit log"),
    "a": (1280, "Home Assistant (A)"),
}
SANDBOX = ("int", "b", "half")
TOP, BOTTOM = 110, 1240

c = Canvas(1400, 1280)
c.box(30, 40, 650, BOTTOM - 20, fill="light", dashed=True, title="INSIDE THE SANDBOX")
for key, (x, heading) in LANES.items():
    c.box(x - 95, 70, 190, 44, heading, fill="white" if key in SANDBOX else "mid", size=12,
          weight="bold")
    c.line([(x, 114), (x, BOTTOM)], arrow=False, dashed=True, width=1)


def msg(a, b, y, text, dashed=False):
    """A message from lane a to lane b, its label just above the arrow."""
    xa, xb = LANES[a][0], LANES[b][0]
    c.line([(xa, y), (xb, y)], dashed=dashed)
    lift = (15 * (text.count("\n") + 1) + 4) / 2 + 3
    c.label((xa + xb) / 2, y - lift, text, size=11)


def step(lane, y, text, h=46):
    """Work a lane does itself: a box on its lifeline."""
    x = LANES[lane][0]
    c.box(x - 125, y - h / 2, 250, h, text, fill="white", size=11)


def panel(y, title):
    c.line([(30, y), (1370, y)], arrow=False, width=1)
    c.text(40, y + 18, title, size=13, weight="bold", anchor="start")


# --- a service call from the sandbox --------------------------------------------------------
panel(140, "THE INTEGRATION SWITCHES ON A LIGHT")
msg("int", "b", 220, "switch on the light, exactly\nas it would unconfined")
msg("b", "half", 275, "not handled here:\npass it on")
msg("half", "med", 335, "the request, sent down\nits private channel")
step("med", 390, "1  identify: by the channel it came\non, never by what it claims")
step("med", 445, "2  look up its approved permissions")
step("med", 500, "3  decide: allow or refuse, naming\nthe permission that decided")
msg("med", "log", 580, "4  record the decision\non disk")
msg("med", "a", 640, "5  carry out the action, with\nthe mediator's credential")
msg("a", "med", 685, "result", dashed=True)
msg("med", "half", 735, "answer, naming the deciding permission", dashed=True)
msg("half", "int", 780, "the call succeeds, or fails if it was refused", dashed=True)
c.label(1170, 470, "a refused request skips\nstep 5: it is recorded\nand answered, and\nnothing is done", size=11)

# --- a state pushed into the sandbox --------------------------------------------------------
panel(810, "A DEVICE THE INTEGRATION FOLLOWS CHANGES IN (A)")
msg("a", "med", 870, "the device's new state")
msg("med", "half", 930, "sent to each sandbox that follows it;\nnot recorded every time")
msg("half", "b", 990, "update the device in (B)")
c.label(1170, 960, "recorded once, when\nfollowing the device\nwas allowed", size=11)

# --- a household's command into the sandbox ---------------------------------------------------
panel(1030, "THE HOUSEHOLD USES A DEVICE THE INTEGRATION PROVIDES")
msg("a", "med", 1080, "command, from the bridge\nin (A)")
msg("med", "log", 1130, "record it")
msg("med", "half", 1180, "pass it to that sandbox")
msg("half", "int", 1225, "the integration handles it")

c.save(OUT)
