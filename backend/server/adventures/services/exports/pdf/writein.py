"""Things drawn on the page: checkboxes, rating circles, markers, ruled lines and QR codes."""

from __future__ import annotations

from typing import Optional

import qrcode
from qrcode.constants import ERROR_CORRECT_L
from reportlab.lib import colors
from reportlab.platypus import Flowable

from .theme import COLOR_FAINT, COLOR_INK, COLOR_MUTED, COLOR_PRIMARY, COLOR_RULE, hex_color


class Checkbox(Flowable):
    """An empty square to tick, or a ticked one."""

    def __init__(self, size: float = 11, checked: bool = False, color=COLOR_INK):
        super().__init__()
        self.size = size
        self.checked = checked
        self.color = color

    def wrap(self, availWidth, availHeight):
        return self.size, self.size

    def draw(self):
        c, s = self.canv, self.size
        c.setLineWidth(1)
        c.setStrokeColor(self.color)
        if self.checked:
            c.setFillColor(COLOR_PRIMARY)
            c.setStrokeColor(COLOR_PRIMARY)
            c.roundRect(0, 0, s, s, 2, stroke=1, fill=1)
            c.setStrokeColor(colors.white)
            c.setLineWidth(1.6)
            path = c.beginPath()
            path.moveTo(s * 0.22, s * 0.52)
            path.lineTo(s * 0.43, s * 0.28)
            path.lineTo(s * 0.80, s * 0.74)
            c.drawPath(path, stroke=1, fill=0)
        else:
            c.roundRect(0, 0, s, s, 2, stroke=1, fill=0)


class Marker(Flowable):
    """A filled circle with a short label in it (a stop number, a day number)."""

    def __init__(self, label: str, color: str = '#0d9488', size: float = 20):
        super().__init__()
        self.label = str(label)
        self.color = hex_color(color)
        self.size = size

    def wrap(self, availWidth, availHeight):
        return self.size, self.size

    def draw(self):
        from .fonts import bold_font_name  # noqa: PLC0415

        c, s = self.canv, self.size
        c.setFillColor(self.color)
        c.circle(s / 2, s / 2, s / 2, stroke=0, fill=1)
        c.setFillColor(colors.white)
        font_size = s * (0.5 if len(self.label) < 3 else 0.38)
        c.setFont(bold_font_name(), font_size)
        c.drawCentredString(s / 2, s / 2 - font_size * 0.35, self.label)


class RatingCircles(Flowable):
    """Five empty circles to colour in, with a label in front."""

    def __init__(self, count: int = 5, size: float = 10, gap: float = 5):
        super().__init__()
        self.count, self.size, self.gap = count, size, gap

    def wrap(self, availWidth, availHeight):
        return self.count * self.size + (self.count - 1) * self.gap, self.size

    def draw(self):
        c = self.canv
        c.setStrokeColor(COLOR_MUTED)
        c.setLineWidth(0.9)
        for i in range(self.count):
            c.circle(self.size / 2 + i * (self.size + self.gap), self.size / 2, self.size / 2, stroke=1, fill=0)


class FilledRating(Flowable):
    """Circles filled to a rating out of five (halves round up)."""

    def __init__(self, rating: float, count: int = 5, size: float = 8, gap: float = 3):
        super().__init__()
        self.rating, self.count, self.size, self.gap = rating, count, size, gap

    def wrap(self, availWidth, availHeight):
        return self.count * self.size + (self.count - 1) * self.gap, self.size

    def draw(self):
        c = self.canv
        filled = round(self.rating + 0.01)
        c.setLineWidth(0.8)
        for i in range(self.count):
            c.setStrokeColor(COLOR_PRIMARY)
            c.setFillColor(COLOR_PRIMARY if i < filled else colors.white)
            c.circle(self.size / 2 + i * (self.size + self.gap), self.size / 2, self.size / 2, stroke=1, fill=1)


