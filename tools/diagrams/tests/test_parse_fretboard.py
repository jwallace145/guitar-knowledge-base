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
    assert len(fb.dots) == 16
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
