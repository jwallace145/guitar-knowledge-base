from xml.etree import ElementTree as ET

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
    assert len(by_class(root, "fb-dot")) == 16
    assert len(by_class(root, "fb-red")) == 3
    assert len(by_class(root, "fb-label")) == 16
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
