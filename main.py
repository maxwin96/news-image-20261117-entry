#!/usr/bin/env python3
"""One-image summary of world news for Tuesday, 17 November 2026.

Pure Python 3 standard library (zlib only). No network, no randomness,
no wall clock: two runs produce byte-identical PNG output.

Usage:  MAKEFUN_OUTPUT_DIR=out python3 main.py
Writes $MAKEFUN_OUTPUT_DIR/entry.png (default ./out/entry.png).

Design: big dated header, then six panels (2 x 3), one verified story each,
with a hand-drawn icon and a short factual label. All six stories were
verified on 18 Nov 2026 against Reuters / AP / BBC / Al Jazeera reporting
of 17 Nov 2026 (see SOURCES line drawn at the foot of the image).
"""

import os
import struct
import zlib

W, H = 1024, 1024

# ---------------------------------------------------------------- palette
PAPER = (244, 239, 230)      # warm newspaper cream
INK = (16, 35, 63)           # deep navy header
CARD = (255, 255, 255)       # panel card
CARD_LINE = (16, 35, 63)     # panel border
GOLD = (232, 184, 75)        # header accent
RED = (192, 57, 43)          # header rule
SUB = (90, 90, 90)           # sub-label grey
WHITE = (255, 255, 255)
LIGHT = (220, 228, 238)      # header subtitle

# ------------------------------------------------------------------- font
# 5x7 bitmap capitals, digits and basic punctuation. '#' = on, '.' = off.
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ",": ("00000", "00000", "00000", "00000", "00100", "00100", "01000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
}


def text_width(text, scale):
    return len(text) * 6 * scale - scale


