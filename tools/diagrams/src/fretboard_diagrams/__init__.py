"""Chord and fretboard diagrams rendered to inline SVG at build time.

Zensical/SuperFences call :func:`fretboard_fence` and :func:`chord_fence` for the
``fretboard`` and ``chord`` fences configured in ``zensical.toml``. SuperFences calls a
formatter positionally as ``(src, language, class_name, options, md)`` plus attribute
keywords; the renderers only need the body.
"""

from __future__ import annotations

from typing import Any

from pymdownx.superfences import SuperFencesException

from .parse import parse_chord, parse_fretboard
from .svg import render_chord, render_fretboard

__all__ = ["chord_fence", "fretboard_fence"]


def _wrap(svg: str) -> str:
    """Wrap in a block-level element so Markdown does not put each diagram in a ``<p>``.

    Consecutive wrappers are inline-block (see diagrams.css), so diagrams written with
    blank lines between them still sit side by side and wrap on narrow screens.
    """
    return f'<div class="fb-wrap">{svg}</div>'


def fretboard_fence(
    src: str, language: str, class_name: str, options: dict[str, Any], md: Any, **kwargs: Any
) -> str:
    """SuperFences ``format`` callable for ``fretboard`` blocks."""
    try:
        return _wrap(render_fretboard(parse_fretboard(src)))
    except Exception as exc:  # SuperFences swallows anything else and renders a code block
        raise SuperFencesException(f"fretboard diagram: {exc}") from exc


def chord_fence(
    src: str, language: str, class_name: str, options: dict[str, Any], md: Any, **kwargs: Any
) -> str:
    """SuperFences ``format`` callable for ``chord`` blocks."""
    try:
        return _wrap(render_chord(parse_chord(src)))
    except Exception as exc:  # SuperFences swallows anything else and renders a code block
        raise SuperFencesException(f"chord diagram: {exc}") from exc
