#!/usr/bin/env python3
"""Figure 8.2 — the confined design, drawn on Figure 8.1's canvas (the submission's §8.3).

Writes, from one description of the figure:

    fig_8_2_confined.json   an OWASP Threat Dragon v2 model, openable and editable
    fig_8_2_confined.svg    the rendered figure, for the submission
    fig_8_2_confined.png    the same, rasterised — only if cairosvg is installed

Run:  python3 fig_8_2_confined.py

A COPY of fig_8_2_confined.py, which stays as the working report's Figure 5.1. Figure 8.1 is
fig_4_1_current_state.svg unchanged. Element positions are those of Figure 5.1, so that Figure
8.2 still reads as Figure 8.1 with boundaries added. Three things differ from Figure 5.1:

  * TB2 is NARROWED, not UNCHANGED (finding F45): the mediator connects as an ordinary
    Home Assistant user the bridge designates, so it holds no administrative function, but it
    still controls every device. That is residual risk R3, re-rated High, narrowed.
  * One flow is added, A: a grant reaches a sandbox only after a person approves exactly what
    was shown, at the device or as an administrator of (A) in the Repairs panel (F57).
  * Labels carry no section numbers from the working report; the submission's text gives them.

Absence and presence are carried in each boundary's NAME, as in Figures 4.1 and 5.1.
"""

import json
import uuid
from pathlib import Path

OUT = Path(__file__).parent
TD_VERSION = "2.3.0"

# --------------------------------------------------------------------------------------
# 1. The figure, described once.
#
# Coordinates are the Threat Dragon canvas; the SVG renderer below uses the same ones, so
# the two outputs cannot drift apart. Every id is a stable name here and is turned into a
# UUID at the end, because Threat Dragon wants UUIDs and humans do not.
# --------------------------------------------------------------------------------------
# id: (kind, label, x, y, width, height)
# Positions are identical to Figure 4.1 wherever the element survives, and must stay so.
NODES = [
    # --- outside the machine — all four kept at their Figure 4.1 positions --------
    ("author",   "actor", "Integration author\n+ community store",              60,   60, 215,  75),
    ("extnet",   "actor", "External network\nendpoints",                   1240,   90, 190,  85),
    ("user",     "actor", "Home occupant\n/ user",                           60,  420, 175,  75),
    ("devices",  "actor", "Home devices, LAN\n(A1, A4, A8): non-public\ndestinations denied\nby default",
                                                                    1225,  685, 235, 120),
    # --- the platform, now alone in its process — kept ----------------------------
    ("ha_core",  "process", "Home Assistant\ncore: events,\nstates, services,\nlogins, web",
                                                                            370,  340, 190, 150),
    # --- the framework, new in this figure ----------------------------------------
    ("supervisor", "process", "Supervisor\nbuilds each\nsandbox; checks\nthe approval",
                                                                            330,  160, 200, 105),
    ("mediator",   "process", "Mediator\nholds the\ncredential;\ndecides each\nrequest",
                                                                            575,  360, 155, 130),
    # --- inside sandbox A — the integration kept at its Figure 4.1 position -------
    ("integ_a",  "process", "Integration A\n(community)",                  760,  357, 180, 115),
    ("ha_min_a", "process", "Stripped Home\nAssistant: real\nhelpers, own state,\nempty at start",
                                                                            960,  325, 190, 120),
    # --- inside sandbox B — the integration kept ---------------------------------
    ("integ_b",  "process", "Integration B\n(community)",                  760,  585, 180, 115),
    ("ha_min_b", "process", "Stripped Home\nAssistant: a\nseparate one,\nalso empty",
                                                                            960,  595, 190, 110),
    # --- on disk — secrets and entries kept; two stores are new ------------------
    ("secrets",  "store", "Secrets file\n+ configuration (A3)",           420,  830, 215,  85),
    ("entries",  "store", "Stored settings\nevery integration's\ncredentials (A3, A6)",
                                                                            760,  830, 215, 100),
    ("manifest", "store", "Manifest store\nthe author's, in the integration\n"
                          "directory, + the operator's,\nordered",  140,  830, 215, 100),
    ("audit",    "store", "Audit record · approvals\nhash-chained, attributed\n(A7)",
                                                                            140,  960, 215, 100),
]

