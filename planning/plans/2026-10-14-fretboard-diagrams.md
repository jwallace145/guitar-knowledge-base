# Fretboard Diagrams Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render `fretboard` and `chord` fenced blocks in the site's Markdown to styled inline SVG at build time.

**Architecture:** A small Python package (`fretboard_diagrams`) in a uv workspace member parses the fence body into frozen dataclasses, renders them to SVG with CSS classes only, and exposes two SuperFences `format` callables that Zensical loads by dotted path. One stylesheet in `docs/assets/stylesheets/` styles every diagram, using Material's color variables so light and dark mode both work.

**Tech Stack:** Python 3.11+, hatchling, uv workspaces, pymdown-extensions SuperFences, pytest, Zensical 0.0.70.

**Spec:** `planning/specs/2026-10-14-fretboard-diagrams-design.md`

## Global Constraints

- Commit messages are one line, Conventional Commits, max 100 chars, no body (AGENTS.md).
- Never push to `main`; all work on branch `feat/fretboard-diagrams`.
- `uv run zensical build --strict` must pass before the PR is opened.
- No new runtime dependencies beyond what Zensical already pulls in (`pymdown-extensions`, `markdown`).
- Do not edit `CHANGELOG.md`, `version.txt`, or the version in `pyproject.toml`.
- Palette names are exactly `red orange yellow green blue purple grey`.
- Dot token grammar is `fret[:label][@color]`; string keys are `E A D G B e`.
- `fretboard` dots have no default label; `chord` dots default to the finger number.

## Review Focus

- A dot token like `8:C#` (sharp in a label): must parse, `#` is only a comment at line start. Pinned in Task 2.
- A `chord` with `fingers:` but muted/open strings in the same slots: finger tokens there must be ignored, not applied. Pinned in Task 4.
- A `fretboard` whose highest fret exceeds 24 after the four-fret widening (e.g. only dot at 23): window must clamp to 21–24. Pinned in Task 5.
- A label containing `<` or `&`: must be escaped in the SVG, never emitted raw. Pinned in Task 5.
- A fence body with Windows line endings or trailing spaces: must parse like a clean one. Pinned in Task 3.

---

### Task 1: Package scaffold and test wiring

**Files:**
- Create: `tools/diagrams/pyproject.toml`
- Create: `tools/diagrams/src/fretboard_diagrams/__init__.py`
- Create: `tools/diagrams/tests/test_package.py`
- Modify: `pyproject.toml`
- Modify: `.github/workflows/ci.yml` (add a pytest step after `uv sync`)

**Interfaces:**
- Produces: importable package `fretboard_diagrams`; `uv run pytest` runs `tools/diagrams/tests`.

- [ ] **Step 1: Write the failing test**

`tools/diagrams/tests/test_package.py`:
```python
def test_package_imports():
    import fretboard_diagrams

    assert fretboard_diagrams.__name__ == "fretboard_diagrams"
```

- [ ] **Step 2: Run it to see it fail**

Run: `uv run pytest` — Expected: error, pytest not installed or module not found.

- [ ] **Step 3: Create the workspace member**

`tools/diagrams/pyproject.toml`:
```toml
[project]
name = "fretboard-diagrams"
version = "0.0.0"
description = "Build-time SVG chord and fretboard diagrams for the Guitar Knowledge Base"
requires-python = ">=3.11"
dependencies = ["pymdown-extensions"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/fretboard_diagrams"]
```

`tools/diagrams/src/fretboard_diagrams/__init__.py`:
```python
"""Chord and fretboard diagrams rendered to inline SVG at build time."""
```

Root `pyproject.toml` becomes:
```toml
[project]
name = "guitar-knowledge-base"
version = "0.1.0" # x-release-please-version
description = "A guitar theory and study knowledge base, built with Zensical"
readme = "README.md"
license = "MIT"
requires-python = ">=3.11"
dependencies = [
    "zensical==0.0.70",
    "fretboard-diagrams",
]

[dependency-groups]
dev = ["pytest>=8"]

[tool.uv.workspace]
members = ["tools/diagrams"]

[tool.uv.sources]
fretboard-diagrams = { workspace = true }

[tool.pytest.ini_options]
testpaths = ["tools/diagrams/tests"]
```

In `.github/workflows/ci.yml`, after `- run: uv sync --frozen` in the `build` job add:
```yaml
      - run: uv run pytest
```

- [ ] **Step 4: Sync and run the test**

Run: `uv sync && uv run pytest -q` — Expected: 1 passed. `uv.lock` is updated; `git status` shows it modified.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock tools .github/workflows/ci.yml
git commit -m "build: add fretboard-diagrams workspace package and pytest"
```

---

### Task 2: Model and dot-token parsing

**Files:**
- Create: `tools/diagrams/src/fretboard_diagrams/model.py`
- Create: `tools/diagrams/src/fretboard_diagrams/parse.py`
- Create: `tools/diagrams/tests/test_parse_tokens.py`

**Interfaces:**
- Produces: `model.PALETTE: tuple[str, ...]`, `model.STRINGS == ("E","A","D","G","B","e")`, `model.MAX_FRET == 24`, `model.Dot(string:int, fret:int, label:str="", color:str="")`, `model.Fretboard(dots:tuple[Dot,...], title:str="", window:tuple[int,int]|None=None)`, `model.Chord(strings:tuple[Dot|None,...], name:str="", barre:int|None=None)`.
- Produces: `parse.DiagramError(ValueError)`, `parse.parse_dot_token(token) -> (fret, label, color)`, `parse.parse_color_rules(value) -> dict[str,str]`, `parse.parse_window(value) -> (lo, hi)`, `parse.apply_rules(dots, rules)`.

- [ ] **Step 1: Write the failing tests**

`tools/diagrams/tests/test_parse_tokens.py`:
```python
import pytest