# ----------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(w * h * 3)
        self.fill_rect(0, 0, w, h, bg)

    def set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i], self.px[i + 1], self.px[i + 2] = color

    def fill_rect(self, x, y, w, h, color):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        for yy in range(y0, y1):
            base = (yy * self.w + x0) * 3
            for xx in range(x0, x1):
                i = base + (xx - x0) * 3
                self.px[i], self.px[i + 1], self.px[i + 2] = color

    def rect(self, x, y, w, h, color, t=1):
        self.fill_rect(x, y, w, t, color)
        self.fill_rect(x, y + h - t, w, t, color)
        self.fill_rect(x, y, t, h, color)
        self.fill_rect(x + w - t, y, t, h, color)

    def line(self, x0, y0, x1, y1, color, t=1):
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        x, y = x0, y0
        while True:
            if t <= 1:
                self.set(x, y, color)
            else:
                r = t // 2
                self.fill_rect(x - r, y - r, t, t, color)
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy

    def circle(self, cx, cy, r, color):
        for yy in range(cy - r, cy + r + 1):
            dx = int((r * r - (yy - cy) ** 2) ** 0.5) if abs(yy - cy) <= r else 0
            self.fill_rect(cx - dx, yy, 2 * dx + 1, 1, color)

    def ring(self, cx, cy, r, color, t=2):
        for k in range(t):
            rr = r - k
            if rr <= 0:
                break
            steps = max(8, rr * 6)
            for s in range(steps):
                import math
                a = 2 * math.pi * s / steps
                self.set(cx + int(rr * math.cos(a)), cy + int(rr * math.sin(a)), color)

    def triangle(self, p0, p1, p2, color):
        xs = [p0[0], p1[0], p2[0]]
        ys = [p0[1], p1[1], p2[1]]
        x0, x1 = min(xs), max(xs)
        y0, y1 = min(ys), max(ys)

        def sign(ax, ay, bx, by, cx, cy):
            return (ax - cx) * (by - cy) - (bx - cx) * (ay - cy)

        d = sign(p0[0], p0[1], p1[0], p1[1], p2[0], p2[1])
        if d == 0:
            return
        for yy in range(y0, y1 + 1):
            for xx in range(x0, x1 + 1):
                s1 = sign(xx, yy, p0[0], p0[1], p1[0], p1[1])
                s2 = sign(xx, yy, p1[0], p1[1], p2[0], p2[1])
                s3 = sign(xx, yy, p2[0], p2[1], p0[0], p0[1])
                neg = (s1 < 0) or (s2 < 0) or (s3 < 0)
                pos = (s1 > 0) or (s2 > 0) or (s3 > 0)
                if not (neg and pos):
                    self.set(xx, yy, color)

    def text(self, x, y, s, scale, color):
        cx = x
        for ch in s:
            glyph = FONT.get(ch, FONT[" "])
            for row in range(7):
                bits = glyph[row]
                for col in range(5):
                    if bits[col] == "1":
                        self.fill_rect(cx + col * scale, y + row * scale,
                                       scale, scale, color)
            cx += 6 * scale

    def text_center(self, cx, y, s, scale, color):
        self.text(cx - text_width(s, scale) // 2, y, s, scale, color)

    def text_right(self, x, y, s, scale, color):
        self.text(x - text_width(s, scale), y, s, scale, color)


def tint(color, frac):
    """Mix a colour towards white (light tint for icon backdrops)."""
    return tuple(int(c + (255 - c) * frac) for c in color)


# ------------------------------------------------------------------- icons
# Each icon draws inside box (x0, y0, x1, y1) in the panel colour `c`.

def icon_bridge(cv, x0, y0, x1, y1, c):
    cx = (x0 + x1) // 2
    cy = (y0 + y1) // 2
    deck = cy - 6
    # towers
    cv.fill_rect(x0 + 26, deck - 52, 10, 52, c)
    cv.fill_rect(x1 - 36, deck - 52, 10, 52, c)
    # deck, split in the middle: the broken span
    cv.fill_rect(x0 + 8, deck, cx - x0 - 26, 8, c)
    cv.fill_rect(cx + 18, deck, x1 - cx - 26, 8, c)
    # arch cables from towers to deck
    cv.line(x0 + 31, deck - 52, cx - 18, deck, c, 3)
    cv.line(x1 - 31, deck - 52, cx + 18, deck, c, 3)
    # fallen span piece, tilted, below the gap
    cv.line(cx - 16, deck + 26, cx + 16, deck + 40, c, 7)
    # water below
    cv.line(x0 + 8, y1 - 12, x1 - 8, y1 - 12, c, 3)
    cv.line(x0 + 24, y1 - 4, x1 - 24, y1 - 4, c, 3)


def icon_radar(cv, x0, y0, x1, y1, c):
    cx = (x0 + x1) // 2
    cy = (y0 + y1) // 2
    # drone, top left, clearly separated from the dish
    dx, dy = x0 + 52, y0 + 18
    cv.fill_rect(dx - 12, dy - 5, 24, 10, c)
    cv.line(dx - 22, dy - 12, dx - 4, dy - 12, c, 3)
    cv.line(dx + 4, dy - 12, dx + 22, dy - 12, c, 3)
    cv.line(dx - 22, dy + 12, dx - 4, dy + 12, c, 3)
    cv.line(dx + 4, dy + 12, dx + 22, dy + 12, c, 3)
    cv.line(dx, dy + 5, dx, dy + 14, c, 3)
    # radar mast + dish (open bowl facing up-right)
    cv.fill_rect(cx - 4, cy - 10, 8, y1 - cy - 4, c)
    cv.line(cx - 4, cy - 10, cx - 44, cy - 48, c, 6)
    cv.line(cx - 4, cy - 10, cx + 40, cy - 52, c, 6)
    cv.line(cx - 44, cy - 48, cx + 40, cy - 52, c, 6)
    # sweep ring around the dish
    cv.ring(cx, cy - 8, 52, c, 3)


def icon_plane(cv, x0, y0, x1, y1, c):
    cx = (x0 + x1) // 2
    cy = (y0 + y1) // 2
    # fuselage
    cv.fill_rect(x0 + 30, cy - 12, x1 - x0 - 78, 24, c)
    cv.circle(x1 - 48, cy, 12, c)
    # nose windows
    cv.fill_rect(x1 - 56, cy - 6, 8, 6, WHITE)
    # wings
    cv.triangle((cx - 10, cy - 8), (cx + 34, cy - 8), (cx - 26, cy - 52), c)
    cv.triangle((cx - 6, cy + 8), (cx + 26, cy + 8), (cx - 18, cy + 44), c)
    # tail
    cv.triangle((x0 + 30, cy - 8), (x0 + 52, cy - 8), (x0 + 30, cy - 44), c)
    # windows
    for i in range(5):
        cv.fill_rect(x0 + 48 + i * 16, cy - 4, 8, 8, WHITE)
    # motion lines
    cv.line(x0 + 2, cy + 26, x0 + 22, cy + 26, c, 3)
    cv.line(x0 + 8, cy + 36, x0 + 30, cy + 36, c, 3)


def icon_podium(cv, x0, y0, x1, y1, c):
    cx = (x0 + x1) // 2
    # flag on a pole
    cv.fill_rect(x0 + 22, y0 + 4, 6, y1 - y0 - 8, c)
    cv.fill_rect(x0 + 28, y0 + 6, 52, 26, c)
    cv.triangle((x0 + 80, y0 + 6), (x0 + 80, y0 + 32), (x0 + 64, y0 + 19), PAPER)
    # podium: flat-topped stand with a top slab
    cv.fill_rect(cx - 40, y0 + 62, 80, y1 - 6 - (y0 + 62), c)
    cv.fill_rect(cx - 52, y0 + 54, 104, 10, c)
    cv.fill_rect(cx - 52, y1 - 12, 104, 8, c)
    # microphone on a stand
    cv.line(cx + 20, y0 + 54, cx + 32, y0 + 34, c, 4)
    cv.circle(cx + 34, y0 + 30, 8, c)


def icon_gavel(cv, x0, y0, x1, y1, c):
    cx = (x0 + x1) // 2
    cy = (y0 + y1) // 2
    # gavel head (diagonal) + handle
    cv.line(cx - 34, cy - 30, cx + 30, cy + 6, c, 16)
    cv.line(cx + 6, cy - 6, cx - 30, cy + 34, c, 10)
    # strike block
    cv.fill_rect(cx - 8, y1 - 22, 64, 12, c)
    # motion ticks
    cv.line(cx + 44, cy - 34, cx + 56, cy - 44, c, 4)
    cv.line(cx + 52, cy - 18, cx + 66, cy - 22, c, 4)


def icon_rocket(cv, x0, y0, x1, y1, c):
    cx = (x0 + x1) // 2
    cy = (y0 + y1) // 2
    # flame
    cv.triangle((cx - 12, cy + 34), (cx + 12, cy + 34), (cx, y1 - 4), (211, 84, 0))
    # body
    cv.fill_rect(cx - 16, cy - 44, 32, 78, c)
    cv.triangle((cx - 16, cy - 44), (cx + 16, cy - 44), (cx, cy - 66), c)
    # fins
    cv.triangle((cx - 16, cy + 10), (cx - 16, cy + 34), (cx - 38, cy + 34), c)
    cv.triangle((cx + 16, cy + 10), (cx + 16, cy + 34), (cx + 38, cy + 34), c)
    # window
    cv.circle(cx, cy - 18, 8, WHITE)
    cv.circle(cx, cy - 18, 5, c)
    # lost satellites: small squares drifting away
    cv.fill_rect(x1 - 34, y0 + 8, 10, 10, c)
    cv.fill_rect(x1 - 52, y0 + 26, 8, 8, c)
    cv.fill_rect(x0 + 22, y0 + 14, 8, 8, c)


# ------------------------------------------------------------------ panels
# (accent colour, tag, title line 1, title line 2, sub-label, icon fn)
PANELS = [
    ((192, 57, 43), "WAR",
     "CRIMEA BRIDGE", "HIT, SPAN FALLS", "TRAFFIC SUSPENDED", icon_bridge),
    ((211, 84, 0), "GULF",
     "IRAN DRONES HIT", "US RADAR, BAHRAIN", "INTERCEPTED, NO CASUALTIES", icon_radar),
    ((36, 113, 163), "DIPLOMACY",
     "TRUMP IN MANILA", "FOR ASEAN SUMMIT", "ASIA TRIP BEGINS", icon_plane),
    ((20, 143, 119), "POLITICS",
     "MONGOLIA LEADER", "TO RESIGN", "DENIES GRAFT CLAIMS", icon_podium),
    ((125, 60, 152), "SANCTIONS",
     "UK SANCTIONS", "SETTLEMENT FIRMS", "8 FIRMS, WEST BANK", icon_gavel),
    ((44, 62, 80), "SPACE",
     "ROCKET FAILS", "40 SATELLITES LOST", "ULA VULCAN, FIRST LOSS", icon_rocket),
]


def draw_panel(cv, x, y, w, h, num, panel):
    color, tag, line1, line2, sub, icon = panel
    cv.fill_rect(x, y, w, h, CARD)
    cv.rect(x, y, w, h, CARD_LINE, 2)
    cv.fill_rect(x, y, w, 7, color)
    # number badge
    bx, by = x + 30, y + 32
    cv.circle(bx, by, 15, color)
    cv.text_center(bx, by - 7, str(num), 2, WHITE)
    # tag, top right
    cv.text_right(x + w - 16, y + 24, tag, 2, color)
    # icon on a light tint band
    cv.fill_rect(x + 16, y + 52, w - 32, 92, tint(color, 0.88))
    icon(cv, x + 16, y + 52, x + w - 16, y + 144, color)
    # titles + sub-label, centred
    cx = x + w // 2
    cv.text_center(cx, y + 156, line1, 4, INK)
    cv.text_center(cx, y + 190, line2, 4, INK)
    cv.text_center(cx, y + 228, sub, 2, SUB)


def draw():
    cv = Canvas(W, H, PAPER)
    # header band
    cv.fill_rect(0, 0, W, 152, INK)
    cv.fill_rect(0, 152, W, 6, RED)
    cv.text_center(W // 2, 16, "TUESDAY", 3, GOLD)
    cv.text_center(W // 2, 44, "17 NOVEMBER 2026", 8, WHITE)
    cv.text_center(W // 2, 116, "WORLD NEWS IN ONE IMAGE", 3, LIGHT)
    # panels: 2 columns x 3 rows
    px, py = 24, 172
    pw, ph = 480, 260
    gx, gy = 16, 14
    for i, panel in enumerate(PANELS):
        col = i % 2
        row = i // 2
        draw_panel(cv, px + col * (pw + gx), py + row * (ph + gy),
                   pw, ph, i + 1, panel)
    # footer: sources
    cv.text_center(W // 2, 992, "SOURCES: REUTERS - AP - BBC - AL JAZEERA", 2, SUB)
    return cv


# --------------------------------------------------------------------- png
def chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return out


def write_png(cv, path):
    raw = bytearray()
    stride = W * 3
    for yy in range(H):
        raw.append(0)  # filter: none
        raw += cv.px[yy * stride:(yy + 1) * stride]
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "./out")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.png")
    size = write_png(draw(), path)
    print("wrote %s (%d bytes, %dx%d)" % (path, size, W, H))


if __name__ == "__main__":
    main()
