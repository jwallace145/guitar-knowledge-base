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