from fretboard_diagrams.model import Dot
from fretboard_diagrams.parse import (
    DiagramError,
    apply_rules,
    parse_color_rules,
    parse_dot_token,
    parse_window,
)


@pytest.mark.parametrize(
    "token, expected",
    [
        ("8", (8, "", "")),
        ("0", (0, "", "")),
        ("8:1", (8, "1", "")),
        ("8@red", (8, "", "red")),
        ("8:1@red", (8, "1", "red")),
        ("8:C#", (8, "C#", "")),
        ("10:b3@blue", (10, "b3", "blue")),
        ("24", (24, "", "")),
    ],
)
def test_dot_token_grammar(token, expected):
    assert parse_dot_token(token) == expected


@pytest.mark.parametrize(
    "token, message",
    [
        ("x", "expected fret[:label][@color]"),
        ("8:", "expected fret[:label][@color]"),
        ("8@", "expected fret[:label][@color]"),
        ("8@red:1", "expected fret[:label][@color]"),
        ("25", "fret must be 0-24"),
        ("8@pink", "unknown color 'pink'"),
    ],
)
def test_dot_token_errors(token, message):
    with pytest.raises(DiagramError, match=message):
        parse_dot_token(token)


def test_color_rules():
    assert parse_color_rules("1=red 3=blue 5=green") == {"1": "red", "3": "blue", "5": "green"}
    assert parse_color_rules("") == {}


@pytest.mark.parametrize("value", ["1", "=red", "1=", "1=pink"])
def test_color_rule_errors(value):
    with pytest.raises(DiagramError):
        parse_color_rules(value)


def test_apply_rules_respects_explicit_color():
    dots = (Dot(0, 8, "1"), Dot(1, 8, "1", "blue"), Dot(2, 8, "3"), Dot(3, 8))
    out = apply_rules(dots, {"1": "red"})
    assert [d.color for d in out] == ["red", "blue", "", ""]


def test_window():
    assert parse_window("7-10") == (7, 10)
    assert parse_window("1-24") == (1, 24)


@pytest.mark.parametrize("value", ["7", "10-7", "0-4", "20-25", "a-b"])
def test_window_errors(value):
    with pytest.raises(DiagramError):
        parse_window(value)
```

- [ ] **Step 2: Run to see them fail**

Run: `uv run pytest tools/diagrams/tests/test_parse_tokens.py -q` — Expected: ImportError.

- [ ] **Step 3: Implement model and token parsing**

`tools/diagrams/src/fretboard_diagrams/model.py`:
```python
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
```

`tools/diagrams/src/fretboard_diagrams/parse.py`:
```python
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
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tools/diagrams/tests/test_parse_tokens.py -q` — Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add tools/diagrams
git commit -m "feat(diagrams): add diagram model and dot token parser"
```

---

### Task 3: `fretboard` parser

**Files:**
- Modify: `tools/diagrams/src/fretboard_diagrams/parse.py` (append)
- Create: `tools/diagrams/tests/test_parse_fretboard.py`

**Interfaces:**
- Consumes: Task 2 helpers.
- Produces: `parse.parse_fretboard(source: str) -> Fretboard`.

- [ ] **Step 1: Write the failing tests**

`tools/diagrams/tests/test_parse_fretboard.py`:
```python
import pytest

from fretboard_diagrams.model import Dot
from fretboard_diagrams.parse import DiagramError, parse_fretboard

C_MAJOR = """
title: C major, position 1
frets: 7-10
color: 1=red
E: 8:1 10:2
A: 7:3 8:4 10:5
D: 7:6 9:7 10:1
G: 7:2 9:3 10:4
B: 8:5 10:6
e: 7:7 8:1 10:2
"""


def test_parses_full_example():
    fb = parse_fretboard(C_MAJOR)
    assert fb.title == "C major, position 1"
    assert fb.window == (7, 10)
    assert len(fb.dots) == 15
    assert fb.dots[0] == Dot(0, 8, "1", "red")
    assert fb.dots[1] == Dot(0, 10, "2", "")
    assert fb.dots[-1] == Dot(5, 10, "2", "")
    assert sum(d.color == "red" for d in fb.dots) == 3


def test_minimal_block_has_no_defaults():
    fb = parse_fretboard("A: 3 5")
    assert fb.title == ""
    assert fb.window is None
    assert fb.dots == (Dot(1, 3), Dot(1, 5))


def test_explicit_color_beats_rule():
    fb = parse_fretboard("color: 1=red\nE: 8:1@blue 10:1")
    assert [d.color for d in fb.dots] == ["blue", "red"]


def test_comments_blank_lines_and_crlf():
    fb = parse_fretboard("# a comment\r\n\r\nE: 8   \r\n  A: 7\r\n")
    assert fb.dots == (Dot(0, 8), Dot(1, 7))


def test_open_string_allowed_with_window():
    fb = parse_fretboard("frets: 1-4\nE: 0 3")
    assert fb.dots == (Dot(0, 0), Dot(0, 3))


@pytest.mark.parametrize(
    "source, message",
    [
        ("E: 8\nE: 10", "line 2: string E given twice"),
        ("X: 8", "unknown key 'X'"),
        ("E 8", "expected 'key: value'"),
        ("E: 8:1@pink", "line 1: bad dot '8:1@pink'"),
        ("frets: 7-10\nE: 12", "fret 12 on string E is outside frets 7-10"),
        ("frets: 10-7", "bad frets"),
        ("color: 1=pink", "line 1: bad color rule"),
    ],
)
def test_errors(source, message):
    with pytest.raises(DiagramError, match=message):
        parse_fretboard(source)
```

