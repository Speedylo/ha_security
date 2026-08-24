#!/usr/bin/env python3
"""Figure 4.1 — Home Assistant as it stands today, with the six trust boundaries of §4.6.

Writes two files, from one description of the figure:

    fig_4_1_current_state.json   an OWASP Threat Dragon v2 model, openable and editable
                                 in Threat Dragon (web or desktop)
    fig_4_1_current_state.svg    the rendered figure, for the report
    fig_4_1_current_state.png    the same, rasterised — only if cairosvg is installed

Run:  python3 fig_4_1_current_state.py

The rule this figure obeys (notes/decision_threat_model_diagrams.md): it draws the system
as it is TODAY. No mediator, no broker, no sandbox. Chapter 5 draws the fix, and the delta
between the two figures is the argument.

Absence is carried in each boundary's NAME — the words EXISTS and ABSENT — not in colour
and not in a symbol. Colour does not survive a greyscale printout; ✓ and ✗ do not survive
a font that lacks them, which is how the first draft of this figure rendered. Words do.

Element and flow content is specified in notes/ch4_figure_4_1_spec.md and derives from
§4.4 (assets), §4.5 (actors) and §4.6 (boundaries). Nothing here is new to the chapter.
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
NODES = [
    # --- outside the machine ------------------------------------------------------
    ("author",   "actor", "Integration author\n+ HACS channel",              60,   60, 215,  75),
    ("extnet",   "actor", "External network\nendpoints",                   1240,   90, 190,  85),
    ("user",     "actor", "Home occupant\n/ user",                           60,  420, 175,  75),
    ("devices",  "actor", "Home devices, LAN\n(A1, A4, A8)",               1240,  700, 190,  85),
    # --- inside the one process ---------------------------------------------------
    ("ha_core",  "process", "Home Assistant core\nbus · states · services\nconfig_entries · auth · http",
                                                                            370,  340, 190, 150),
    ("integ_a",  "process", "Integration A\n(third-party)",                  760,  357, 180, 115),
    ("integ_b",  "process", "Integration B\n(third-party)",                  760,  545, 180, 115),
    ("mem",      "store",   "In-memory shared state\nhass.data · states (A2, A6)",
                                                                            960,  300, 175,  85),
    # --- on disk ------------------------------------------------------------------
    ("secrets",  "store", "secrets.yaml\n+ config directory (A3)",           420,  830, 215,  85),
    ("entries",  "store", "Config entry store\nevery integration's\ncredentials (A3, A6)",
                                                                            760,  830, 215, 100),
]

# The container. A box, not a claim of protection — its label says what it is.
BOUNDARY_BOX = {
    "id": "ha_process",
    "label": "HOME ASSISTANT — ONE OS PROCESS, ONE PYTHON INTERPRETER",
    "x": 340, "y": 220, "width": 800, "height": 480,
}

# id: (name, source, target, [vertices], exists, label_xy)
# `exists` drives colour in the SVG only. The words EXISTS / ABSENT are what always
# survive — a greyscale printout, a Threat Dragon PNG export, a font without ✓ and ✗.
BOUNDARIES = [
    ("tb4", "TB4 · EXISTS — structure, not behaviour",
     (25, 240), (335, 25), [(210, 245), (300, 195)], True, (185, 212)),
    ("tb2", "TB2 · EXISTS — unscoped API surface",
     (620, 290), (620, 540), [(640, 415)], True, (600, 262)),
    ("tb1", "TB1 · ABSENT — required by S1",
     (690, 290), (690, 560), [(710, 415)], False, (600, 292)),
    ("tb3", "TB3 · ABSENT — required by F2/S4",
     (1215, 30), (1215, 900), [(1225, 400), (1215, 650)], False, (1260, 470)),
    ("tb5", "TB5 · ABSENT — required by S8",
     (300, 770), (1160, 770), [(700, 780)], False, (700, 780)),
    ("tb6", "TB6 · ABSENT — demonstrated crossable",
     (700, 508), (1150, 508), [(1000, 508)], False, (940, 508)),
]

# (id, source, target, label, source_port, target_port, bidirectional, [vertices], label_xy)
FLOWS = [
    ("f1",  "author",  "secrets", "F1  installs / updates\nintegration source",
     "bottom", "left",  False, [(180, 760)], (250, 730)),
    ("f2",  "ha_core", "integ_a", "F2  import_module →\nasync_setup(hass, …)\npasses the hass reference",
     "right",  "left",  False, [], (655, 340)),
    ("f3",  "integ_a", "ha_core", "F3  service calls · state writes\nevent subscription",
     "bottom", "bottom", False, [(640, 500)], (560, 570)),
    ("f4",  "integ_a", "mem",     "F4  direct read/write of hass.data\n(all domains)",
     "right",  "left",  True,  [], (1030, 465)),
    ("f4b", "integ_b", "mem",     "F4b  the same shared dict,\nfrom another integration",
     "right",  "bottom", True, [(1100, 602), (1100, 430)], (1040, 645)),
    ("f5",  "integ_a", "entries", "F5  reads any integration's\nstored credentials",
     "bottom", "top",   False, [(930, 740)], (1000, 730)),
    ("f6",  "integ_a", "secrets", "F6  arbitrary file read via\nhass.config.path()",
     "bottom", "top",   False, [(560, 740)], (420, 745)),
    ("f7",  "integ_a", "extnet",  "F7  unrestricted outbound",
     "top",    "left",  False, [(1030, 230)], (1080, 195)),
    ("f8",  "integ_a", "integ_b", "F8  in-process object access",
     "bottom", "top",   True,  [], (850, 488)),
    ("f9",  "integ_a", "devices", "F9  local network access",
     "right",  "left",  False, [(1170, 414), (1170, 742)], (1170, 600)),
    ("f10", "user",    "ha_core", "F10  web UI",
     "right",  "left",  True,  [], (292, 435)),
]

# Kept off the canvas and set below it: on-diagram prose competes with flow labels, and
# these two sentences are the ones a reader most needs undisturbed.
NOTES = [
    "Integrations are drawn as separate elements because they are separate CODE. They are"
    " not separate processes:\nno boundary exists between the elements inside the box, and"
    " nothing in the platform enforces one.",
    "TB1 and TB2 meet at a single interface today. No component stands between them — the"
    " integration calls the\nplatform directly, and the gap between those two curves is empty.",
]


# --------------------------------------------------------------------------------------
# 2. Threat Dragon model
# --------------------------------------------------------------------------------------

def _uid(name):
    """Stable UUID per element name, so re-running does not churn the JSON."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"td:fig41:{name}"))


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
        "position": {"x": BOUNDARY_BOX["x"], "y": BOUNDARY_BOX["y"]},
        "size": {"width": BOUNDARY_BOX["width"], "height": BOUNDARY_BOX["height"]},
        "attrs": {"label": {"text": BOUNDARY_BOX["label"]}},
        "visible": True, "shape": "trust-boundary-box", "zIndex": -1,
        "id": _uid(BOUNDARY_BOX["id"]),
        "data": {"type": "tm.BoundaryBox", "description": "", "isTrustBoundary": True,
                 "hasOpenThreats": False},
    }]
    for i, (nid, kind, label, x, y, w, h) in enumerate(NODES):
        cells.append(td_node(nid, kind, label, x, y, w, h, z=5 + i))
    for i, (bid, name, src, tgt, verts, _exists, _lxy) in enumerate(BOUNDARIES):
        cells.append(td_boundary(bid, name, src, tgt, verts, z=20 + i))
    for i, (fid, s, t, lab, sp, tp, bidi, verts, _lxy) in enumerate(FLOWS):
        cells.append(td_flow(fid, s, t, lab, sp, tp, bidi, verts, z=30 + i))
    # The two notes sit below the drawing in the SVG; in Threat Dragon they become text
    # blocks under the canvas, where they do not fight with flow labels either.
    for i, text in enumerate(NOTES):
        cells.append(td_text(i, 340, 960 + i * 70, 800, 60, text, z=50 + i))

    return {
        "version": TD_VERSION,
        "summary": {
            "title": "Home Assistant — current state (Ch. 4 §4.6)",
            "owner": "Younes Rahati",
            "id": 0,
            "description": (
                "Figure 4.1 of the capstone report. VISUALISATION ONLY: this model records "
                "the system as it stands today and its six trust boundaries. Threats are "
                "NOT enumerated here — they are derived in the report by STRIDE per "
                "boundary (§4.8), within an ISO 31000 process (§4.1), and Threat Dragon's "
                "own threat generator was not used. Boundaries marked ✗ do not exist in the "
                "current system. Generated by figures/fig_4_1_current_state.py; edit that "
                "script rather than this file."
            ),
        },
        "detail": {
            "contributors": [],
            "diagrams": [{
                "id": 0,
                "title": "Home Assistant — current state",
                "diagramType": "STRIDE",
                "placeholder": "Current state: one process, six boundaries, four absent",
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
CANVAS = (1600, 1120)
VIEW = (0, 0, 1600, 1120)


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def text_lines(x, y, label, size=12, fill=INK, weight="normal", anchor="middle"):
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

    # container
    b = BOUNDARY_BOX
    p.append(f'<rect x="{b["x"]}" y="{b["y"]}" width="{b["width"]}" height="{b["height"]}" '
             f'fill="#f7f7f7" stroke="{INK}" stroke-width="3" stroke-dasharray="12 6" rx="6"/>')
    # Left-aligned, so the top of the box stays free for the TB1/TB2 labels.
    p.append(text_lines(b["x"] + 16, b["y"] + 20, b["label"], size=13, weight="bold",
                        anchor="start"))

    # boundaries
    for _bid, name, src, tgt, verts, exists, lxy in BOUNDARIES:
        colour = PRESENT if exists else ABSENT
        pts = [src] + list(verts) + [tgt]
        d = "M " + " L ".join(f"{x},{y}" for x, y in pts)
        p.append(f'<path d="{d}" fill="none" stroke="{colour}" stroke-width="2.5" '
                 f'stroke-dasharray="10 7"/>')
        mx, my = lxy
        width = 7.3 * len(name)
        p.append(f'<rect x="{mx - width / 2:.0f}" y="{my - 11:.0f}" width="{width:.0f}" '
                 f'height="22" fill="#ffffff" stroke="{colour}" stroke-width="1" rx="4"/>')
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
        w = 6.4 * max(len(x) for x in lines)
        h = 15 * len(lines) + 6
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
    lx, ly = 40, 960
    p.append(f'<rect x="{lx}" y="{ly}" width="640" height="64" fill="#ffffff" '
             f'stroke="{MUTED}" stroke-width="1" rx="4"/>')
    p.append(f'<line x1="{lx + 16}" y1="{ly + 22}" x2="{lx + 56}" y2="{ly + 22}" '
             f'stroke="{PRESENT}" stroke-width="2.5" stroke-dasharray="10 7"/>')
    p.append(text_lines(lx + 66, ly + 22, "EXISTS — a boundary is enforced here today",
                        size=11, fill=PRESENT, anchor="start"))
    p.append(f'<line x1="{lx + 16}" y1="{ly + 44}" x2="{lx + 56}" y2="{ly + 44}" '
             f'stroke="{ABSENT}" stroke-width="2.5" stroke-dasharray="10 7"/>')
    p.append(text_lines(lx + 66, ly + 44, "ABSENT — no enforcement point exists anywhere in "
                        "the running system", size=11, fill=ABSENT, anchor="start"))
    p.append(text_lines(lx + 700, ly + 32, "4 of 6 boundaries absent", size=16,
                        fill=ABSENT, weight="bold", anchor="start"))

    # notes, below the drawing where they cannot collide with a flow label
    for i, text in enumerate(NOTES):
        p.append(text_lines(40, 1052 + i * 34, text, size=10.5, fill=MUTED, anchor="start"))

    p.append("</svg>")
    return "\n".join(p)


if __name__ == "__main__":
    (OUT / "fig_4_1_current_state.json").write_text(
        json.dumps(build_model(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT / "fig_4_1_current_state.svg").write_text(render_svg(), encoding="utf-8")
    counts = {"exists": sum(1 for b in BOUNDARIES if b[5]),
              "absent": sum(1 for b in BOUNDARIES if not b[5])}
    print(f"wrote fig_4_1_current_state.json  ({len(build_model()['detail']['diagrams'][0]['cells'])} cells)")
    print("wrote fig_4_1_current_state.svg")

    try:
        import cairosvg  # optional: SVG is the figure of record, PNG is a convenience
        cairosvg.svg2png(url=str(OUT / "fig_4_1_current_state.svg"),
                         write_to=str(OUT / "fig_4_1_current_state.png"),
                         output_width=1600, background_color="white")
        print("wrote fig_4_1_current_state.png")
    except ImportError:
        print("cairosvg not installed — skipped PNG (the SVG is the figure of record)")

    # The chapter says four of six are absent. If an edit above ever changes that, the
    # figure and §4.6 have diverged, and this stops the wrong figure being committed.
    print(f"boundaries: {counts['exists']} present, {counts['absent']} absent")
    assert counts["absent"] == 4 and counts["exists"] == 2, "§4.6 says four of six are absent"
