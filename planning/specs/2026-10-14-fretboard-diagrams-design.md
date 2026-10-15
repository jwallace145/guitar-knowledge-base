# Fretboard diagrams: design

Date: 2026-10-14
Status: approved

## Goal

Let any page in the knowledge base include chord boxes and fretboard shapes (scales,
modes, arpeggios, triads) that all share one visual style, by writing a short text block
inline in the Markdown. Diagrams are rendered to inline SVG at build time by a Python
custom fence. No JavaScript at runtime, no generated image files to commit.

Authoring must be cheap enough that every chord, position, and mode gets a diagram.
The author must be able to color any dot independently (for example root, third, and
fifth in different colors, or every dot the same) for demonstrative purposes.

## Non-goals

- A shared library of named chords or shapes. Every diagram is written inline where it
  is used. A library can be layered on later without changing this format.
- Interactivity (hover, toggles). The SVG uses stable CSS classes so a script could be
  added later, but none ships now.
- Left-handed or alternate-tuning rendering. Six strings, standard tuning labels only.

## Authoring format

Two fence types, `fretboard` and `chord`. Both bodies are line-based: `key: value`
lines in any order, blank lines ignored, `#` at line start is a comment.

### `fretboard`: a horizontal neck diagram

```
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
```

- Strings are keyed `E A D G B e` (low to high). Any string may be omitted.
- A string line is a whitespace-separated list of dot tokens `fret[:label][@color]`.
  - `fret` is an integer 0–24. Fret 0 is an open string, drawn as a dot beside the nut.
  - `label` is any text with no whitespace, `:` or `@`. There is **no default label**;
    a dot with no `:label` is drawn empty.
  - `color` is one of the palette names below. Omitted means the neutral default.
- `color:` (optional) is a space-separated list of `label=color` rules. A dot whose label
  matches a rule takes that color unless it has its own `@color`, which always wins.
- `frets: lo-hi` (optional) fixes the visible fret window. If omitted, the window runs
  from the lowest to the highest fretted dot and is widened to at least four frets.
  Fret 0 is never part of the window; the nut is drawn whenever any dot is at fret 0
  or the window starts at fret 1.
- `title:` (optional) is drawn above the diagram and used as the accessible name.
- Rendering: high e on top, low E at the bottom, string strokes thicker toward the low
  strings, fret numbers under every fret, position inlay marks at frets 3, 5, 7, 9, 12
  (double), 15, 17, 19, 21.

### `chord`: a vertical chord box

```
```chord
name: C
frets: x 3@red 2 0 1@red 0
fingers: - 3 2 - 1 -
barre: 1
```
```

- `frets:` (required) has exactly six tokens, low E to high e. Each is `x` (muted),
  or a dot token `fret[:label][@color]` with fret 0 meaning open.
- `fingers:` (optional) has six tokens, each `-` or 1–4. A fretted dot with no explicit
  `:label` uses its finger number as the label; `-` means no label.
- `barre: N` (optional) draws a barre at fret N from the lowest to the highest string
  whose fret is N. Dots under the barre are not drawn individually; the barre takes the
  color and label of its lowest string's token.
- `name:` (optional) is drawn above the box and used as the accessible name.
- `color:` works as in `fretboard`, matching against the dot's final label.
- Window: if the highest fret is 4 or less, the nut is drawn and the box starts at
  fret 1. Otherwise the box starts at the lowest fretted fret and that number is printed
  beside the first fret. The box is always at least four frets tall.
- Muted strings show `×` above the nut; open strings show a hollow circle, which takes
  the token's color.

### Palette

`red orange yellow green blue purple grey`. Each is a CSS class `fb-red` and so on,
defined once per color scheme in the stylesheet. Any other name is an error.

## Errors

Every parse error raises `pymdownx.superfences.SuperFencesException` with the fence
type, the offending line, and what was expected. SuperFences re-raises that exception
class (it swallows all others), so `zensical build --strict` fails on a malformed block
rather than falling back to a code block. Errors include: unknown key, bad fret number,
wrong token count in `chord`, unknown color, bad `frets` range, duplicate string line,
and a dot outside an explicit `frets` window.

## Architecture

```
src/guitar_kb/
  __init__.py
  diagrams/
    __init__.py       # fence entry points: fretboard_fence(), chord_fence()
    model.py          # Dot, Fretboard, Chord dataclasses; palette constant
    parse.py          # text -> model; all validation and error messages
    svg.py            # model -> SVG string; geometry only, styling via classes
docs/assets/stylesheets/diagrams.css
tests/
  test_parse_fretboard.py
  test_parse_chord.py
  test_svg.py
```

- `parse.py` knows nothing about SVG. `svg.py` knows nothing about the text format.
  Both are pure functions over the dataclasses, which keeps them unit-testable without
  Markdown or Zensical.
- `diagrams/__init__.py` exposes the two SuperFences `format` callables with the
  signature `(source, language, css_class, options, md, **kwargs) -> str`. Each calls
  the parser, then the renderer, and wraps parse errors in `SuperFencesException`.
- `zensical.toml` gains two entries in `pymdownx.superfences.custom_fences` pointing at
  those callables by dotted path, and `extra_css = ["assets/stylesheets/diagrams.css"]`.
- `pyproject.toml` gains a hatchling build section so `uv sync` installs `guitar_kb`
  into the venv and Zensical can import it. Release Please keeps owning the version
  field. `pytest` is added as a dev dependency.

## SVG and styling

- Every SVG has `class="fb fb-fretboard"` or `class="fb fb-chord"`, `role="img"`, an
  `aria-label` from the title or name, and a `viewBox` so it scales. Width is fixed in
  CSS pixels per fret and string so all diagrams on the site share the same scale.
- Elements use classes only: `fb-title fb-fret fb-string fb-nut fb-inlay fb-fretnum
  fb-dot fb-open fb-mute fb-barre fb-label` plus a palette class on dots, open circles
  and barres.
- Default style is the "Ink" direction approved in brainstorming: solid dots filled with
  `--md-default-fg-color`, labels knocked out in `--md-default-bg-color`, lines in the
  foreground color at reduced opacity. Palette dots are filled with the palette color
  and keep white labels. Dark mode is handled by Material's variables plus a
  `[data-md-color-scheme="slate"]` block that brightens the palette.
- Diagrams are inline-block with a right and bottom margin so several sit side by side
  and wrap on narrow screens.

## Testing

- Parser tests: every documented feature and every documented error, with the error
  message asserted on.
- SVG tests: parse the output with `xml.etree`, assert element counts and classes (for
  example "three `fb-red` dots", "nut present", "fret number 7 printed"), and assert
  geometry invariants such as all dots lying inside the viewBox.
- Fence tests: run `markdown` with `pymdownx.superfences` configured as in
  `zensical.toml` and assert that a `fretboard` block becomes an `<svg>` and that a
  malformed block raises.
- `uv run zensical build --strict` is the integration check and is what CI runs.

## First use

`docs/theory/major-scale.md`, section "One position on the fretboard", is rewritten to
show C major from the C at fret 8 on the low E string up two octaves to the C at fret 8
on the high e string, frets 7–10, with the three roots red and degree labels on every
dot. The ASCII block for the A-string position is removed.

## Documentation

`CONTRIBUTING.md` gains a short "Diagrams" section with both fence examples and the
palette list, and `AGENTS.md` gets one line pointing at it so agents reach for the
fences instead of ASCII.