- [ ] **Step 2: Run to see them fail**

Run: `uv run pytest tools/diagrams/tests/test_parse_fretboard.py -q` — Expected: ImportError on `parse_fretboard`.

- [ ] **Step 3: Implement**

Append to `parse.py`:
```python
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
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tools/diagrams/tests -q` — Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add tools/diagrams
git commit -m "feat(diagrams): parse fretboard fence bodies"
```

---

### Task 4: `chord` parser

**Files:**
- Modify: `tools/diagrams/src/fretboard_diagrams/parse.py` (append)
- Create: `tools/diagrams/tests/test_parse_chord.py`

**Interfaces:**
- Produces: `parse.parse_chord(source: str) -> Chord`.

- [ ] **Step 1: Write the failing tests**

`tools/diagrams/tests/test_parse_chord.py`:
```python
import pytest

from fretboard_diagrams.model import Dot
from fretboard_diagrams.parse import DiagramError, parse_chord


def test_open_c():
    ch = parse_chord("name: C\nfrets: x 3@red 2 0 1@red 0\nfingers: - 3 2 - 1 -")
    assert ch.name == "C"
    assert ch.barre is None
    assert ch.strings == (
        None,
        Dot(1, 3, "3", "red"),
        Dot(2, 2, "2", ""),
        Dot(3, 0, "", ""),
        Dot(4, 1, "1", "red"),
        Dot(5, 0, "", ""),
    )


def test_barre_f():
    ch = parse_chord("name: F\nfrets: 1 3 3 2 1 1\nfingers: 1 3 4 2 1 1\nbarre: 1")
    assert ch.barre == 1
    assert ch.strings[0] == Dot(0, 1, "1", "")


def test_explicit_label_beats_finger_and_rules_use_final_label():
    ch = parse_chord("frets: x 3:C 2:E 0 1:C 0\nfingers: - 3 2 - 1 -\ncolor: C=red")
    assert ch.strings[1] == Dot(1, 3, "C", "red")
    assert ch.strings[2] == Dot(2, 2, "E", "")


def test_fingers_on_open_and_muted_strings_are_ignored():
    ch = parse_chord("frets: x 0 2 2 1 0\nfingers: 1 1 2 3 1 1")
    assert ch.strings[0] is None
    assert ch.strings[1] == Dot(1, 0, "", "")
    assert ch.strings[2] == Dot(2, 2, "2", "")


def test_no_fingers_means_no_labels():
    ch = parse_chord("frets: x 3 2 0 1 0")
    assert all(d is None or d.label == "" for d in ch.strings)


@pytest.mark.parametrize(
    "source, message",
    [
        ("name: C", "needs a 'frets:' line"),
        ("frets: x 3 2 0 1", "line 1: frets needs six tokens, got 5"),
        ("frets: x 3 2 0 1 0\nfingers: 1 2 3", "line 2: fingers needs six tokens, got 3"),
        ("frets: x 3 2 0 1 0\nfingers: - 5 2 - 1 -", "line 2: bad finger '5'"),
        ("frets: x 3 2 0 1 0\nbarre: 2", "barre at fret 2 but no string is fretted there"),
        ("frets: x 3 2 0 1 0\nbarre: 0", "line 2: bad barre"),
        ("frets: x 3 2 0 1 0\nfoo: 1", "line 2: unknown key 'foo'"),
        ("frets: x y 2 0 1 0", "line 1: bad dot 'y'"),
    ],
)
def test_errors(source, message):
    with pytest.raises(DiagramError, match=message):
        parse_chord(source)
```

- [ ] **Step 2: Run to see them fail**

Run: `uv run pytest tools/diagrams/tests/test_parse_chord.py -q` — Expected: ImportError.

- [ ] **Step 3: Implement**

Append to `parse.py`:
```python
_FINGERS = {"-", "1", "2", "3", "4"}


def _six(number: int, key: str, value: str) -> list[str]:
    tokens = value.split()
    if len(tokens) != 6:
        raise DiagramError(f"line {number}: {key} needs six tokens, got {len(tokens)}")
    return tokens


