"""Drawing primitives shared by the five Section 9 figures (fig_9_1 … fig_9_5).

Figures 4.1 and 5.1 each carry their own renderer, because each also writes a Threat Dragon
model. The Section 9 figures are architecture drawings with no model behind them, so they share
this one small renderer instead of repeating it five times.

The rules are Figure 4.1's: greyscale only, and every distinction carried in words rather than
in colour or symbols, because colour does not survive a greyscale printout and a symbol does not
survive a font that lacks it. Three greys are used for fill, and they mean nothing on their own;
a dashed outline marks a boundary, a solid one a component.
"""

INK, MUTED = "#1a1a1a", "#555555"
FILL = {"none": "none", "white": "#ffffff", "light": "#f3f3f3", "mid": "#e2e2e2",
        "dark": "#c8c8c8"}
FONT = "Helvetica,Arial,sans-serif"


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class Canvas:
    """An SVG under construction. Coordinates are pixels from the top left."""

    def __init__(self, width, height):
        self.width, self.height = width, height
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}">',
            '<rect width="100%" height="100%" fill="#ffffff"/>',
            '<defs><marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
            'markerHeight="7" orient="auto-start-reverse">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{INK}"/></marker></defs>',
        ]

    def text(self, x, y, label, size=13, weight="normal", anchor="middle", fill=INK,
             italic=False):
        """One or more lines, split on newlines, centred vertically on y."""
        lines = label.split("\n")
        step = size + 4
        start = y - (len(lines) - 1) * step / 2
        style = ' font-style="italic"' if italic else ""
        for i, line in enumerate(lines):
            self.parts.append(
                f'<text x="{x:.0f}" y="{start + i * step:.0f}" font-size="{size}" '
                f'font-family="{FONT}" font-weight="{weight}" fill="{fill}"{style} '
                f'text-anchor="{anchor}" dominant-baseline="middle">{esc(line)}</text>')

    def box(self, x, y, w, h, label="", fill="white", dashed=False, size=13,
            weight="normal", stroke=1.5, title=None, title_size=12):
        """A rectangle. `label` is centred in it; `title`, if given, sits at its top left."""
        dash = ' stroke-dasharray="9 5"' if dashed else ""
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="5" fill="{FILL[fill]}" '
            f'stroke="{INK}" stroke-width="{stroke}"{dash}/>')
        if title:
            self.text(x + 12, y + 16, title, size=title_size, weight="bold", anchor="start")
        if label:
            self.text(x + w / 2, y + h / 2 + (8 if title else 0), label, size=size,
                      weight=weight)

    def line(self, points, arrow=True, both=False, dashed=False, width=1.6):
        d = "M " + " L ".join(f"{x:.0f},{y:.0f}" for x, y in points)
        marks = (' marker-end="url(#ar)"' if arrow else "") + \
                (' marker-start="url(#ar)"' if both else "")
        dash = ' stroke-dasharray="6 4"' if dashed else ""
        self.parts.append(f'<path d="{d}" fill="none" stroke="{INK}" '
                          f'stroke-width="{width}"{dash}{marks}/>')

    def label(self, x, y, text, size=12, anchor="middle"):
        """Text on a white ground, so that it stays legible where it crosses a line."""
        lines = text.split("\n")
        w = 0.6 * size * max(len(s) for s in lines) + 10
        h = (size + 4) * len(lines) + 4
        left = {"middle": x - w / 2, "start": x - 5, "end": x - w + 5}[anchor]
        self.parts.append(f'<rect x="{left:.0f}" y="{y - h / 2:.0f}" width="{w:.0f}" '
                          f'height="{h:.0f}" fill="#ffffff"/>')
        self.text(x, y, text, size=size, anchor=anchor)

    def save(self, path):
        path.write_text("\n".join(self.parts + ["</svg>"]) + "\n")
        print(f"wrote {path.name}")
        try:
            import cairosvg  # optional: the SVG is the figure of record; the PNG is Word's fallback
            png = path.with_suffix(".png")
            cairosvg.svg2png(url=str(path), write_to=str(png), output_width=1600,
                             background_color="white")
            print(f"wrote {png.name}")
        except ImportError:
            print("cairosvg not installed — skipped PNG (the SVG is the figure of record)")