class RuledLines(Flowable):
    """Lines to write on, ``count`` of them, or as many as fit (between ``min_height`` and ``max_height``)."""

    def __init__(self, width: float, count: Optional[int] = None, spacing: float = 20,
                 min_height: float = 0, max_height: float = 0, label: str = ''):
        super().__init__()
        self.width = width
        self.count = count
        self.spacing = spacing
        self.min_height = min_height
        self.max_height = max_height
        self.label = label
        self._height = 0.0

    def wrap(self, availWidth, availHeight):
        if self.count is not None:
            self._height = self.count * self.spacing + (14 if self.label else 0)
        else:
            # Fill what is left of the page, but never ask for a whole page of lines.
            self._height = max(min(availHeight - 2, self.max_height or availHeight), self.min_height)
        return self.width, self._height

    def draw(self):
        from .fonts import bold_font_name  # noqa: PLC0415

        c = self.canv
        c.setStrokeColor(COLOR_RULE)
        c.setLineWidth(0.6)
        y = self._height
        if self.label:
            c.setFillColor(COLOR_FAINT)
            c.setFont(bold_font_name(), 7.5)
            c.drawString(0, y - 8, self.label.upper())
            y -= 14
        y -= self.spacing - 2
        while y > 0.5:
            c.line(0, y, self.width, y)
            y -= self.spacing


class Arrow(Flowable):
    """A right-pointing arrow (the fonts have no arrow glyph)."""

    def __init__(self, width: float = 36, height: float = 24, color=COLOR_FAINT):
        super().__init__()
        self.width, self.height, self.color = width, height, color

    def wrap(self, availWidth, availHeight):
        return self.width, self.height

    def draw(self):
        c, w, mid = self.canv, self.width, self.height / 2
        c.setStrokeColor(self.color)
        c.setFillColor(self.color)
        c.setLineWidth(1.4)
        c.line(4, mid, w - 6, mid)
        head = c.beginPath()
        head.moveTo(w - 2, mid)
        head.lineTo(w - 9, mid + 4)
        head.lineTo(w - 9, mid - 4)
        head.close()
        c.drawPath(head, stroke=0, fill=1)


class FillIn(Flowable):
    """A line to write on, with optional text already filled in above it."""

    def __init__(self, width: float, prefill: str = '', height: float = 16):
        super().__init__()
        self.width, self.prefill, self.height = width, prefill, height

    def wrap(self, availWidth, availHeight):
        return self.width, self.height

    def draw(self):
        from .fonts import ensure_pdf_fonts  # noqa: PLC0415

        c = self.canv
        c.setStrokeColor(COLOR_RULE)
        c.setLineWidth(0.8)
        c.line(0, 2, self.width, 2)
        if self.prefill:
            body, _ = ensure_pdf_fonts()
            c.setFillColor(COLOR_INK)
            c.setFont(body, 9)
            c.drawString(2, 5, self.prefill)


class Rule(Flowable):
    """A thin horizontal line."""

    def __init__(self, width: float, color=COLOR_RULE, thickness: float = 0.6):
        super().__init__()
        self.width, self.color, self.thickness = width, color, thickness

    def wrap(self, availWidth, availHeight):
        return self.width, self.thickness + 1

    def draw(self):
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(self.thickness)
        self.canv.line(0, 0.5, self.width, 0.5)


class ProgressBar(Flowable):
    """A bar filled to ``fraction``."""

    def __init__(self, width: float, fraction: float, height: float = 8):
        super().__init__()
        self.width, self.fraction, self.height = width, max(0.0, min(1.0, fraction)), height

    def wrap(self, availWidth, availHeight):
        return self.width, self.height

    def draw(self):
        c, h = self.canv, self.height
        c.setFillColor(colors.HexColor('#e2e8f0'))
        c.roundRect(0, 0, self.width, h, h / 2, stroke=0, fill=1)
        if self.fraction > 0:
            c.setFillColor(COLOR_PRIMARY)
            c.roundRect(0, 0, max(self.width * self.fraction, h), h, h / 2, stroke=0, fill=1)


class QRCode(Flowable):
    """A QR code drawn as vector squares, so it stays sharp however it is printed."""

    def __init__(self, url: str, size: float = 46):
        super().__init__()
        qr = qrcode.QRCode(border=0, error_correction=ERROR_CORRECT_L)
        qr.add_data(url)
        qr.make(fit=True)
        self.matrix = qr.get_matrix()
        self.size = size

    def wrap(self, availWidth, availHeight):
        return self.size, self.size

    def draw(self):
        c = self.canv
        n = len(self.matrix)
        cell = self.size / n
        c.setFillColor(COLOR_INK)
        for row, line in enumerate(self.matrix):
            for col, filled in enumerate(line):
                if filled:
                    c.rect(col * cell, self.size - (row + 1) * cell, cell + 0.2, cell + 0.2, stroke=0, fill=1)


def map_link(lat: float, lon: float) -> str:
    """A link that opens the point in whatever maps app the phone has."""
    return f'https://www.google.com/maps/search/?api=1&query={lat:.6f},{lon:.6f}'