def parse_chord(source: str) -> Chord:
    """Parse a ``chord`` fence body."""
    name = ""
    frets: list[str] | None = None
    fingers: list[str] | None = None
    frets_line = 0
    barre: int | None = None
    rules: dict[str, str] = {}
    for number, key, value in entries(source):
        if key == "name":
            name = value
        elif key == "frets":
            frets, frets_line = _six(number, key, value), number
        elif key == "fingers":
            fingers = _six(number, key, value)
            for token in fingers:
                if token not in _FINGERS:
                    raise DiagramError(f"line {number}: bad finger {token!r}, expected - or 1-4")
        elif key == "barre":
            if not value.isdigit() or not 1 <= int(value) <= MAX_FRET:
                raise DiagramError(f"line {number}: bad barre {value!r}, expected a fret 1-{MAX_FRET}")
            barre = int(value)
        elif key == "color":
            rules = _prefixed(number, parse_color_rules, value)
        else:
            raise DiagramError(
                f"line {number}: unknown key {key!r} (expected name, frets, fingers, barre, color)"
            )
    if frets is None:
        raise DiagramError("chord needs a 'frets:' line with six tokens (x, 0, or fret[:label][@color])")
    strings: list[Dot | None] = []
    for index, token in enumerate(frets):
        if token == "x":
            strings.append(None)
            continue
        fret, label, color = _prefixed(frets_line, parse_dot_token, token)
        if not label and fret > 0 and fingers is not None and fingers[index] != "-":
            label = fingers[index]
        strings.append(Dot(index, fret, label, color))
    if barre is not None and not any(d is not None and d.fret == barre for d in strings):
        raise DiagramError(f"barre at fret {barre} but no string is fretted there")
    return Chord(strings=apply_rules(strings, rules), name=name, barre=barre)
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tools/diagrams/tests -q` — Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add tools/diagrams
git commit -m "feat(diagrams): parse chord fence bodies"
```

---

### Task 5: Fretboard SVG renderer

**Files:**
- Create: `tools/diagrams/src/fretboard_diagrams/svg.py`
- Create: `tools/diagrams/tests/test_svg_fretboard.py`

**Interfaces:**
- Consumes: `model.Fretboard`, `model.Dot`, `model.MAX_FRET`.
- Produces: `svg.fretboard_window(fb) -> (lo, hi)`, `svg.render_fretboard(fb) -> str`.

- [ ] **Step 1: Write the failing tests**

`tools/diagrams/tests/test_svg_fretboard.py`:
```python
from xml.etree import ElementTree as ET

import pytest

from fretboard_diagrams.model import Dot, Fretboard
from fretboard_diagrams.parse import parse_fretboard
from fretboard_diagrams.svg import fretboard_window, render_fretboard

C_MAJOR = """
title: C major, position 1
frets: 7-10
color: 1=red
E: 8:1 10:2
A: 7:3 8:4 10:5
D: 7:6 9:7 10:1
G: 7:2 9:3 10:4
B: 8:5 10:6
e: 7:7 8:1 10:2
"""


def svg_of(source: str) -> ET.Element:
    return ET.fromstring(render_fretboard(parse_fretboard(source)))


def by_class(root: ET.Element, cls: str) -> list[ET.Element]:
    return [el for el in root.iter() if cls in el.get("class", "").split()]


def test_window_fits_dots_with_minimum_width():
    assert fretboard_window(Fretboard((Dot(0, 5), Dot(1, 6)))) == (5, 8)
    assert fretboard_window(Fretboard((Dot(0, 5), Dot(1, 12)))) == (5, 12)
    assert fretboard_window(Fretboard((Dot(0, 0),))) == (1, 4)
    assert fretboard_window(Fretboard(())) == (1, 4)
    assert fretboard_window(Fretboard((Dot(0, 23),))) == (21, 24)
    assert fretboard_window(Fretboard((Dot(0, 23),), window=(20, 24))) == (20, 24)


def test_structure_of_full_example():
    root = svg_of(C_MAJOR)
    assert root.tag == "svg"
    assert root.get("class") == "fb fb-fretboard"
    assert root.get("role") == "img"
    assert root.get("aria-label") == "C major, position 1"
    assert len(by_class(root, "fb-dot")) == 15
    assert len(by_class(root, "fb-red")) == 3
    assert len(by_class(root, "fb-label")) == 15
    assert len(by_class(root, "fb-string")) == 6
    assert len(by_class(root, "fb-fret")) == 5  # four frets need five wires
    assert [el.text for el in by_class(root, "fb-fretnum")] == ["7", "8", "9", "10"]
    assert not by_class(root, "fb-nut")
    assert by_class(root, "fb-inlay")  # fret 7 and 9 have inlays


def test_nut_and_open_dots():
    root = svg_of("E: 0 3\nA: 2")
    assert len(by_class(root, "fb-nut")) == 1
    assert len(by_class(root, "fb-dot")) == 3
    # the open dot sits left of the nut
    nut_x = float(by_class(root, "fb-nut")[0].get("x1"))
    open_dot = by_class(root, "fb-dot")[0]
    assert float(open_dot.get("cx")) < nut_x


def test_no_title_means_no_title_element_and_generic_label():
    root = svg_of("E: 8")
    assert not by_class(root, "fb-title")
    assert root.get("aria-label") == "Fretboard diagram"


def test_labels_are_escaped():
    out = render_fretboard(Fretboard((Dot(0, 8, "<&"),), title="a<b"))
    assert "<&" not in out.replace("&lt;&amp;", "")
    root = ET.fromstring(out)
    assert by_class(root, "fb-label")[0].text == "<&"
    assert root.get("aria-label") == "a<b"


def test_every_dot_inside_viewbox():
    root = svg_of(C_MAJOR)
    _, _, w, h = (float(v) for v in root.get("viewBox").split())
    for el in by_class(root, "fb-dot"):
        cx, cy, r = (float(el.get(k)) for k in ("cx", "cy", "r"))
        assert 0 <= cx - r and cx + r <= w
        assert 0 <= cy - r and cy + r <= h


def test_twelfth_fret_double_inlay():
    root = svg_of("frets: 10-13\nE: 12")
    assert len(by_class(root, "fb-inlay")) == 2
```

