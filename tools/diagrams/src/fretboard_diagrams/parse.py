"""Parse fence bodies into diagram models. Knows nothing about SVG."""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from dataclasses import replace

from .model import MAX_FRET, PALETTE, STRINGS, Chord, Dot, Fretboard


class DiagramError(ValueError):
    """A fence body that cannot be turned into a diagram."""


_DOT_RE = re.compile(r"^(\d+)(?::([^:@\s]+))?(?:@([^:@\s]+))?$")
_WINDOW_RE = re.compile(r"^(\d+)-(\d+)$")
_PALETTE_HINT = "expected one of " + ", ".join(PALETTE)


def entries(source: str) -> Iterator[tuple[int, str, str]]:
    """Yield ``(line_number, key, value)`` for each non-blank, non-comment line."""
    for number, raw in enumerate(source.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition(":")
        key = key.strip()
        if not sep or not key or " " in key:
            raise DiagramError(f"line {number}: expected 'key: value', got {line!r}")
        yield number, key, value.strip()


def parse_dot_token(token: str) -> tuple[int, str, str]:
    """Parse ``fret[:label][@color]`` into ``(fret, label, color)``."""
    match = _DOT_RE.match(token)
    if not match:
        raise DiagramError(f"bad dot {token!r}: expected fret[:label][@color]")
    fret = int(match.group(1))
    if fret > MAX_FRET:
        raise DiagramError(f"bad dot {token!r}: fret must be 0-{MAX_FRET}")
    label = match.group(2) or ""
    color = match.group(3) or ""
    if color and color not in PALETTE:
        raise DiagramError(f"bad dot {token!r}: unknown color {color!r}, {_PALETTE_HINT}")
    return fret, label, color


def parse_color_rules(value: str) -> dict[str, str]:
    """Parse ``label=color label=color ...`` into a mapping."""
    rules: dict[str, str] = {}
    for item in value.split():
        label, sep, color = item.partition("=")
        if not sep or not label or not color:
            raise DiagramError(f"bad color rule {item!r}: expected label=color")
        if color not in PALETTE:
            raise DiagramError(f"bad color rule {item!r}: unknown color {color!r}, {_PALETTE_HINT}")
        rules[label] = color
    return rules


def parse_window(value: str) -> tuple[int, int]:
    """Parse ``lo-hi`` into a fret window with 1 <= lo <= hi <= MAX_FRET."""
    match = _WINDOW_RE.match(value)
    if not match:
        raise DiagramError(f"bad frets {value!r}: expected lo-hi, for example 5-8")
    lo, hi = int(match.group(1)), int(match.group(2))
    if not 1 <= lo <= hi <= MAX_FRET:
        raise DiagramError(f"bad frets {value!r}: need 1 <= lo <= hi <= {MAX_FRET}")
    return lo, hi


def apply_rules(dots: Iterable[Dot | None], rules: dict[str, str]) -> tuple[Dot | None, ...]:
    """Color dots by label rule unless they already carry an explicit color."""
    out: list[Dot | None] = []
    for dot in dots:
        if dot is not None and not dot.color and dot.label in rules:
            dot = replace(dot, color=rules[dot.label])
        out.append(dot)
    return tuple(out)


def _prefixed(number: int, func, *args):
    try:
        return func(*args)
    except DiagramError as exc:
        raise DiagramError(f"line {number}: {exc}") from None


def parse_fretboard(source: str) -> Fretboard:
    """Parse a ``fretboard`` fence body."""
    title = ""
    window: tuple[int, int] | None = None
    rules: dict[str, str] = {}
    dots: list[Dot] = []
    seen: set[str] = set()
    for number, key, value in entries(source):
        if key == "title":
            title = value
        elif key == "frets":
            window = _prefixed(number, parse_window, value)
        elif key == "color":
            rules = _prefixed(number, parse_color_rules, value)
        elif key in STRINGS:
            if key in seen:
                raise DiagramError(f"line {number}: string {key} given twice")
            seen.add(key)
            string = STRINGS.index(key)
            for token in value.split():
                fret, label, color = _prefixed(number, parse_dot_token, token)
                dots.append(Dot(string, fret, label, color))
        else:
            raise DiagramError(
                f"line {number}: unknown key {key!r} "
                "(expected title, frets, color, or a string E A D G B e)"
            )
    if window is not None:
        lo, hi = window
        for dot in dots:
            if dot.fret and not lo <= dot.fret <= hi:
                raise DiagramError(
                    f"fret {dot.fret} on string {STRINGS[dot.string]} is outside frets {lo}-{hi}"
                )
    colored = apply_rules(dots, rules)
    return Fretboard(dots=tuple(d for d in colored if d is not None), title=title, window=window)
