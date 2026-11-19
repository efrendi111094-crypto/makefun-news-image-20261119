#!/usr/bin/env python3
"""One-day newspaper poster for 19 November 2026.

Renders the stories in news.json (sitting next to this file) into a
1024x1024 PNG at /output/entry.png (or $MAKEFUN_OUTPUT_DIR/entry.png).
Pure Python 3.13 standard library: a hand-rolled 5x7 bitmap typeface
stored as integer bit rows, a small software rasteriser, and a PNG
encoder built on zlib + struct. No network, no third-party packages.

Everything is deterministic: the same news.json always produces the
same PNG bytes, so running the program twice gives identical output.
"""

import json
import os
import struct
import zlib
from pathlib import Path

# ---------------------------------------------------------------------------
# Page geometry
# ---------------------------------------------------------------------------
PAGE_W = 1024
PAGE_H = 1024
MARGIN = 24
GUTTER = 20

# ---------------------------------------------------------------------------
# Newsprint palette
# ---------------------------------------------------------------------------
PAPER = (246, 241, 227)
PAPER_SOFT = (239, 231, 211)
CARD = (255, 255, 255)
INK = (25, 25, 25)
FAINT = (107, 107, 107)
ACCENT = (179, 38, 30)
DEEP_BLUE = (31, 58, 95)
MID_BLUE = (31, 78, 121)
DARK_BLUE = (22, 35, 58)
PALE_BLUE = (220, 233, 245)
GOLD = (201, 162, 39)
PALE_GOLD = (244, 208, 90)
SAND = (217, 197, 138)
PEACH = (244, 178, 140)
TANGERINE = (230, 126, 34)
PLUM = (88, 52, 120)
LEAF = (46, 125, 50)
PALE_LEAF = (222, 240, 222)
BLUSH = (246, 227, 224)

# ---------------------------------------------------------------------------
# 5x7 bitmap typeface, one glyph = seven 5-bit rows (MSB = leftmost pixel).
# Only capitals, digits and punctuation are needed: every string is
# upper-cased before it is drawn.
# ---------------------------------------------------------------------------
GLYPH_ROWS = 7
GLYPH_COLS = 5
GLYPH_ADVANCE = 6  # columns per character, including one blank column