# Figure 4.1's single container becomes three. Each label says what the box IS; none of them
# claims protection the boundary curves do not also carry.
BOXES = [
    # Taller than in Figure 5.1, with its title at the bottom: flow A leaves the top of the
    # Home Assistant ellipse, where the title used to be.
    {"id": "ha_proc",   "label": "HOME ASSISTANT",
     "x": 348, "y": 318, "width": 222, "height": 200, "label_at": "bottom"},
    {"id": "sandbox_a", "label": "SANDBOX A: own view, filter, limits",
     "x": 750, "y": 285, "width": 405, "height": 205},
    {"id": "sandbox_b", "label": "SANDBOX B: same build, shares nothing",
     "x": 750, "y": 552, "width": 405, "height": 200},
]

# id: (name, source, target, [vertices], exists, label_xy)
# All six now read EXISTS or UNCHANGED. `exists` still drives colour in the SVG only; the
# words are what survive a greyscale printout.
BOUNDARIES = [
    ("tb4", "TB4 · UNCHANGED — checks structure only",
     (25, 240), (335, 25), [(210, 245), (300, 195)], True, (190, 150)),
    ("tb2", "TB2 · NARROWED — an ordinary user",
     (570, 330), (570, 520), [(562, 425)], True, (592, 300)),
    ("tb1", "TB1 · EXISTS — the channel",
     (749, 300), (749, 745), [(741, 520)], True, (1330, 250)),
    ("tb3", "TB3 · EXISTS — connections via the mediator",
     (1195, 30), (1195, 900), [(1205, 400), (1195, 650)], True, (1390, 470)),
    ("tb5", "TB5 · EXISTS — host files absent",
     (740, 800), (1195, 800), [(960, 810)], True, (960, 775)),
    ("tb6", "TB6 · EXISTS — separate processes",
     (748, 520), (1160, 520), [(950, 512)], True, (950, 520)),
]

# (id, source, target, label, source_port, target_port, bidirectional, [vertices], label_xy)
# A primed name — F2′, F3′ — replaces the same-numbered flow in Figure 4.1. Figure 4.1's
# F4b, F5, F6, F8 and F9 have no counterpart here, and that is the point.
FLOWS = [
    ("f1",  "author",  "secrets", "(a) installs or updates the integration's\ncode, with the author's manifest",
     "bottom", "left",  False, [(180, 760)], (270, 640)),
    ("f10", "user",    "ha_core", "(k) web interface",
     "right",  "left",  True,  [], (292, 435)),
    ("fsup", "supervisor", "ha_min_a", "(l) builds the sandbox before any integration\n"
                                       "code runs, with its own channel, so the\n"
                                       "identity is fixed before the code starts",
     "right", "top", False, [(1055, 213)], (960, 215)),
    ("f2p", "integ_a", "mediator", "(b′) the channel: every mediated request",
     "left", "right", True, [], (770, 332)),
    ("f2pp", "integ_b", "mediator", "(b″) B's own channel: a different\nchannel, therefore a different identity",
     "left", "bottom", True, [(700, 642), (700, 505)], (620, 662)),
    ("f3p", "mediator", "ha_core", "(c′) the mediator performs permitted requests\n"
                                   "with its own credential",
     "left", "right", False, [], (460, 560)),
    ("f7p", "mediator", "extnet", "(h′) the mediator resolves the name,\n"
                                  "checks the address, then connects",
     "top", "left", False, [(652, 115)], (900, 90)),
    ("f4p", "integ_a", "ha_min_a", "(d′) uses the real platform code;\nthe platform it gets is local and empty",
     "right", "left", True, [], (1040, 468)),
    ("f4pp", "integ_b", "ha_min_b", "(d″) the same, privately",
     "right", "left", True, [], (1050, 725)),
    ("fapp", "ha_core", "supervisor", "(m) approval: an administrator allows\nexactly the grant shown, in Repairs,\nor the operator at the device",
     "top", "bottom", False, [], (212, 300)),
    ("fman", "manifest", "mediator", "(n) manifest read when\nthe sandbox is built",
     "top", "bottom", False, [(247, 690), (600, 690), (600, 530)], (350, 730)),
    ("faud", "mediator", "audit", "(o) every decision recorded:\nintegration, request, verdict",
     "bottom", "left", False, [(690, 780), (90, 780), (90, 1010)], (560, 802)),
]