- [ ] **Step 2: Run to see them fail**

Run: `uv run pytest tools/diagrams/tests/test_svg_fretboard.py -q` — Expected: ImportError.

- [ ] **Step 3: Implement**

`tools/diagrams/src/fretboard_diagrams/svg.py`:
```python
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
        out.append(_line("fb-string", x0, y, x0 + FB_FRET_W * nfrets, y,
                         style=f"stroke-width:{_n(0.8 + (5 - s) * 0.25)}"))
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
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tools/diagrams/tests -q` — Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add tools/diagrams
git commit -m "feat(diagrams): render fretboard diagrams to svg"
```

---

### Task 6: Chord SVG renderer

**Files:**
- Modify: `tools/diagrams/src/fretboard_diagrams/svg.py` (append)
- Create: `tools/diagrams/tests/test_svg_chord.py`

**Interfaces:**
- Produces: `svg.chord_window(ch) -> (base_fret, has_nut, nfrets)`, `svg.render_chord(ch) -> str`.

- [ ] **Step 1: Write the failing tests**

`tools/diagrams/tests/test_svg_chord.py`:
```python
from xml.etree import ElementTree as ET

from fretboard_diagrams.parse import parse_chord
from fretboard_diagrams.svg import chord_window, render_chord

OPEN_C = "name: C\nfrets: x 3@red 2 0 1@red 0\nfingers: - 3 2 - 1 -"
BARRE_F = "name: F\nfrets: 1@red 3 3 2 1@red 1@red\nfingers: 1 3 4 2 1 1\nbarre: 1"
HIGH_G = "name: G\nfrets: x x 9 7 8 7\nfingers: - - 3 1 2 1"


def svg_of(source: str) -> ET.Element:
    return ET.fromstring(render_chord(parse_chord(source)))


def by_class(root: ET.Element, cls: str) -> list[ET.Element]:
    return [el for el in root.iter() if cls in el.get("class", "").split()]


def test_window():
    assert chord_window(parse_chord(OPEN_C)) == (1, True, 4)
    assert chord_window(parse_chord(HIGH_G)) == (7, False, 4)
    assert chord_window(parse_chord("frets: x x 5 7 8 10")) == (5, False, 6)
    assert chord_window(parse_chord("frets: 0 0 0 0 0 0")) == (1, True, 4)


def test_open_c_structure():
    root = svg_of(OPEN_C)
    assert root.get("class") == "fb fb-chord"
    assert root.get("aria-label") == "C"
    assert len(by_class(root, "fb-nut")) == 1
    assert len(by_class(root, "fb-mute")) == 1
    assert len(by_class(root, "fb-open")) == 2
    assert len(by_class(root, "fb-dot")) == 3
    assert len(by_class(root, "fb-red")) == 2
    assert [el.text for el in by_class(root, "fb-label")] == ["3", "2", "1"]
    assert not by_class(root, "fb-fretnum")


def test_barre_replaces_its_dots():
    root = svg_of(BARRE_F)
    barres = by_class(root, "fb-barre")
    assert len(barres) == 1
    assert "fb-red" in barres[0].get("class")
    # only the three non-barre notes are individual dots; one label for the barre
    assert len(by_class(root, "fb-dot")) == 3
    assert [el.text for el in by_class(root, "fb-label")] == ["1", "3", "4", "2"]


def test_high_position_prints_base_fret_instead_of_nut():
    root = svg_of(HIGH_G)
    assert not by_class(root, "fb-nut")
    assert [el.text for el in by_class(root, "fb-fretnum")] == ["7"]
    assert len(by_class(root, "fb-mute")) == 2


def test_no_name():
    root = svg_of("frets: x 3 2 0 1 0")
    assert not by_class(root, "fb-title")
    assert root.get("aria-label") == "Chord diagram"


def test_open_string_color_applies_to_open_marker():
    root = svg_of("frets: x 0@red 2 2 1 0")
    opens = by_class(root, "fb-open")
    assert "fb-red" in opens[0].get("class")
    assert "fb-red" not in opens[1].get("class")
```

- [ ] **Step 2: Run to see them fail**

Run: `uv run pytest tools/diagrams/tests/test_svg_chord.py -q` — Expected: ImportError.

- [ ] **Step 3: Implement**

Append to `svg.py`:
```python
# ---------------------------------------------------------------------------
# Chord


