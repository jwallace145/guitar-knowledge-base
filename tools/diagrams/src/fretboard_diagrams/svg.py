"""Render diagram models to SVG. Geometry only; all styling comes from CSS classes."""

from __future__ import annotations

from xml.sax.saxutils import escape, quoteattr

from .model import MAX_FRET, Chord, Dot, Fretboard

# Fretboard (horizontal) geometry, in SVG user units (CSS px).
FB_STRING_GAP = 20
FB_FRET_W = 40
FB_PAD = 24
FB_OPEN_AREA = 26
# Chord (vertical) geometry.
CH_STRING_GAP = 22
CH_FRET_H = 26
CH_PAD = 30
CH_MIN_FRETS = 4
DOT_R = 8.5
INLAY_SINGLE = frozenset({3, 5, 7, 9, 15, 17, 19, 21})
INLAY_DOUBLE = frozenset({12, 24})


def _n(value: float) -> str:
    return f"{value:g}"


def _cls(base: str, color: str) -> str:
    return f"{base} fb-{color}" if color else base


def _line(cls: str, x1: float, y1: float, x2: float, y2: float, style: str = "") -> str:
    extra = f' style="{style}"' if style else ""
    return f'<line class="{cls}" x1="{_n(x1)}" y1="{_n(y1)}" x2="{_n(x2)}" y2="{_n(y2)}"{extra}/>'


def _text(cls: str, x: float, y: float, text: str, anchor: str = "middle") -> str:
    return f'<text class="{cls}" x="{_n(x)}" y="{_n(y)}" text-anchor="{anchor}">{escape(text)}</text>'


def _dot(dot: Dot, cx: float, cy: float, r: float = DOT_R) -> str:
    out = f'<circle class="{_cls("fb-dot", dot.color)}" cx="{_n(cx)}" cy="{_n(cy)}" r="{_n(r)}"/>'
    if dot.label:
        out += _text("fb-label", cx, cy + 3.5, dot.label)
    return out


# ---------------------------------------------------------------------------
# Fretboard


def fretboard_window(fb: Fretboard) -> tuple[int, int]:
    """Visible fret range: explicit, else fitted to the dots and at least four wide."""
    if fb.window is not None:
        return fb.window
    fretted = [d.fret for d in fb.dots if d.fret > 0]
    if not fretted:
        return 1, 4
    lo, hi = min(fretted), max(fretted)
    if hi - lo < 3:
        hi = lo + 3
    if hi > MAX_FRET:
        lo, hi = MAX_FRET - 3, MAX_FRET
    return lo, hi


def render_fretboard(fb: Fretboard) -> str:
    """Horizontal neck diagram, high e on top."""
    lo, hi = fretboard_window(fb)
    nfrets = hi - lo + 1
    has_nut = lo == 1 or any(d.fret == 0 for d in fb.dots)
    x0 = FB_PAD + (FB_OPEN_AREA if has_nut else 0)
    top = 30 if fb.title else 16
    bottom = top + FB_STRING_GAP * 5
    width = x0 + FB_FRET_W * nfrets + FB_PAD
    height = bottom + 30
    label = fb.title or "Fretboard diagram"

    def string_y(string: int) -> float:
        return top + FB_STRING_GAP * (5 - string)

    def fret_x(fret: int) -> float:
        return x0 + FB_FRET_W * (fret - lo) + FB_FRET_W / 2

    out = [
        f'<svg class="fb fb-fretboard" viewBox="0 0 {_n(width)} {_n(height)}" '
        f'width="{_n(width)}" height="{_n(height)}" role="img" aria-label={quoteattr(label)}>'
    ]
    if fb.title:
        out.append(_text("fb-title", x0, 14, fb.title, anchor="start"))
    for i in range(nfrets + 1):
        x = x0 + FB_FRET_W * i
        out.append(_line("fb-fret", x, top, x, bottom))
    if has_nut:
        out.append(_line("fb-nut", x0, top, x0, bottom))
    for s in range(6):
        y = string_y(s)
        out.append(
            _line(
                "fb-string", x0, y, x0 + FB_FRET_W * nfrets, y,
                style=f"stroke-width:{_n(0.8 + (5 - s) * 0.25)}",
            )
        )
    for fret in range(lo, hi + 1):
        x = fret_x(fret)
        if fret in INLAY_DOUBLE:
            out.append(f'<circle class="fb-inlay" cx="{_n(x)}" cy="{_n(top + FB_STRING_GAP * 1.5)}" r="3"/>')
            out.append(f'<circle class="fb-inlay" cx="{_n(x)}" cy="{_n(top + FB_STRING_GAP * 3.5)}" r="3"/>')
        elif fret in INLAY_SINGLE:
            out.append(f'<circle class="fb-inlay" cx="{_n(x)}" cy="{_n(top + FB_STRING_GAP * 2.5)}" r="3"/>')
        out.append(_text("fb-fretnum", x, bottom + 18, str(fret)))
    for dot in fb.dots:
        cx = x0 - FB_OPEN_AREA / 2 if dot.fret == 0 else fret_x(dot.fret)
        out.append(_dot(dot, cx, string_y(dot.string)))
    out.append("</svg>")
    return "".join(out)
