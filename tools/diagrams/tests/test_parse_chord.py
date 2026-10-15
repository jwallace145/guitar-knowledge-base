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
        ("frets: x 3 2 0 1 0\nbarre: 4", "barre at fret 4 but no string is fretted there"),
        ("frets: x 3 2 0 1 0\nbarre: 0", "line 2: bad barre"),
        ("frets: x 3 2 0 1 0\nfoo: 1", "line 2: unknown key 'foo'"),
        ("frets: x y 2 0 1 0", "line 1: bad dot 'y'"),
    ],
)
def test_errors(source, message):
    with pytest.raises(DiagramError, match=message):
        parse_chord(source)


def test_non_ascii_digit_barre_is_rejected():
    with pytest.raises(DiagramError, match="line 2: bad barre"):
        parse_chord("frets: 1 3 3 2 1 1\nbarre: ²")
