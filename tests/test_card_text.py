"""Every character drawn onto the card must exist in the font that draws it.

DejaVu has no Myanmar glyphs and Noto Sans Myanmar has no Latin ones, so a string
that mixes scripts — or a stray ASCII hyphen in a Burmese line — silently renders as
empty boxes on the payment card. Nothing else would catch that.
"""

import pytest
from PIL import ImageFont

from bot import texts
from bot.services.languages import Language
from bot.services.renderer import (
    HINT_SIZE,
    MYANMAR_BOLD_CANDIDATES,
    SANS_BOLD_CANDIDATES,
    _font,
    has_myanmar,
)

#: In the Private Use Area, so no real font assigns it a glyph. Anything that renders
#: identically to this is falling back to .notdef.
_DEFINITELY_MISSING = "\ue123"


def _renders(font: ImageFont.FreeTypeFont, char: str) -> bool:
    if char.isspace():
        return True
    return bytes(font.getmask(char)) != bytes(font.getmask(_DEFINITELY_MISSING))


def _missing(font: ImageFont.FreeTypeFont, text: str) -> list[str]:
    return sorted({char for char in text if not _renders(font, char)})


def test_the_probe_itself_works():
    """Guard the guard: DejaVu must be seen to lack Myanmar, and Noto to lack Latin."""
    dejavu = _font(SANS_BOLD_CANDIDATES, HINT_SIZE)
    noto = _font(MYANMAR_BOLD_CANDIDATES, HINT_SIZE)

    assert _missing(dejavu, "ဂဏန်း"), "DejaVu has no Myanmar glyphs"
    assert _missing(noto, "abc-"), "Noto Sans Myanmar has no Latin glyphs"
    assert not _missing(dejavu, "abc-!"), "DejaVu covers Latin"
    assert not _missing(noto, "ဂဏန်း"), "Noto covers Myanmar"


@pytest.mark.parametrize("lang", list(Language))
def test_the_card_warning_is_fully_renderable(lang):
    warning = texts.get(lang).PADDING_WARNING
    font = _font(
        MYANMAR_BOLD_CANDIDATES if has_myanmar(warning) else SANS_BOLD_CANDIDATES,
        HINT_SIZE,
    )
    assert _missing(font, warning) == [], (
        f"{lang.value} card warning has characters the chosen font cannot draw"
    )


@pytest.mark.parametrize("lang", list(Language))
def test_the_card_warning_does_not_mix_scripts(lang):
    """One font draws the whole line, so a mixed-script string cannot render fully."""
    warning = texts.get(lang).PADDING_WARNING
    if not has_myanmar(warning):
        return
    latin = [c for c in warning if not c.isspace() and c.isascii()]
    assert latin == [], f"{lang.value} card warning mixes ASCII into Burmese: {latin}"