NOTES = [
    "Compare with Figure 8.1. Five flows drawn there are absent here: (e) the shared memory,"
    " (f) reading any integration's stored credentials, (g) reading any file,\n(i) reaching another"
    " integration's objects and (j) home network access. None of the five is refused by a check."
    " The stored settings and the secrets file are not in the\nsandbox's view, the two integrations"
    " are separate processes, and addresses in the home are refused by default, so there is no"
    " request to make.",

    "TB5 and TB6 are crossed by no flow at all, and that is deliberate rather than an omission:"
    " in Figure 8.1 those same two places carried (e), (f), (g), (i) and (j). A boundary nothing"
    " crosses is the\nstrongest form this design produces, because nothing has to decide"
    " correctly for it to hold.",

    "TB2 is narrowed, not closed. The mediator connects as an ordinary Home Assistant user that the"
    " bridge designates, so it can no longer create users, change the configuration or install"
    " integrations,\nbut it can still operate every device, because the platform cannot limit a user"
    " to some devices through a supported interface. That is residual risk R3, High, narrowed."
    " Flow (m) is new:\nno grant reaches a sandbox until a person has approved exactly what was shown.",
]

# --------------------------------------------------------------------------------------
# 2. Threat Dragon model
# --------------------------------------------------------------------------------------

