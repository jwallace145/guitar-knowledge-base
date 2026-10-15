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
        ("x", "expected fret\\[:label\\]\\[@color\\]"),
        ("8:", "expected fret\\[:label\\]\\[@color\\]"),
        ("8@", "expected fret\\[:label\\]\\[@color\\]"),
        ("8@red:1", "expected fret\\[:label\\]\\[@color\\]"),
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