def chord_window(ch: Chord) -> tuple[int, bool, int]:
    """``(base_fret, has_nut, fret_count)`` for a chord box."""
    fretted = [d.fret for d in ch.strings if d is not None and d.fret > 0]
    if not fretted or max(fretted) <= CH_MIN_FRETS:
        return 1, True, CH_MIN_FRETS
    base = min(fretted)
    return base, False, max(CH_MIN_FRETS, max(fretted) - base + 1)


def render_chord(ch: Chord) -> str:
    """Vertical chord box, low E on the left."""
    base, has_nut, nfrets = chord_window(ch)
    top = 36 if ch.name else 22
    x_left = CH_PAD
    x_right = CH_PAD + CH_STRING_GAP * 5
    bottom = top + CH_FRET_H * nfrets
    width = x_right + CH_PAD
    height = bottom + 12
    label = ch.name or "Chord diagram"

    def string_x(string: int) -> float:
        return x_left + CH_STRING_GAP * string

    def fret_y(fret: int) -> float:
        return top + CH_FRET_H * (fret - base) + CH_FRET_H / 2

    out = [
        f'<svg class="fb fb-chord" viewBox="0 0 {_n(width)} {_n(height)}" '
        f'width="{_n(width)}" height="{_n(height)}" role="img" aria-label={quoteattr(label)}>'
    ]
    if ch.name:
        out.append(_text("fb-title", width / 2, 14, ch.name))
    if has_nut:
        out.append(_line("fb-nut", x_left, top, x_right, top))
    else:
        out.append(_text("fb-fretnum", x_left - 10, fret_y(base) + 4, str(base), anchor="end"))
    for i in range(nfrets + 1):
        y = top + CH_FRET_H * i
        out.append(_line("fb-fret", x_left, y, x_right, y))
    for s in range(6):
        x = string_x(s)
        out.append(_line("fb-string", x, top, x, bottom))
    barre_strings: list[int] = []
    if ch.barre is not None:
        barre_strings = [i for i, d in enumerate(ch.strings) if d is not None and d.fret == ch.barre]
        first = ch.strings[barre_strings[0]]
        assert first is not None
        x_a, x_b = string_x(barre_strings[0]), string_x(barre_strings[-1])
        y = fret_y(ch.barre)
        out.append(
            f'<rect class="{_cls("fb-barre", first.color)}" x="{_n(x_a - 9)}" y="{_n(y - 9)}" '
            f'width="{_n(x_b - x_a + 18)}" height="18" rx="9"/>'
        )
        if first.label:
            out.append(_text("fb-label", x_a, y + 3.5, first.label))
    for i, dot in enumerate(ch.strings):
        x = string_x(i)
        if dot is None:
            out.append(_text("fb-mute", x, top - 8, "×"))
        elif dot.fret == 0:
            out.append(f'<circle class="{_cls("fb-open", dot.color)}" cx="{_n(x)}" cy="{_n(top - 11)}" r="5"/>')
        elif i in barre_strings:
            continue
        else:
            out.append(_dot(dot, x, fret_y(dot.fret), r=9))
    out.append("</svg>")
    return "".join(out)
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tools/diagrams/tests -q` — Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add tools/diagrams
git commit -m "feat(diagrams): render chord boxes to svg"
```

---

### Task 7: Fence entry points, site config, and stylesheet

**Files:**
- Modify: `tools/diagrams/src/fretboard_diagrams/__init__.py`
- Create: `tools/diagrams/tests/test_fence.py`
- Create: `docs/assets/stylesheets/diagrams.css`
- Modify: `zensical.toml` (`extra_css`, `custom_fences`)

**Interfaces:**
- Produces: `fretboard_diagrams.fretboard_fence` and `fretboard_diagrams.chord_fence`, SuperFences `format` callables.

- [ ] **Step 1: Write the failing tests**

`tools/diagrams/tests/test_fence.py`:
```python
import markdown
import pytest
from pymdownx.superfences import SuperFencesException

from fretboard_diagrams import chord_fence, fretboard_fence

CONFIG = {
    "pymdownx.superfences": {
        "custom_fences": [
            {"name": "fretboard", "class": "fb-fence", "format": fretboard_fence},
            {"name": "chord", "class": "fb-fence", "format": chord_fence},
        ]
    }
}


def convert(text: str) -> str:
    md = markdown.Markdown(extensions=["pymdownx.superfences"], extension_configs=CONFIG)
    return md.convert(text)


def test_fretboard_fence_renders_svg():
    html = convert("Before\n\n```fretboard\ntitle: Test\nE: 8:1@red\n```\n\nAfter")
    assert '<svg class="fb fb-fretboard"' in html
    assert "<pre" not in html


def test_chord_fence_renders_svg():
    html = convert("```chord\nname: C\nfrets: x 3 2 0 1 0\n```")
    assert '<svg class="fb fb-chord"' in html


def test_malformed_block_fails_the_build():
    with pytest.raises(SuperFencesException, match="fretboard diagram: line 1: unknown key 'Z'"):
        convert("```fretboard\nZ: 8\n```")
    with pytest.raises(SuperFencesException, match="chord diagram: chord needs a 'frets:' line"):
        convert("```chord\nname: C\n```")
```

