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
