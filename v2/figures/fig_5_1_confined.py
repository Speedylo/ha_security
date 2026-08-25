#!/usr/bin/env python3
"""Figure 5.1 — the same diagram as Figure 4.1, with TB1, TB3, TB5 and TB6 instantiated.

Writes two files, from one description of the figure:

    fig_5_1_confined.json   an OWASP Threat Dragon v2 model, openable and editable
    fig_5_1_confined.svg    the rendered figure, for the report
    fig_5_1_confined.png    the same, rasterised — only if cairosvg is installed

Run:  python3 fig_5_1_confined.py

This is a COPY of fig_4_1_current_state.py, per notes/ch4_figure_4_1_spec.md §9. Element
positions are deliberately unchanged wherever the element survives, so that Figure 5.1 is
recognisable as Figure 4.1 with boundaries added. The delta between the two figures is the
argument (notes/decision_threat_model_diagrams.md); redrawn from scratch it would not be.

Three things about the delta are load-bearing and are stated in the notes below the drawing:

  * Five flows present in Figure 4.1 are simply absent here — F4b, F5, F6, F8, F9. They are
    not refused by a check; the design leaves nothing to ask (§5.6.2, §5.10.2).
  * TB5 and TB6 are crossed by no flow at all, which is the strongest form a boundary takes.
  * TB2 is UNCHANGED, and the figure says so. The mediator holds as unscoped a credential as
    an integration holds today, because the platform issues no other kind. That is R3.

Absence and presence are carried in each boundary's NAME — the words EXISTS and UNCHANGED —
not in colour and not in a symbol, for the reasons given in the Figure 4.1 script.
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
    ("author",   "actor", "Integration author\n+ HACS channel",              60,   60, 215,  75),
    ("extnet",   "actor", "External network\nendpoints",                   1240,   90, 190,  85),
    ("user",     "actor", "Home occupant\n/ user",                           60,  420, 175,  75),
    ("devices",  "actor", "Home devices, LAN (A1, A4, A8)\nnon-public destinations are\n"
                          "denied by default (T10)",                       1240,  690, 190, 105),
    # --- the platform, now alone in its process — kept ----------------------------
    ("ha_core",  "process", "Home Assistant core\nbus · states · services\nconfig_entries · auth · http",
                                                                            370,  340, 190, 150),
    # --- the framework, new in this figure ----------------------------------------
    ("supervisor", "process", "Supervisor\nbuilds each sandbox\n(§5.7.3, §5.12.2)",
                                                                            330,  160, 200, 105),
    ("mediator",   "process", "Mediator\nholds the credential ·\ndecides each request\n(§5.10, §5.11.3)",
                                                                            575,  360, 155, 130),
    # --- inside sandbox A — the integration kept at its Figure 4.1 position -------
    ("integ_a",  "process", "Integration A\n(third-party)",                  760,  357, 180, 115),
    ("ha_min_a", "process", "Stripped Home Assistant\nthe real helper layer · its own\n"
                            "bus, state machine and hass.data,\nempty at start (§5.6.2)",
                                                                            960,  325, 190, 120),
    # --- inside sandbox B — the integration kept ---------------------------------
    ("integ_b",  "process", "Integration B\n(third-party)",                  760,  585, 180, 115),
    ("ha_min_b", "process", "Stripped Home Assistant\na separate instance,\nseparately empty",
                                                                            960,  595, 190, 110),
    # --- on disk — secrets and entries kept; two stores are new ------------------
    ("secrets",  "store", "secrets.yaml\n+ config directory (A3)",           420,  830, 215,  85),
    ("entries",  "store", "Config entry store\nevery integration's\ncredentials (A3, A6)",
                                                                            760,  830, 215, 100),
    ("manifest", "store", "Manifest store\nthe author's, in the integration\n"
                          "directory, + the operator's,\nordered (§5.9.4)",  140,  830, 215, 100),
    ("audit",    "store", "Audit record\nhash-chained, attributed\n(A7, §5.12)",
                                                                            140,  960, 215, 100),
]

# Figure 4.1's single container becomes three. Each label says what the box IS; none of them
# claims protection the boundary curves do not also carry.
BOXES = [
    {"id": "ha_proc",   "label": "HOME ASSISTANT PROCESS",
     "x": 348, "y": 318, "width": 222, "height": 185},
    {"id": "sandbox_a", "label": "SANDBOX A — its own namespaces, seccomp, cgroup v2",
     "x": 750, "y": 285, "width": 405, "height": 205},
    {"id": "sandbox_b", "label": "SANDBOX B — identically constructed, sharing nothing",
     "x": 750, "y": 552, "width": 405, "height": 200},
]

# id: (name, source, target, [vertices], exists, label_xy)
# All six now read EXISTS or UNCHANGED. `exists` still drives colour in the SVG only; the
# words are what survive a greyscale printout.
BOUNDARIES = [
    ("tb4", "TB4 · UNCHANGED — structure, not behaviour",
     (25, 240), (335, 25), [(210, 245), (300, 195)], True, (185, 212)),
    ("tb2", "TB2 · UNCHANGED — still unscoped (R3)",
     (570, 330), (570, 520), [(562, 425)], True, (455, 300)),
    ("tb1", "TB1 · EXISTS — the socket (§5.11.2)",
     (749, 300), (749, 745), [(741, 520)], True, (1330, 250)),
    ("tb3", "TB3 · EXISTS — proxied egress (§5.11.1)",
     (1195, 30), (1195, 900), [(1205, 400), (1195, 650)], True, (1300, 470)),
    ("tb5", "TB5 · EXISTS — mount namespace (§5.7.3)",
     (740, 800), (1195, 800), [(960, 810)], True, (960, 775)),
    ("tb6", "TB6 · EXISTS — separate processes (§5.7.3)",
     (748, 520), (1160, 520), [(950, 512)], True, (950, 520)),
]

# (id, source, target, label, source_port, target_port, bidirectional, [vertices], label_xy)
# A primed name — F2′, F3′ — replaces the same-numbered flow in Figure 4.1. Figure 4.1's
# F4b, F5, F6, F8 and F9 have no counterpart here, and that is the point.
FLOWS = [
    ("f1",  "author",  "secrets", "F1  installs / updates integration\nsource, the author manifest with it",
     "bottom", "left",  False, [(180, 760)], (270, 640)),
    ("f10", "user",    "ha_core", "F10  web UI",
     "right",  "left",  True,  [], (292, 435)),
    ("fsup", "supervisor", "ha_min_a", "S  constructs the sandbox before any integration\n"
                                       "code runs: namespaces, mounts, cgroup, and the\n"
                                       "socket pair — identity precedes execution (§5.11.2)",
     "right", "top", False, [(1055, 213)], (960, 215)),
    ("f2p", "integ_a", "mediator", "F2′  the socket — every mediated request (T02, §5.11.2)",
     "left", "right", True, [], (770, 332)),
    ("f2pp", "integ_b", "mediator", "F2′′  B's own socket pair: a different\nsocket, therefore a different identity",
     "left", "bottom", True, [(700, 642), (700, 505)], (620, 662)),
    ("f3p", "mediator", "ha_core", "F3′  the mediator applies permitted effects\n"
                                   "using its OWN credential (S2, §5.11.3 step 5)",
     "left", "right", False, [], (460, 560)),
    ("f7p", "mediator", "extnet", "F7′  proxied egress — the mediator resolves,\n"
                                  "pins the address, then connects (T11, §5.11.1)",
     "top", "left", False, [(652, 115)], (900, 90)),
    ("f4p", "integ_a", "ha_min_a", "F4′  imports the REAL helper layer;\nthe hass it gets is local and empty",
     "right", "left", True, [], (1040, 468)),
    ("f4pp", "integ_b", "ha_min_b", "F4′′  the same, privately",
     "right", "left", True, [], (1050, 725)),
    ("fman", "manifest", "mediator", "F  manifest read at\nsandbox construction\n(§5.9.4, §5.12.2)",
     "top", "bottom", False, [(247, 690), (600, 690), (600, 530)], (350, 730)),
    ("faud", "mediator", "audit", "F  every decision recorded:\nintegration, capability, verdict\n(S7, §5.12.3)",
     "bottom", "left", False, [(690, 780), (90, 780), (90, 1010)], (560, 802)),
]

NOTES = [
    "Compare with Figure 4.1. Five flows drawn there are absent here — F4b (the shared"
    " hass.data dict), F5 (reads any integration's stored credentials), F6 (arbitrary file read"
    " via hass.config.path),\nF8 (direct object access between integrations) and F9 (local"
    " network access). None of the five is refused by a check. The config entry store and"
    " secrets.yaml are not in the sandbox's\nmount namespace, the two integrations are separate"
    " processes, and non-public destinations are denied by default, so there is no request to"
    " make (§5.6.2, §5.10.2, §5.11.1).",

    "TB5 and TB6 are crossed by no flow at all, and that is deliberate rather than an omission:"
    " in Figure 4.1 those same two locations carried F5, F6, F8, F4b and F9. A boundary nothing"
    " crosses is the\nstrongest form this design produces, because nothing has to decide"
    " correctly for it to hold.",

    "TB2 is unchanged, and the figure says so rather than quietly upgrading it. The mediator"
    " holds a Home Assistant long-lived token, which the platform issues with no read-only and"
    " no per-domain\nvariant, so its credential is exactly as unscoped as the one an integration"
    " holds today. That is residual risk R3 (§4.11) — the one boundary of the six this design"
    " does not improve.",
]

# --------------------------------------------------------------------------------------
# 2. Threat Dragon model
# --------------------------------------------------------------------------------------

def _uid(name):
    """Stable UUID per element name, so re-running does not churn the JSON."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"td:fig51:{name}"))


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
            "title": "Home Assistant confined — the design of Ch. 5 (§5.14)",
            "owner": "Younes Rahati",
            "id": 0,
            "description": (
                "Figure 5.1 of the capstone report: the design of Chapter 5, drawn on the "
                "same canvas as Figure 4.1 so the delta is legible. VISUALISATION ONLY — no "
                "threats are enumerated here; they are derived in §4.8 by STRIDE per "
                "boundary within an ISO 31000 process (§4.1), and Threat Dragon's own threat "
                "generator was not used. All six boundaries now read EXISTS or UNCHANGED; "
                "TB2 is UNCHANGED on purpose and carries residual risk R3. Generated by "
                "figures/fig_5_1_confined.py; edit that script rather than this file."
            ),
        },
        "detail": {
            "contributors": [],
            "diagrams": [{
                "id": 0,
                "title": "Home Assistant confined — Ch. 5 design",
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

    # containers — one per process group. Figure 4.1 had exactly one, and that is the
    # single most visible difference between the two drawings.
    for b in BOXES:
        p.append(f'<rect x="{b["x"]}" y="{b["y"]}" width="{b["width"]}" '
                 f'height="{b["height"]}" fill="#f7f7f7" stroke="{INK}" stroke-width="3" '
                 f'stroke-dasharray="12 6" rx="6"/>')
        # Left-aligned, so the top of each box stays free for the boundary labels.
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
    lx, ly = 420, 952
    p.append(f'<rect x="{lx}" y="{ly}" width="740" height="96" fill="#ffffff" '
             f'stroke="{MUTED}" stroke-width="1" rx="4"/>')
    p.append(text_lines(lx + 16, ly + 20, "6 of 6 boundaries enforced — in Figure 4.1, four "
                        "of the six were absent", size=14, fill=PRESENT, weight="bold",
                        anchor="start"))
    p.append(f'<line x1="{lx + 16}" y1="{ly + 46}" x2="{lx + 56}" y2="{ly + 46}" '
             f'stroke="{PRESENT}" stroke-width="2.5" stroke-dasharray="10 7"/>')
    p.append(text_lines(lx + 66, ly + 46, "EXISTS — this design puts an enforcement point "
                        "here; in Figure 4.1 there was none", size=11, fill=PRESENT,
                        anchor="start"))
    p.append(f'<line x1="{lx + 16}" y1="{ly + 66}" x2="{lx + 56}" y2="{ly + 66}" '
             f'stroke="{PRESENT}" stroke-width="2.5" stroke-dasharray="10 7"/>')
    p.append(text_lines(lx + 66, ly + 66, "UNCHANGED — the boundary existed in Figure 4.1, "
                        "and this design does not improve it", size=11, fill=MUTED,
                        anchor="start"))
    p.append(text_lines(lx + 66, ly + 86, "F2\u2032 \u00b7 F3\u2032 \u00b7 F4\u2032 \u00b7 "
                        "F7\u2032 — a primed flow replaces the same-numbered flow of Figure 4.1",
                        size=11, fill=INK, anchor="start"))

    # notes, below the drawing where they cannot collide with a flow label
    for i, text in enumerate(NOTES):
        p.append(text_lines(40, 1105 + i * 62, text, size=10.5, fill=MUTED, anchor="start"))

    p.append("</svg>")
    return "\n".join(p)


if __name__ == "__main__":
    (OUT / "fig_5_1_confined.json").write_text(
        json.dumps(build_model(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT / "fig_5_1_confined.svg").write_text(render_svg(), encoding="utf-8")
    print(f"wrote fig_5_1_confined.json  "
          f"({len(build_model()['detail']['diagrams'][0]['cells'])} cells)")
    print("wrote fig_5_1_confined.svg")

    try:
        import cairosvg  # optional: SVG is the figure of record, PNG is a convenience
        cairosvg.svg2png(url=str(OUT / "fig_5_1_confined.svg"),
                         write_to=str(OUT / "fig_5_1_confined.png"),
                         output_width=1600, background_color="white")
        print("wrote fig_5_1_confined.png")
    except ImportError:
        print("cairosvg not installed — skipped PNG (the SVG is the figure of record)")

    # ------------------------------------------------------------------------------
    # Checks that stop a wrong figure being committed. Figure 4.1's script asserts that
    # four of six boundaries are absent; this one asserts the complement, and two more
    # things the caption of §5.14 states in words.
    # ------------------------------------------------------------------------------
    absent = [b[1] for b in BOUNDARIES if not b[5]]
    assert not absent, f"§5.14 says every boundary is now enforced: {absent}"
    assert len(BOUNDARIES) == 6, "six boundaries, the same six as §4.6"

    unchanged = sorted(b[0] for b in BOUNDARIES if "UNCHANGED" in b[1])
    assert unchanged == ["tb2", "tb4"], (
        "§5.14 and the third note say TB2 and TB4 are the boundaries this design does not "
        f"improve; the figure now says {unchanged}")

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

    print(f"boundaries: 6 enforced, 0 absent  ({', '.join(unchanged)} unchanged)")
    print("TB5 and TB6 crossed by no flow: verified")