- [ ] **Step 2: Run to see them fail**

Run: `uv run pytest tools/diagrams/tests/test_fence.py -q` — Expected: ImportError on `chord_fence`.

- [ ] **Step 3: Implement the entry points**

`tools/diagrams/src/fretboard_diagrams/__init__.py`:
```python
"""Chord and fretboard diagrams rendered to inline SVG at build time.

Zensical/SuperFences call :func:`fretboard_fence` and :func:`chord_fence` for the
``fretboard`` and ``chord`` fences configured in ``zensical.toml``.
"""

from __future__ import annotations

from typing import Any

from pymdownx.superfences import SuperFencesException

from .parse import DiagramError, parse_chord, parse_fretboard
from .svg import render_chord, render_fretboard

__all__ = ["chord_fence", "fretboard_fence"]


def fretboard_fence(source: str, language: str, css_class: str, options: dict[str, Any],
                    md: Any, **kwargs: Any) -> str:
    """SuperFences ``format`` callable for ``fretboard`` blocks."""
    try:
        return render_fretboard(parse_fretboard(source))
    except DiagramError as exc:
        raise SuperFencesException(f"fretboard diagram: {exc}") from exc


def chord_fence(source: str, language: str, css_class: str, options: dict[str, Any],
                md: Any, **kwargs: Any) -> str:
    """SuperFences ``format`` callable for ``chord`` blocks."""
    try:
        return render_chord(parse_chord(source))
    except DiagramError as exc:
        raise SuperFencesException(f"chord diagram: {exc}") from exc
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tools/diagrams/tests -q` — Expected: all pass.

- [ ] **Step 5: Add the stylesheet**

`docs/assets/stylesheets/diagrams.css`:
```css
/* Chord and fretboard diagrams rendered by tools/diagrams. See CONTRIBUTING.md. */

.fb {
  display: inline-block;
  vertical-align: top;
  margin: 0 1.25rem 1rem 0;
  max-width: 100%;
  height: auto;
  overflow: visible;
  font-family: var(--md-text-font-family, sans-serif);
  --fb-red: #d6453b;
  --fb-orange: #e07b1a;
  --fb-yellow: #d4a300;
  --fb-green: #2f9e6b;
  --fb-blue: #2f6fdc;
  --fb-purple: #8a4fd6;
  --fb-grey: #8b919a;
}

[data-md-color-scheme="slate"] .fb {
  --fb-red: #ff6b5e;
  --fb-orange: #ffa14a;
  --fb-yellow: #f2c94c;
  --fb-green: #4fc38a;
  --fb-blue: #6ea2ff;
  --fb-purple: #b48cff;
  --fb-grey: #9aa3b2;
}

.fb-title { font-size: 12px; font-weight: 600; fill: var(--md-default-fg-color); }
.fb-fretnum { font-size: 10px; fill: var(--md-default-fg-color--light); }
.fb-mute { font-size: 13px; fill: var(--md-default-fg-color--light); }
.fb-inlay { fill: var(--md-default-fg-color); opacity: 0.15; }
.fb-string,
.fb-fret { stroke: var(--md-default-fg-color); stroke-width: 1.1; stroke-opacity: 0.8; }
.fb-nut { stroke: var(--md-default-fg-color); stroke-width: 5; }
.fb-dot,
.fb-barre { fill: var(--md-default-fg-color); }
.fb-open { fill: none; stroke: var(--md-default-fg-color); stroke-width: 1.5; }
.fb-label { font-size: 10px; font-weight: 600; fill: var(--md-default-bg-color); pointer-events: none; }

.fb-dot.fb-red, .fb-barre.fb-red { fill: var(--fb-red); }
.fb-dot.fb-orange, .fb-barre.fb-orange { fill: var(--fb-orange); }
.fb-dot.fb-yellow, .fb-barre.fb-yellow { fill: var(--fb-yellow); }
.fb-dot.fb-green, .fb-barre.fb-green { fill: var(--fb-green); }
.fb-dot.fb-blue, .fb-barre.fb-blue { fill: var(--fb-blue); }
.fb-dot.fb-purple, .fb-barre.fb-purple { fill: var(--fb-purple); }
.fb-dot.fb-grey, .fb-barre.fb-grey { fill: var(--fb-grey); }

.fb-open.fb-red { stroke: var(--fb-red); stroke-width: 2.2; }
.fb-open.fb-orange { stroke: var(--fb-orange); stroke-width: 2.2; }
.fb-open.fb-yellow { stroke: var(--fb-yellow); stroke-width: 2.2; }
.fb-open.fb-green { stroke: var(--fb-green); stroke-width: 2.2; }
.fb-open.fb-blue { stroke: var(--fb-blue); stroke-width: 2.2; }
.fb-open.fb-purple { stroke: var(--fb-purple); stroke-width: 2.2; }
.fb-open.fb-grey { stroke: var(--fb-grey); stroke-width: 2.2; }

/* Labels sit directly after their dot or barre in the markup. */
.fb-red + .fb-label,
.fb-orange + .fb-label,
.fb-green + .fb-label,
.fb-blue + .fb-label,
.fb-purple + .fb-label,
.fb-grey + .fb-label { fill: #fff; }
.fb-yellow + .fb-label { fill: #1f2328; }
```