def _uid(name):
    """Stable UUID per element name, so re-running does not churn the JSON."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"td:fig82:{name}"))


PORT_SIDES = ("top", "right", "bottom", "left")


def _ports(node_id):
    groups = {
        side: {
            "position": side,
            "attrs": {"circle": {"r": 4, "magnet": True, "stroke": "#5F95FF",
                                 "strokeWidth": 1, "fill": "#fff",
                                 "style": {"visibility": "hidden"}}},
        }
        for side in PORT_SIDES
    }
    items = [{"group": s, "id": _uid(f"{node_id}:{s}")} for s in PORT_SIDES]
    return {"groups": groups, "items": items}


DATA_DEFAULTS = {
    "actor": {"type": "tm.Actor", "providesAuthentication": False},
    "process": {"type": "tm.Process", "handlesCardPayment": False,
                "handlesGoodsOrServices": False, "isWebApplication": False,
                "privilegeLevel": ""},
    "store": {"type": "tm.Store", "isALog": False, "isEncrypted": False,
              "isSigned": False, "storesCredentials": False, "storesInventory": False},
}


def td_node(node_id, kind, label, x, y, w, h, z):
    attrs = {"text": {"text": label}}
    if kind == "store":
        attrs["topLine"] = {"strokeWidth": 1.5, "strokeDasharray": None}
        attrs["bottomLine"] = {"strokeWidth": 1.5, "strokeDasharray": None}
    else:
        attrs["body"] = {"stroke": "#333333", "strokeWidth": 1.5, "strokeDasharray": None}
    data = dict(DATA_DEFAULTS[kind])
    data.update({"name": label, "description": "", "outOfScope": False,
                 "reasonOutOfScope": "", "hasOpenThreats": False, "threats": []})
    return {
        "position": {"x": x, "y": y}, "size": {"width": w, "height": h},
        "attrs": attrs, "visible": True, "shape": kind, "zIndex": z,
        "ports": _ports(node_id), "id": _uid(node_id), "data": data,
    }


def _edge_label(text):
    return [{
        "markup": [{"tagName": "ellipse", "selector": "labelBody"},
                   {"tagName": "text", "selector": "labelText"}],
        "attrs": {"labelText": {"text": text, "textAnchor": "middle",
                                "textVerticalAnchor": "middle"},
                  "labelBody": {"ref": "labelText", "refRx": "50%", "refRy": "60%",
                                "fill": "#fff", "strokeWidth": 0}},
        "position": {"distance": 0.5, "args": {"keepGradient": True,
                                               "ensureLegibility": True}},
    }]


def td_flow(fid, src, tgt, label, sport, tport, bidi, vertices, z):
    return {
        "shape": "flow",
        "attrs": {"line": {"stroke": "#333333",
                           "targetMarker": {"name": "block"},
                           "sourceMarker": {"name": "block" if bidi else ""},
                           "strokeDasharray": None}},
        "width": 200, "height": 100, "zIndex": z,
        "labels": _edge_label(label.replace("\n", " ")),
        "connector": "smooth",
        "data": {"type": "tm.Flow", "name": label.replace("\n", " "), "description": "",
                 "outOfScope": False, "reasonOutOfScope": "", "hasOpenThreats": False,
                 "isBidirectional": bidi, "isEncrypted": False, "isPublicNetwork": False,
                 "protocol": "", "threats": []},
        "id": _uid(fid),
        "source": {"cell": _uid(src), "port": _uid(f"{src}:{sport}")},
        "target": {"cell": _uid(tgt), "port": _uid(f"{tgt}:{tport}")},
        "vertices": [{"x": vx, "y": vy} for vx, vy in vertices],
    }


def td_boundary(bid, name, src, tgt, vertices, z):
    return {
        "shape": "trust-boundary-curve", "width": 200, "height": 100, "zIndex": z,
        "labels": _edge_label(name), "connector": "smooth",
        "data": {"type": "tm.Boundary", "name": name, "description": "",
                 "isTrustBoundary": True, "hasOpenThreats": False},
        "id": _uid(bid),
        "source": {"x": src[0], "y": src[1]},
        "target": {"x": tgt[0], "y": tgt[1]},
        "vertices": [{"x": vx, "y": vy} for vx, vy in vertices],
    }


def td_text(idx, x, y, w, h, text, z):
    return {
        "position": {"x": x, "y": y}, "size": {"width": w, "height": h},
        "attrs": {"text": {"text": text}}, "visible": True, "shape": "td-text-block",
        "zIndex": z, "id": _uid(f"note{idx}"),
        "data": {"type": "tm.Text", "name": text, "hasOpenThreats": False},
    }


def build_model():
    cells = [{
        "position": {"x": b["x"], "y": b["y"]},
        "size": {"width": b["width"], "height": b["height"]},
        "attrs": {"label": {"text": b["label"]}},
        "visible": True, "shape": "trust-boundary-box", "zIndex": -1,
        "id": _uid(b["id"]),
        "data": {"type": "tm.BoundaryBox", "description": "", "isTrustBoundary": True,
                 "hasOpenThreats": False},
    } for b in BOXES]
    for i, (nid, kind, label, x, y, w, h) in enumerate(NODES):
        cells.append(td_node(nid, kind, label, x, y, w, h, z=5 + i))
    for i, (bid, name, src, tgt, verts, _exists, _lxy) in enumerate(BOUNDARIES):
        cells.append(td_boundary(bid, name, src, tgt, verts, z=20 + i))
    for i, (fid, s, t, lab, sp, tp, bidi, verts, _lxy) in enumerate(FLOWS):
        cells.append(td_flow(fid, s, t, lab, sp, tp, bidi, verts, z=30 + i))
    # The two notes sit below the drawing in the SVG; in Threat Dragon they become text
    # blocks under the canvas, where they do not fight with flow labels either.
    for i, text in enumerate(NOTES):
        cells.append(td_text(i, 140, 1100 + i * 70, 1180, 60, text, z=50 + i))

    return {
        "version": TD_VERSION,
        "summary": {
            "title": "Home Assistant confined — Figure 8.2 of the submission",
            "owner": "Younes Rahati",
            "id": 0,
            "description": (
                "Figure 8.2 of the capstone submission: the confined design, drawn on the "
                "same canvas as Figure 8.1 so the delta is legible. VISUALISATION ONLY — no "
                "threats are enumerated here; they are derived by STRIDE per boundary within "
                "an ISO 31000 process, and Threat Dragon's own threat generator was not used. "
                "Five boundaries read EXISTS or UNCHANGED; TB2 reads NARROWED (finding F45) and "
                "carries residual risk R3. Generated by figures/fig_8_2_confined.py; edit that "
                "script rather than this file."
            ),
        },
        "detail": {
            "contributors": [],
            "diagrams": [{
                "id": 0,
                "title": "Home Assistant confined — Figure 8.2",
                "diagramType": "STRIDE",
                "placeholder": "Confined: three processes, six boundaries, none absent",
                "thumbnail": "./public/content/images/thumbnail.stride.jpg",
                "version": TD_VERSION,
                "cells": cells,
            }],
            "diagramTop": 1,
            "reviewer": "",
            "threatTop": 0,
        },
    }


# --------------------------------------------------------------------------------------
# 3. SVG rendering — the same coordinates, drawn for the report
# --------------------------------------------------------------------------------------

INK, ABSENT, PRESENT, MUTED = "#1a1a1a", "#c0392b", "#1f7a4d", "#666666"
CANVAS = (1600, 1290)
VIEW = (0, 0, 1600, 1290)


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


TS = 1.3  # every text size, and the white ground behind each label, enlarged for print (2026-11-10)


def text_lines(x, y, label, size=12, fill=INK, weight="normal", anchor="middle"):
    size = round(size * TS, 2)
    lines = label.split("\n")
    start = y - (len(lines) - 1) * (size + 3) / 2
    out = []
    for i, line in enumerate(lines):
        out.append(
            f'<text x="{x:.0f}" y="{start + i * (size + 3):.0f}" font-size="{size}" '
            f'fill="{fill}" font-weight="{weight}" text-anchor="{anchor}" '
            f'font-family="Helvetica,Arial,sans-serif" dominant-baseline="middle">'
            f"{esc(line)}</text>"
        )
    return "\n".join(out)


def port_xy(node, side):
    _, _, _, x, y, w, h = node
    return {"top": (x + w / 2, y), "bottom": (x + w / 2, y + h),
            "left": (x, y + h / 2), "right": (x + w, y + h / 2)}[side]


def render_svg():
    nodes = {n[0]: n for n in NODES}
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS[0]}" '
         f'height="{CANVAS[1]}" viewBox="{" ".join(map(str, VIEW))}">',
         '<rect width="100%" height="100%" fill="#ffffff"/>',
         '<defs>'
         '<marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
         'markerHeight="7" orient="auto-start-reverse">'
         f'<path d="M0,0 L10,5 L0,10 z" fill="{INK}"/></marker>'
         '</defs>']

    # containers — one per process group. Figure 4.1 had exactly one, and that is the
    # single most visible difference between the two drawings.
    for b in BOXES:
        p.append(f'<rect x="{b["x"]}" y="{b["y"]}" width="{b["width"]}" '
                 f'height="{b["height"]}" fill="#f7f7f7" stroke="{INK}" stroke-width="3" '
                 f'stroke-dasharray="12 6" rx="6"/>')
        # Left-aligned, so the top of each box stays free for the boundary labels.
        label_y = b["y"] + b["height"] - 10 if b.get("label_at") == "bottom" else b["y"] + 20
        p.append(text_lines(b["x"] + 16, label_y, b["label"], size=13, weight="bold",
                            anchor="start"))

    # boundaries
    for _bid, name, src, tgt, verts, exists, lxy in BOUNDARIES:
        colour = PRESENT if exists else ABSENT
        pts = [src] + list(verts) + [tgt]
        d = "M " + " L ".join(f"{x},{y}" for x, y in pts)
        p.append(f'<path d="{d}" fill="none" stroke="{colour}" stroke-width="2.5" '
                 f'stroke-dasharray="10 7"/>')
        mx, my = lxy
        width = 7.3 * TS * len(name)
        p.append(f'<rect x="{mx - width / 2:.0f}" y="{my - 11 * TS:.0f}" width="{width:.0f}" '
                 f'height="{22 * TS:.0f}" fill="#ffffff" stroke="{colour}" stroke-width="1" rx="4"/>')
        p.append(text_lines(mx, my, name, size=11, fill=colour, weight="bold"))

    # flows
    for _fid, s, t, label, sp, tp, bidi, verts, lxy in FLOWS:
        x1, y1 = port_xy(nodes[s], sp)
        x2, y2 = port_xy(nodes[t], tp)
        pts = [(x1, y1)] + list(verts) + [(x2, y2)]
        d = "M " + " L ".join(f"{x:.0f},{y:.0f}" for x, y in pts)
        extra = ' marker-start="url(#ar)"' if bidi else ""
        p.append(f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="1.6" '
                 f'marker-end="url(#ar)"{extra}/>')
        lines = label.split("\n")
        w = 6.4 * TS * max(len(x) for x in lines)
        h = 15 * TS * len(lines) + 6
        p.append(f'<rect x="{lxy[0] - w / 2:.0f}" y="{lxy[1] - h / 2:.0f}" width="{w:.0f}" '
                 f'height="{h:.0f}" fill="#ffffff" fill-opacity="0.93" rx="3"/>')
        p.append(text_lines(lxy[0], lxy[1], label, size=10.5, fill=INK))

    # nodes
    for nid, kind, label, x, y, w, h in NODES:
        cx, cy = x + w / 2, y + h / 2
        if kind == "actor":
            p.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#ffffff" '
                     f'stroke="{INK}" stroke-width="2"/>')
        elif kind == "process":
            p.append(f'<ellipse cx="{cx}" cy="{cy}" rx="{w / 2}" ry="{h / 2}" '
                     f'fill="#ffffff" stroke="{INK}" stroke-width="2"/>')
        else:  # store — open-ended, two rules
            p.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#ffffff" '
                     f'stroke="none"/>')
            p.append(f'<line x1="{x}" y1="{y}" x2="{x + w}" y2="{y}" stroke="{INK}" '
                     f'stroke-width="2"/>')
            p.append(f'<line x1="{x}" y1="{y + h}" x2="{x + w}" y2="{y + h}" '
                     f'stroke="{INK}" stroke-width="2"/>')
        p.append(text_lines(cx, cy, label, size=11.5, weight="bold" if kind == "process" else "normal"))

    # legend
    lx, ly = 420, 952
    p.append(f'<rect x="{lx}" y="{ly}" width="740" height="96" fill="#ffffff" '
             f'stroke="{MUTED}" stroke-width="1" rx="4"/>')
    p.append(text_lines(lx + 16, ly + 20, "6 of 6 boundaries enforced — in Figure 8.1, four "
                        "of the six were absent", size=14, fill=PRESENT, weight="bold",
                        anchor="start"))
    p.append(f'<line x1="{lx + 16}" y1="{ly + 46}" x2="{lx + 56}" y2="{ly + 46}" '
             f'stroke="{PRESENT}" stroke-width="2.5" stroke-dasharray="10 7"/>')
    p.append(text_lines(lx + 66, ly + 46, "EXISTS — this design puts an enforcement point "
                        "here; in Figure 8.1 there was none", size=11, fill=PRESENT,
                        anchor="start"))
    p.append(f'<line x1="{lx + 16}" y1="{ly + 66}" x2="{lx + 56}" y2="{ly + 66}" '
             f'stroke="{PRESENT}" stroke-width="2.5" stroke-dasharray="10 7"/>')
    p.append(text_lines(lx + 66, ly + 66, "UNCHANGED / NARROWED — existed in Figure 8.1; TB4 "
                        "is as it was, TB2 is narrowed", size=11, fill=MUTED,
                        anchor="start"))
    p.append(text_lines(lx + 66, ly + 86, "(b\u2032) \u00b7 (c\u2032) \u00b7 (d\u2032) \u00b7 (h\u2032) — a primed flow replaces the "
                        "same-letter flow of Figure 8.1; (l) to (o) are new",
                        size=11, fill=INK, anchor="start"))

    # notes, below the drawing where they cannot collide with a flow label
    for i, text in enumerate(NOTES):
        p.append(text_lines(40, 1105 + i * 62, text, size=10.5, fill=MUTED, anchor="start"))

    p.append("</svg>")
    return "\n".join(p)


if __name__ == "__main__":
    (OUT / "fig_8_2_confined.json").write_text(
        json.dumps(build_model(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT / "fig_8_2_confined.svg").write_text(render_svg(), encoding="utf-8")
    print(f"wrote fig_8_2_confined.json  "
          f"({len(build_model()['detail']['diagrams'][0]['cells'])} cells)")
    print("wrote fig_8_2_confined.svg")

    try:
        import cairosvg  # optional: SVG is the figure of record, PNG is a convenience
        cairosvg.svg2png(url=str(OUT / "fig_8_2_confined.svg"),
                         write_to=str(OUT / "fig_8_2_confined.png"),
                         output_width=1600, background_color="white")
        print("wrote fig_8_2_confined.png")
    except ImportError:
        print("cairosvg not installed — skipped PNG (the SVG is the figure of record)")

    # ------------------------------------------------------------------------------
    # Checks that stop a wrong figure being committed. Figure 4.1's script asserts that
    # four of six boundaries are absent; this one asserts the complement, and two more
    # things the figure's notes state in words.
    # ------------------------------------------------------------------------------
    absent = [b[1] for b in BOUNDARIES if not b[5]]
    assert not absent, f"every boundary is enforced in this design: {absent}"
    assert len(BOUNDARIES) == 6, "six boundaries, the same six as Figure 8.1"

    unchanged = sorted(b[0] for b in BOUNDARIES if "UNCHANGED" in b[1])
    narrowed = sorted(b[0] for b in BOUNDARIES if "NARROWED" in b[1])
    assert unchanged == ["tb4"] and narrowed == ["tb2"], (
        "the third note says TB4 is unchanged and TB2 narrowed (F45); the figure now says "
        f"unchanged {unchanged}, narrowed {narrowed}")

    # The five flows Figure 4.1 draws and this one must not: F4b, F5, F6, F8, F9. If one
    # is ever added back, the notes below the drawing become false.
    gone = {"f4b", "f5", "f6", "f8", "f9"}
    drawn = {f[0] for f in FLOWS}
    assert not (gone & drawn), f"these flows are removed by the design: {gone & drawn}"

    # TB5 and TB6 are crossed by no flow. Checked structurally: no flow may have one
    # endpoint inside a sandbox box and the other in a different sandbox (TB6) or in a
    # disk store (TB5). The sandbox contents are listed once here.
    sandboxed = {"integ_a": "a", "ha_min_a": "a", "integ_b": "b", "ha_min_b": "b"}
    stores_on_disk = {"secrets", "entries", "manifest", "audit"}
    for fid, src, tgt, *_ in FLOWS:
        a, b = sandboxed.get(src), sandboxed.get(tgt)
        if a and b:
            assert a == b, f"{fid} crosses TB6, which the second note says nothing crosses"
        if (a or b) and (src in stores_on_disk or tgt in stores_on_disk):
            raise AssertionError(
                f"{fid} crosses TB5, which the second note says nothing crosses")

    print(f"boundaries: 6 enforced, 0 absent  ({', '.join(unchanged)} unchanged, {', '.join(narrowed)} narrowed)")
    print("TB5 and TB6 crossed by no flow: verified")
