"""
Register Unicode-capable fonts for ReportLab PDF generation (including emoji).
"""
from __future__ import annotations

import logging
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFError, TTFont

logger = logging.getLogger(__name__)

BODY_FONT = 'AdventureLogSans'
EMOJI_FONT = 'AdventureLogEmoji'

_BUNDLED_DIR = Path(__file__).resolve().parent.parent / 'pdf_assets' / 'fonts'

# System paths (Debian/Ubuntu fonts-noto-* packages)
_SYSTEM_FONT_CANDIDATES = {
    BODY_FONT: [
        _BUNDLED_DIR / 'NotoSans-Regular.ttf',
        Path('/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf'),
        Path('/usr/share/fonts/opentype/noto/NotoSans-Regular.ttf'),
        Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
    ],
    EMOJI_FONT: [
        _BUNDLED_DIR / 'NotoEmoji-Regular.ttf',
        Path('/usr/share/fonts/truetype/noto/NotoEmoji-Regular.ttf'),
        Path('/usr/share/fonts/truetype/noto/NotoSansSymbols2-Regular.ttf'),
        Path('/usr/share/fonts/truetype/noto/NotoSansSymbols-Regular.ttf'),
    ],
}

_registered = False


def _register_font(alias: str, path: Path) -> bool:
    try:
        pdfmetrics.registerFont(TTFont(alias, str(path)))
        return True
    except (TTFError, OSError, ValueError) as exc:
        logger.debug('Could not register font %s from %s: %s', alias, path, exc)
        return False


@lru_cache(maxsize=1)
def ensure_pdf_fonts() -> tuple[str, str | None]:
    """
    Register body and emoji fonts once. Returns (body_font_name, emoji_font_name or None).
    """
    global _registered
    if _registered:
        return BODY_FONT, EMOJI_FONT if EMOJI_FONT in pdfmetrics.getRegisteredFontNames() else None

    body_path = next((p for p in _SYSTEM_FONT_CANDIDATES[BODY_FONT] if p.is_file()), None)
    if body_path:
        _register_font(BODY_FONT, body_path)
    else:
        logger.warning('PDF body font not found; emoji and non-Latin text may not render')

    emoji_path = next((p for p in _SYSTEM_FONT_CANDIDATES[EMOJI_FONT] if p.is_file()), None)
    emoji_registered = None
    if emoji_path and _register_font(EMOJI_FONT, emoji_path):
        emoji_registered = EMOJI_FONT
    else:
        logger.warning('PDF emoji font not found; category icons may not render')

    _registered = True
    body = BODY_FONT if BODY_FONT in pdfmetrics.getRegisteredFontNames() else 'Helvetica'
    return body, emoji_registered


def _char_is_emoji(c: str) -> bool:
    if c in '\u200d\ufe0f\u20e3':
        return True
    o = ord(c)
    if 0x1F1E6 <= o <= 0x1F1FF:
        return True
    if 0x1F300 <= o <= 0x1FAFF:
        return True
    if 0x2600 <= o <= 0x27BF:
        return True
    if 0x2300 <= o <= 0x23FF:
        return True
    if 0x1F600 <= o <= 0x1F64F:
        return True
    if 0x1F680 <= o <= 0x1F6FF:
        return True
    if 0x1F900 <= o <= 0x1F9FF:
        return True
    try:
        return 'EMOJI' in unicodedata.name(c, '')
    except ValueError:
        return False


def _split_text_runs(text: str) -> list[tuple[str, bool]]:
    if not text:
        return []
    runs: list[tuple[str, bool]] = []
    buf: list[str] = []
    is_emoji: bool | None = None
    for char in text:
        char_emoji = _char_is_emoji(char)
        if buf and char_emoji != is_emoji:
            runs.append((''.join(buf), bool(is_emoji)))
            buf = []
        buf.append(char)
        is_emoji = char_emoji
    if buf:
        runs.append((''.join(buf), bool(is_emoji)))
    return runs


def escape_xml(text: str) -> str:
    return (
        text.replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
    )


def pdf_markup(text: str, *, emoji_font: str | None = None) -> str:
    """
    Escape text for ReportLab Paragraph XML and wrap emoji runs in the emoji font.
    """
    if not text:
        return ''
    _, emoji_registered = ensure_pdf_fonts()
    font = emoji_font or emoji_registered
    parts: list[str] = []
    for chunk, is_emoji in _split_text_runs(text):
        escaped = escape_xml(chunk)
        if is_emoji and font:
            parts.append(f'<font face="{font}">{escaped}</font>')
        else:
            parts.append(escaped)
    return ''.join(parts).replace('\n', '<br/>')


def apply_fonts_to_styles(styles: dict, body_font: str) -> None:
    for style in styles.values():
        style.fontName = body_font