- [ ] **Step 6: Register in `zensical.toml`**

Under `[project]` (after `edit_uri`) add:
```toml
extra_css = ["assets/stylesheets/diagrams.css"]
```

Replace the `custom_fences` line with:
```toml
pymdownx.superfences.custom_fences = [
  { name = "mermaid", class = "mermaid", format = "pymdownx.superfences.fence_code_format" },
  { name = "fretboard", class = "fb-fence", format = "fretboard_diagrams.fretboard_fence" },
  { name = "chord", class = "fb-fence", format = "fretboard_diagrams.chord_fence" },
]
```

- [ ] **Step 7: Verify the strict build still passes with no diagrams on any page**

Run: `uv run zensical build --strict` — Expected: success, and `site/assets/stylesheets/diagrams.css` exists.

- [ ] **Step 8: Commit**

```bash
git add tools/diagrams docs/assets/stylesheets/diagrams.css zensical.toml
git commit -m "feat(diagrams): register fretboard and chord fences with styles"
```

---

### Task 8: First diagram on the major scale page

**Files:**
- Modify: `docs/theory/major-scale.md` (section "One position on the fretboard")

- [ ] **Step 1: Replace the section**

Replace everything from `## One position on the fretboard` up to (not including) `## Why it matters` with:
````markdown
## One position on the fretboard

Here is C major in one position, starting from the C at the 8th fret of the low E
string and climbing two octaves to the C at the 8th fret of the high e string. The roots
are red; every other dot is labelled with its scale degree.

```fretboard
title: C major, two octaves from the low E string root
frets: 7-10
color: 1=red
E: 8:1 10:2
A: 7:3 8:4 10:5
D: 7:6 9:7 10:1
G: 7:2 9:3 10:4
B: 8:5 10:6
e: 7:7 8:1
```

Play it slowly, say the degree numbers out loud (1 2 3 4 5 6 7 1), and listen for where
the half steps are: 3 to 4 and 7 to 1 are the only places two scale notes sit one fret
apart on the same string. The other positions, and how they connect, will live in the
[Fretboard](../fretboard/index.md) section.

````

- [ ] **Step 2: Build strictly and inspect**

Run: `uv run zensical build --strict && grep -c 'fb fb-fretboard' site/theory/major-scale/index.html` — Expected: build succeeds, count is 1.

- [ ] **Step 3: Commit**

```bash
git add docs/theory/major-scale.md
git commit -m "docs(theory): add C major position diagram to the major scale page"
```

---

### Task 9: Contributor docs

**Files:**
- Modify: `CONTRIBUTING.md` (new section before "Workflow: branches and pull requests only")
- Modify: `AGENTS.md` (one bullet under "Content conventions")

- [ ] **Step 1: Add the Diagrams section to CONTRIBUTING.md**

Insert after the "Local development" section:
````markdown
## Diagrams

Chord boxes and fretboard shapes are written inline as fenced blocks and rendered to
SVG at build time by `tools/diagrams`. Never paste ASCII diagrams or image files.

A shape (scale, mode, arpeggio) is a `fretboard` block. Strings are `E A D G B e`, low
to high. Each dot is `fret[:label][@color]`; dots have no label unless you give one.

```fretboard
title: C major, position 1
frets: 7-10
color: 1=red
E: 8:1 10:2
A: 7:3 8:4 10:5
D: 7:6 9:7 10:1
G: 7:2 9:3 10:4
B: 8:5 10:6
e: 7:7 8:1 10:2
```

A chord is a `chord` block. `frets` has six tokens low to high (`x` muted, `0` open);
`fingers` labels the dots; `barre: N` draws a barre across every string fretted at N.

```chord
name: C
frets: x 3@red 2 0 1@red 0
fingers: - 3 2 - 1 -
```

- Colors: `red orange yellow green blue purple grey`. `color: 1=red 3=blue` colors by
  label; `@color` on a dot always wins.
- `frets: lo-hi` fixes the window; omit it to fit the dots (minimum four frets).
- A malformed block fails `zensical build --strict` with the line and the problem.
- Run `uv run pytest` after changing anything in `tools/diagrams`.

````

- [ ] **Step 2: Add the AGENTS.md bullet**

Under "Content conventions" add:
```markdown
- Chord and scale diagrams are `chord` and `fretboard` fenced blocks, never ASCII art or
  images. See "Diagrams" in [CONTRIBUTING.md](CONTRIBUTING.md).
```

- [ ] **Step 3: Verify**

Run: `uv run pytest -q && uv run zensical build --strict` — Expected: all pass, build succeeds.

- [ ] **Step 4: Commit**

```bash
git add CONTRIBUTING.md AGENTS.md
git commit -m "docs: describe the chord and fretboard diagram fences"
```

---

### Task 10: Pull request

- [ ] **Step 1: Lint commits and push the branch**

Run: `npx commitlint --from main && git push -u origin feat/fretboard-diagrams`.

- [ ] **Step 2: Open the PR**

`gh pr create --template feat.md --title "feat(diagrams): render chord and fretboard diagrams from fenced blocks"` with every template section filled, including the strict build result and the pytest count under "How it was verified", and the attribution line from the session reminder at the end of the body.
