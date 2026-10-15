"""Diagram data model. Parsers build these; the renderer consumes them."""

from __future__ import annotations

from dataclasses import dataclass

PALETTE: tuple[str, ...] = ("red", "orange", "yellow", "green", "blue", "purple", "grey")
STRINGS: tuple[str, ...] = ("E", "A", "D", "G", "B", "e")  # index 0 is the low E
MAX_FRET = 24


@dataclass(frozen=True)
class Dot:
    """One marked note. ``string`` is 0 (low E) to 5 (high e); ``fret`` 0 is open."""

    string: int
    fret: int
    label: str = ""
    color: str = ""  # "" or a PALETTE name


@dataclass(frozen=True)
class Fretboard:
    """A horizontal neck diagram."""

    dots: tuple[Dot, ...]
    title: str = ""
    window: tuple[int, int] | None = None  # explicit lo-hi fret range


@dataclass(frozen=True)
class Chord:
    """A vertical chord box. ``strings`` has six entries, low to high; None is muted."""

    strings: tuple[Dot | None, ...]
    name: str = ""
    barre: int | None = None