GLYPHS = {
    "A": (0b01110, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001),
    "B": (0b11110, 0b10001, 0b10001, 0b11110, 0b10001, 0b10001, 0b11110),
    "C": (0b01110, 0b10001, 0b10000, 0b10000, 0b10000, 0b10001, 0b01110),
    "D": (0b11100, 0b10010, 0b10001, 0b10001, 0b10001, 0b10010, 0b11100),
    "E": (0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b11111),
    "F": (0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b10000),
    "G": (0b01110, 0b10001, 0b10000, 0b10111, 0b10001, 0b10001, 0b01111),
    "H": (0b10001, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001),
    "I": (0b01110, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110),
    "J": (0b00111, 0b00010, 0b00010, 0b00010, 0b00010, 0b10010, 0b01100),
    "K": (0b10001, 0b10010, 0b10100, 0b11000, 0b10100, 0b10010, 0b10001),
    "L": (0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b11111),
    "M": (0b10001, 0b11011, 0b10101, 0b10101, 0b10001, 0b10001, 0b10001),
    "N": (0b10001, 0b11001, 0b10101, 0b10011, 0b10001, 0b10001, 0b10001),
    "O": (0b01110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110),
    "P": (0b11110, 0b10001, 0b10001, 0b11110, 0b10000, 0b10000, 0b10000),
    "Q": (0b01110, 0b10001, 0b10001, 0b10001, 0b10101, 0b10010, 0b01101),
    "R": (0b11110, 0b10001, 0b10001, 0b11110, 0b10100, 0b10010, 0b10001),
    "S": (0b01111, 0b10000, 0b10000, 0b01110, 0b00001, 0b00001, 0b11110),
    "T": (0b11111, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100),
    "U": (0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110),
    "V": (0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01010, 0b00100),
    "W": (0b10001, 0b10001, 0b10001, 0b10101, 0b10101, 0b10101, 0b01010),
    "X": (0b10001, 0b10001, 0b01010, 0b00100, 0b01010, 0b10001, 0b10001),
    "Y": (0b10001, 0b10001, 0b01010, 0b00100, 0b00100, 0b00100, 0b00100),
    "Z": (0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b10000, 0b11111),
    "0": (0b01110, 0b10001, 0b10011, 0b10101, 0b11001, 0b10001, 0b01110),
    "1": (0b00100, 0b01100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110),
    "2": (0b01110, 0b10001, 0b00001, 0b00110, 0b01000, 0b10000, 0b11111),
    "3": (0b11111, 0b00010, 0b00100, 0b00010, 0b00001, 0b10001, 0b01110),
    "4": (0b00010, 0b00110, 0b01010, 0b10010, 0b11111, 0b00010, 0b00010),
    "5": (0b11111, 0b10000, 0b11110, 0b00001, 0b00001, 0b10001, 0b01110),
    "6": (0b00110, 0b01000, 0b10000, 0b11110, 0b10001, 0b10001, 0b01110),
    "7": (0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b01000, 0b01000),
    "8": (0b01110, 0b10001, 0b10001, 0b01110, 0b10001, 0b10001, 0b01110),
    "9": (0b01110, 0b10001, 0b10001, 0b01111, 0b00001, 0b00010, 0b01100),
    " ": (0, 0, 0, 0, 0, 0, 0),
    ".": (0, 0, 0, 0, 0, 0b01100, 0b01100),
    ",": (0, 0, 0, 0, 0b01100, 0b00100, 0b01000),
    ":": (0, 0b01100, 0b01100, 0, 0b01100, 0b01100, 0),
    ";": (0, 0b01100, 0b01100, 0, 0b01100, 0b00100, 0b01000),
    "!": (0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0, 0b00100),
    "?": (0b01110, 0b10001, 0b00001, 0b00110, 0b00100, 0, 0b00100),
    "-": (0, 0, 0, 0b01110, 0, 0, 0),
    "'": (0b00100, 0b00100, 0b01000, 0, 0, 0, 0),
    "(": (0b00010, 0b00100, 0b01000, 0b01000, 0b01000, 0b00100, 0b00010),
    ")": (0b01000, 0b00100, 0b00010, 0b00010, 0b00010, 0b00100, 0b01000),
    "/": (0b00001, 0b00010, 0b00010, 0b00100, 0b01000, 0b01000, 0b10000),
    "&": (0b01100, 0b10010, 0b10100, 0b01000, 0b10101, 0b10010, 0b01101),
    "%": (0b11001, 0b11010, 0b00010, 0b00100, 0b01000, 0b01011, 0b10011),
    "+": (0, 0b00100, 0b00100, 0b01110, 0b00100, 0b00100, 0),
    "$": (0b00100, 0b01111, 0b10100, 0b01110, 0b00101, 0b11110, 0b00100),
    "#": (0b01010, 0b01010, 0b11111, 0b01010, 0b11111, 0b01010, 0b01010),
    "=": (0, 0, 0b11111, 0, 0b11111, 0, 0),
    "*": (0, 0b10101, 0b01110, 0b11111, 0b01110, 0b10101, 0),
    '"': (0b01010, 0b01010, 0, 0, 0, 0, 0),
    "_": (0, 0, 0, 0, 0, 0, 0b11111),
    "|": (0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100),
}
UNKNOWN_GLYPH = GLYPHS["?"]


# ---------------------------------------------------------------------------
# Text measurement and wrapping
# ---------------------------------------------------------------------------
def measure(text, size):
    """Width in pixels of `text` drawn at `size` (no trailing advance)."""
    if not text:
        return 0
    return len(text) * GLYPH_ADVANCE * size - size


