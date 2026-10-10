#!/usr/bin/env python3
"""Figure 9.4 — Egress, resolved and pinned: how a confined integration reaches an internet host.

Writes fig_9_4_egress.svg. Run:  python3 fig_9_4_egress.py

The five numbered steps are the broker's, in `EgressBroker.open` (`confine/egress.py`): step 1 is
the decision, made before the broker is called, and steps 2 to 5 are the method. The placeholder
is the shim's (`confine/egress_shim.py`): an address from 240.0.0.0/4, reserved and unroutable,
which the shim maps back to the name it stands for. The decision is recorded before step 2,
and a refusal at step 3 is recorded as well (`Mediator._handle_ready`), so the log never shows a
grant as the last word on a request that was refused. The right-hand panel is the rebinding
attack the order defeats: the address is judged after resolution, and the connection is made to
that address, with nothing between the two lines.
"""

from pathlib import Path

from svg9 import Canvas

OUT = Path(__file__).parent / "fig_9_4_egress.svg"

LANES = {
    "int": (150, "Integration"),
    "shim": (390, "Egress shim"),
    "med": (690, "Mediator: egress broker"),
    "dns": (940, "Resolver (DNS)"),
    "host": (1150, "Declared host"),
}
SANDBOX = ("int", "shim")
BOTTOM = 820

c = Canvas(1560, 860)
c.box(30, 40, 520, BOTTOM - 10, fill="light", dashed=True, title="INSIDE THE SANDBOX")
for key, (x, heading) in LANES.items():
    c.box(x - 100, 70, 200, 44, heading, fill="white" if key in SANDBOX else "mid", size=12,
          weight="bold")
    c.line([(x, 114), (x, BOTTOM)], arrow=False, dashed=True, width=1)


def msg(a, b, y, text, dashed=False):
    xa, xb = LANES[a][0], LANES[b][0]
    c.line([(xa, y), (xb, y)], dashed=dashed)
    lift = (15 * (text.count("\n") + 1) + 4) / 2 + 3
    c.label((xa + xb) / 2, y - lift, text, size=11)


def step(lane, y, text, h=46):
    x = LANES[lane][0]
    c.box(x - 125, y - h / 2, 250, h, text, fill="white", size=11)


msg("int", "shim", 175, "resolve api.example.com")
msg("shim", "int", 225, "a placeholder from\n240.0.0.0/4 (unroutable)", dashed=True)
msg("int", "shim", 290, "connect to the\nplaceholder, port 443")
msg("shim", "med", 350, "connect api.example.com:443,\non its channel")
step("med", 410, "1  decide against the network.egress\nclauses, and record the decision", h=50)
msg("med", "dns", 475, "2  resolve the name")
msg("dns", "med", 520, "addresses", dashed=True)
step("med", 585, "3  re-check each address: refuse\nprivate, loopback, link-local,\n"
     "multicast and reserved ones;\na refusal here is recorded too", h=78)
msg("med", "host", 670, "4  connect to exactly the\naddress just checked")
msg("med", "shim", 730, "5  the connected socket,\npassed over the channel", dashed=True)
msg("shim", "int", 775, "an ordinary connected socket", dashed=True)

# --- the attack the order defeats -------------------------------------------------------------
c.box(1260, 150, 270, 330, fill="white", title="IF THE NAME REBINDS")
c.text(1395, 320, "The name was granted, but\nnow resolves to 192.168.1.1,\na device in the "
       "house.\n\nStep 3 refuses that address,\nand no connection is made.\n\nNothing passes "
       "between the\ncheck and the connect, and\nthe sandbox never holds a\nroutable address.",
       size=12)

c.save(OUT)