def split_lines(text, max_width, size):
    """Greedy word wrap; over-long words are chopped to fit."""
    words = text.upper().split()
    if not words:
        return [""]
    lines = []
    current = words[0]
    for word in words[1:]:
        joined = current + " " + word
        if measure(joined, size) <= max_width:
            current = joined
        else:
            lines.append(current)
            current = word
            # Chop a single word that still does not fit on its own.
            while measure(current, size) > max_width:
                per_line = max(1, max_width // (GLYPH_ADVANCE * size))
                lines.append(current[:per_line])
                current = current[per_line:]
    lines.append(current)
    return lines


# ---------------------------------------------------------------------------
# Software rasteriser: a flat RGB buffer with filled shapes and text.
# ---------------------------------------------------------------------------
class Sheet:
    """A 24-bit RGB canvas backed by one bytearray."""

    def __init__(self, width, height, background):
        self.width = width
        self.height = height
        self.pixels = bytearray(width * height * 3)
        self.fill_rect(0, 0, width, height, background)

    # -- primitive paint ----------------------------------------------------
    def set_pixel(self, x, y, colour):
        if 0 <= x < self.width and 0 <= y < self.height:
            offset = (y * self.width + x) * 3
            self.pixels[offset:offset + 3] = bytes(colour)

    def fill_rect(self, x, y, w, h, colour):
        left = max(x, 0)
        top = max(y, 0)
        right = min(x + w, self.width)
        bottom = min(y + h, self.height)
        if right <= left or bottom <= top:
            return
        row = bytes(colour) * (right - left)
        for yy in range(top, bottom):
            start = (yy * self.width + left) * 3
            self.pixels[start:start + len(row)] = row

    def frame(self, x, y, w, h, colour, thick=2):
        self.fill_rect(x, y, w, thick, colour)
        self.fill_rect(x, y + h - thick, w, thick, colour)
        self.fill_rect(x, y, thick, h, colour)
        self.fill_rect(x + w - thick, y, thick, h, colour)

    def rule_h(self, x, y, w, colour, thick=1):
        self.fill_rect(x, y, w, thick, colour)

    def rule_v(self, x, y, h, colour, thick=1):
        self.fill_rect(x, y, thick, h, colour)

    def segment(self, x0, y0, x1, y1, colour, thick=1):
        """Bresenham segment stamped with a square brush."""
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        step_x = 1 if x0 < x1 else -1
        step_y = 1 if y0 < y1 else -1
        err = dx + dy
        half = thick // 2
        while True:
            self.fill_rect(x0 - half, y0 - half, thick, thick, colour)
            if x0 == x1 and y0 == y1:
                return
            doubled = 2 * err
            if doubled >= dy:
                err += dy
                x0 += step_x
            if doubled <= dx:
                err += dx
                y0 += step_y

    def blob(self, cx, cy, radius, colour):
        """Filled circle."""
        for yy in range(cy - radius, cy + radius + 1):
            dy = yy - cy
            if abs(dy) > radius:
                continue
            half_w = int((radius * radius - dy * dy) ** 0.5)
            self.fill_rect(cx - half_w, yy, 2 * half_w + 1, 1, colour)

    def halo(self, cx, cy, radius, colour, thick=2):
        """Circle outline, `thick` pixels wide."""
        inner = radius - thick
        for yy in range(cy - radius, cy + radius + 1):
            for xx in range(cx - radius, cx + radius + 1):
                d2 = (xx - cx) ** 2 + (yy - cy) ** 2
                if inner * inner <= d2 <= radius * radius:
                    self.set_pixel(xx, yy, colour)

    def wedge(self, ax, ay, bx, by, cx, cy, colour):
        """Filled triangle, scanline by scanline, top vertex first."""
        verts = sorted(((ax, ay), (bx, by), (cx, cy)), key=lambda p: p[1])
        (x_top, y_top), (x_mid, y_mid), (x_bot, y_bot) = verts

        def interp_x(y, p, q):
            if q[1] == p[1]:
                return p[0]
            return p[0] + (q[0] - p[0]) * (y - p[1]) / (q[1] - p[1])

        for y in range(y_top, y_bot + 1):
            left_edge = interp_x(y, (x_top, y_top), (x_mid, y_mid)) if y < y_mid \
                else interp_x(y, (x_mid, y_mid), (x_bot, y_bot))
            right_edge = interp_x(y, (x_top, y_top), (x_bot, y_bot))
            lo, hi = sorted((int(round(left_edge)), int(round(right_edge))))
            self.fill_rect(lo, y, hi - lo + 1, 1, colour)

    def rays(self, cx, cy, radius, colour, count=10):
        """Starburst: `count` spokes plus a solid hub."""
        import math

        for k in range(count):
            angle = 2 * math.pi * k / count
            tip_x = cx + int(radius * math.cos(angle))
            tip_y = cy + int(radius * math.sin(angle))
            self.segment(cx, cy, tip_x, tip_y, colour, thick=3)
        self.blob(cx, cy, max(3, radius // 3), colour)

    # -- text ---------------------------------------------------------------
    def draw_glyph(self, x, y, size, colour, char):
        rows = GLYPHS.get(char, UNKNOWN_GLYPH)
        for row_idx, bits in enumerate(rows):
            for col in range(GLYPH_COLS):
                if bits >> (GLYPH_COLS - 1 - col) & 1:
                    self.fill_rect(x + col * size, y + row_idx * size,
                                   size, size, colour)

    def draw_text(self, x, y, size, colour, string, align="left"):
        string = string.upper()
        if align == "center":
            x -= measure(string, size) // 2
        elif align == "right":
            x -= measure(string, size)
        for i, char in enumerate(string):
            self.draw_glyph(x + i * GLYPH_ADVANCE * size, y, size, colour, char)

    def draw_paragraph(self, x, y, width, size, colour, string,
                       leading=None, limit=None):
        """Wrapped text block; returns the y just below the last line."""
        if leading is None:
            leading = GLYPH_ROWS * size + 3
        lines = split_lines(string, width, size)
        if limit is not None:
            lines = lines[:limit]
        for i, line in enumerate(lines):
            self.draw_text(x, y + i * leading, size, colour, line)
        return y + len(lines) * leading


# ---------------------------------------------------------------------------
# Story illustrations. Each takes (sheet, x, y, w, h) and paints inside
# that box. Subjects match the six stories in news.json.
# ---------------------------------------------------------------------------
def paint_vice_city(sheet, x, y, w, h):
    """GTA VI: neon sunset over a Vice City skyline and bay."""
    bands = [(PLUM, 0), (TANGERINE, h // 3), (PEACH, 2 * h // 3)]
    for colour, top in bands:
        sheet.fill_rect(x, y + top, w, h // 3, colour)
    # Low sun, half-hidden behind the towers.
    sun_cx, sun_cy = x + w // 2, y + h // 2 + 18
    sheet.blob(sun_cx, sun_cy, 36, GOLD)
    sheet.blob(sun_cx, sun_cy, 27, PALE_GOLD)
    # Tower silhouettes, tallest in the middle of the frame.
    towers = [(6, 44, 88), (58, 32, 128), (98, 50, 78),
              (156, 30, 118), (194, 42, 92), (244, 38, 136),
              (290, 48, 82)]
    for bx, bw, bh in towers:
        sheet.fill_rect(x + bx, y + h - bh - 30, bw, bh, DARK_BLUE)
    # A few lit windows in the towers.
    for wx, wy in ((18, 148), (70, 108), (114, 168), (168, 118),
                   (206, 158), (256, 108), (304, 168)):
        sheet.fill_rect(x + wx, y + wy, 6, 8, GOLD)
    # Bay water with white wave dashes.
    sheet.fill_rect(x, y + h - 30, w, 30, MID_BLUE)
    for i in range(5):
        sheet.fill_rect(x + 14 + i * 68, y + h - 18, 34, 4, CARD)


def paint_three_flags(sheet, x, y, w, h):
    """Shenzhen summit: three national flags on poles against the sky."""
    sheet.fill_rect(x, y, w, h, PALE_BLUE)
    sheet.fill_rect(x, y + h - 12, w, 4, INK)
    pole_xs = (x + 8, x + 30, x + 52)
    for px in pole_xs:
        sheet.rule_v(px, y + 8, h - 20, INK, thick=2)
    # China: red field, one gold star.
    sheet.fill_rect(pole_xs[0] + 2, y + 8, 16, 14, ACCENT)
    sheet.blob(pole_xs[0] + 7, y + 15, 3, GOLD)
    # Russia: white over blue over red.
    sheet.fill_rect(pole_xs[1] + 2, y + 8, 16, 5, CARD)
    sheet.fill_rect(pole_xs[1] + 2, y + 13, 16, 5, DEEP_BLUE)
    sheet.fill_rect(pole_xs[1] + 2, y + 18, 16, 4, ACCENT)
    # USA: stripes with a blue canton.
    for i in range(4):
        stripe = ACCENT if i % 2 == 0 else CARD
        sheet.fill_rect(pole_xs[2] + 2, y + 8 + i * 4, 16, 2, stripe)
    sheet.fill_rect(pole_xs[2] + 2, y + 8, 8, 8, DEEP_BLUE)
    sheet.blob(pole_xs[2] + 5, y + 12, 2, CARD)


def paint_cyclone(sheet, x, y, w, h):
    """Cyclone Akvan: spiral over the Bay of Bengal, rain at the edges."""
    sheet.fill_rect(x, y, w, h, PALE_BLUE)
    # Sandy coastline creeping in from the lower right.
    sheet.wedge(x + w, y + h, x + w - 40, y + h, x + w, y + h - 60, SAND)
    sheet.fill_rect(x + w - 34, y + h - 22, 34, 22, SAND)
    # The storm itself: nested rings and sweeping arms.
    cx, cy = x + w // 2 - 6, y + h // 2 - 4
    sheet.halo(cx, cy, 30, CARD, thick=6)
    sheet.halo(cx, cy, 20, DEEP_BLUE, thick=5)
    sheet.halo(cx, cy, 11, CARD, thick=4)
    sheet.blob(cx, cy, 6, DEEP_BLUE)
    sheet.segment(cx - 30, cy - 26, cx - 8, cy - 12, CARD, thick=4)
    sheet.segment(cx + 30, cy + 22, cx + 8, cy + 10, CARD, thick=4)
    sheet.segment(cx - 26, cy + 28, cx - 6, cy + 14, DEEP_BLUE, thick=3)
    # Slanted rain streaks in the corners.
    for rx, ry in ((10, 12), (w - 16, 10), (14, h - 18), (w - 12, h - 26)):
        sheet.segment(x + rx, y + ry, x + rx - 4, y + ry + 10, MID_BLUE, thick=2)


def paint_ballot_box(sheet, x, y, w, h):
    """Speaker nomination: a ballot box, a paper going in, a gold tick."""
    sheet.fill_rect(x, y, w, h, PAPER_SOFT)
    sheet.fill_rect(x + 10, y + 26, w - 20, h - 36, DEEP_BLUE)
    sheet.fill_rect(x + 14, y + 22, w - 28, 6, DEEP_BLUE)
    sheet.fill_rect(x + w // 2 - 10, y + 23, 20, 3, CARD)
    # The paper sliding through the slot.
    sheet.segment(x + w // 2 - 4, y + 8, x + w // 2 + 4, y + 24, INK, thick=2)
    sheet.fill_rect(x + w // 2 - 8, y + 6, 12, 16, CARD)
    sheet.frame(x + w // 2 - 8, y + 6, 12, 16, INK, thick=1)
    # Gold check mark on the front of the box.
    sheet.segment(x + 18, y + 42, x + 26, y + 50, GOLD, thick=3)
    sheet.segment(x + 26, y + 50, x + 42, y + 32, GOLD, thick=3)


def paint_deep_space(sheet, x, y, w, h):
    """Voyager 1: dish spacecraft, stars, and a dotted flight path."""
    sheet.fill_rect(x, y, w, h, DARK_BLUE)
    for sx, sy in ((8, 8), (w - 10, 12), (12, h - 12),
                   (w - 8, h - 8), (w // 2, 6)):
        sheet.fill_rect(x + sx - 1, y + sy - 1, 3, 3, CARD)
    # Dotted trajectory climbing away from the craft.
    for i in range(5):
        sheet.blob(x + 8 + i * 9, y + h - 14 - i * 7, 2, GOLD)
    # Dish, body and antenna mast.
    cx, cy = x + w // 2 + 6, y + h // 2 - 2
    sheet.wedge(cx - 14, cy - 10, cx + 12, cy - 2, cx - 14, cy + 8, GOLD)
    sheet.blob(cx + 2, cy, 5, CARD)
    sheet.segment(cx + 2, cy, cx + 16, cy - 14, CARD, thick=2)
    sheet.blob(cx + 16, cy - 14, 2, CARD)


def paint_all_clear(sheet, x, y, w, h):
    """Saudi all-clear: a green shield with a white inner shield and tick."""
    sheet.fill_rect(x, y, w, h, PALE_LEAF)
    cx = x + w // 2
    # Outer shield: domed top, straight sides, pointed base.
    sheet.blob(cx, y + 18, 18, LEAF)
    sheet.fill_rect(cx - 18, y + 18, 36, 18, LEAF)
    sheet.wedge(cx - 18, y + 18, cx + 18, y + 18, cx, y + h - 10, LEAF)
    # Inner white shield, inset by the same margin on every side.
    sheet.fill_rect(cx - 12, y + 23, 24, 11, CARD)
    sheet.wedge(cx - 12, y + 23, cx + 12, y + 23, cx, y + h - 15, CARD)
    # The tick.
    sheet.segment(cx - 8, y + 32, cx - 1, y + 40, LEAF, thick=4)
    sheet.segment(cx - 1, y + 40, cx + 10, y + 26, LEAF, thick=4)


ILLUSTRATIONS = {
    "game": paint_vice_city,
    "summit": paint_three_flags,
    "storm": paint_cyclone,
    "ballot": paint_ballot_box,
    "voyager": paint_deep_space,
    "shield": paint_all_clear,
}


# ---------------------------------------------------------------------------
# PNG encoding (truecolour, 8 bit, no interlace, filter type 0 per row).
# ---------------------------------------------------------------------------
def make_chunk(kind, payload):
    size = struct.pack(">I", len(payload))
    crc = struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
    return size + kind + payload + crc


def encode_png(sheet):
    header = struct.pack(">IIBBBBB", sheet.width, sheet.height, 8, 2, 0, 0, 0)
    stride = sheet.width * 3
    scanlines = bytearray()
    for row in range(sheet.height):
        scanlines.append(0)  # filter: none
        scanlines += sheet.pixels[row * stride:(row + 1) * stride]
    return (
        b"\x89PNG\r\n\x1a\n"
        + make_chunk(b"IHDR", header)
        + make_chunk(b"IDAT", zlib.compress(bytes(scanlines), 9))
        + make_chunk(b"IEND", b"")
    )


# ---------------------------------------------------------------------------
# Page composition
# ---------------------------------------------------------------------------
def draw_masthead(sheet, data):
    sheet.draw_text(PAGE_W // 2, 26, 6, INK, data["masthead"], align="center")
    sheet.rule_h(MARGIN, 84, PAGE_W - 2 * MARGIN, INK, thick=3)
    sheet.draw_text(PAGE_W // 2, 94, 3, ACCENT, data["date_label"],
                    align="center")
    sheet.rule_h(MARGIN, 130, PAGE_W - 2 * MARGIN, ACCENT, thick=5)


def draw_lead(sheet, story):
    top, height = 148, 272
    sheet.fill_rect(MARGIN, top, PAGE_W - 2 * MARGIN, height, CARD)
    sheet.frame(MARGIN, top, PAGE_W - 2 * MARGIN, height, INK, thick=3)
    ILLUSTRATIONS[story["icon"]](sheet, MARGIN + 4, top + 4, 360, 264)
    sheet.frame(MARGIN + 4, top + 4, 360, 264, INK, thick=2)
    text_x = 412
    sheet.draw_text(text_x, top + 20, 2, ACCENT, story["kicker"])
    sheet.draw_paragraph(text_x, top + 48, 576, 4, INK,
                         story["headline"], leading=34)
    sheet.draw_paragraph(text_x, top + 164, 576, 2, INK,
                         story["summary"], leading=17)


def draw_story_card(sheet, story, x, y, w, h, icon_size,
                    headline_size, headline_leading):
    sheet.fill_rect(x, y, w, h, CARD)
    sheet.frame(x, y, w, h, INK, thick=2)
    pad = 10 if icon_size <= 76 else 12
    ILLUSTRATIONS[story["icon"]](sheet, x + pad, y + pad,
                                 icon_size, icon_size)
    sheet.frame(x + pad, y + pad, icon_size, icon_size, INK, thick=1)
    text_x = x + pad + icon_size + 10
    text_w = x + w - pad - text_x
    sheet.draw_text(text_x, y + 14, 2, ACCENT, story["kicker"])
    headline_bottom = sheet.draw_paragraph(
        text_x, y + 36, text_w, headline_size, INK,
        story["headline"], leading=headline_leading)
    # Summary follows the headline instead of sitting at a fixed offset,
    # but never starts lower than the old fixed position would allow.
    summary_y = min(headline_bottom + 10, y + h - 84)
    sheet.draw_paragraph(x + pad, summary_y, w - 2 * pad, 2, INK,
                         story["summary"], leading=17)


def draw_footer(sheet, data):
    sheet.rule_h(MARGIN, 868, PAGE_W - 2 * MARGIN, INK, thick=3)
    sheet.draw_text(MARGIN, 880, 2, ACCENT, "ALSO TODAY")
    for i, item in enumerate(data["also"]):
        ix = MARGIN + (i % 2) * 500
        iy = 904 + (i // 2) * 22
        sheet.fill_rect(ix, iy + 3, 8, 8, ACCENT)
        sheet.draw_text(ix + 14, iy, 2, INK, item)
    sheet.draw_text(PAGE_W // 2, 952, 2, DEEP_BLUE, data["numbers"],
                    align="center")
    sheet.draw_text(PAGE_W // 2, 976, 2, FAINT, data["footer_note"],
                    align="center")


def compose(data):
    sheet = Sheet(PAGE_W, PAGE_H, PAPER)
    draw_masthead(sheet, data)
    draw_lead(sheet, data["lead"])

    # Second row: two half-width cards.
    card_w = (PAGE_W - 2 * MARGIN - GUTTER) // 2
    for i, story in enumerate(data["row2"]):
        draw_story_card(sheet, story, MARGIN + i * (card_w + GUTTER),
                        436, card_w, 196, 76, 3, 24)

    # Third row: three third-width cards.
    card_w = (PAGE_W - 2 * MARGIN - 2 * GUTTER) // 3
    for i, story in enumerate(data["row3"]):
        draw_story_card(sheet, story, MARGIN + i * (card_w + GUTTER),
                        648, card_w, 204, 56, 2, 17)
    draw_footer(sheet, data)
    return sheet


def main():
    here = Path(__file__).resolve().parent
    with (here / "news.json").open(encoding="utf-8") as fh:
        data = json.load(fh)
    sheet = compose(data)
    out_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "entry.png").write_bytes(encode_png(sheet))


if __name__ == "__main__":
    main()
