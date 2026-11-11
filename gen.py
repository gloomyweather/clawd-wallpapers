#!/usr/bin/env python3
"""clawd dot-matrix wallpapers.

scenes are drawn on a 256x144 grid of "cells"; every cell becomes one dot whose
brightness is the cell value. clawd is pasted on top as solid pixel art.

usage: gen.py [outdir] [scene ...]

outdir defaults to ./wallpapers next to this script. the label in the corner
uses a nerd font for its music-note glyph: set CLAWD_FONT=/path/to/font.ttf to
pick one, otherwise a few common locations are tried and the glyph is dropped
if none is found.
"""
import os
import random
import sys
import zlib

from PIL import Image, ImageDraw, ImageFont

GW, GH = 256, 144
CELL = 30                     # render px per cell (7680x4320 master, downsampled)
SIZES = [(3840, 2160), (1920, 1080)]
FONTS = [
    os.environ.get("CLAWD_FONT", ""),
    "/usr/share/fonts/TTF/JetBrainsMonoNerdFont-Regular.ttf",
    os.path.expanduser("~/.local/share/fonts/JetBrainsMonoNerdFont-Regular.ttf"),
    "/Library/Fonts/JetBrainsMonoNerdFont-Regular.ttf",
]


def load_font(size):
    """returns (font, has_music_glyph)"""
    for path in FONTS:
        if path and os.path.exists(path):
            return ImageFont.truetype(path, size), True
    return ImageFont.load_default(size), False


# ───────────────────────── scene canvas ─────────────────────────

class S:
    def __init__(self, seed):
        self.v = Image.new("L", (GW, GH), 0)
        self.d = ImageDraw.Draw(self.v)
        self.t = Image.new("RGB", (GW, GH))          # tint colour per cell
        self.td = ImageDraw.Draw(self.t)
        self.m = Image.new("L", (GW, GH), 0)          # tint mask
        self.md = ImageDraw.Draw(self.m)
        self.r = random.Random(seed)

    # plain value drawing (half-open rects)
    def rect(self, x0, y0, x1, y1, f=None, l=None, w=1):
        self.d.rectangle([x0, y0, x1 - 1, y1 - 1], fill=f, outline=l, width=w)

    def rrect(self, x0, y0, x1, y1, rad, f=None, l=None, w=1):
        self.d.rounded_rectangle([x0, y0, x1 - 1, y1 - 1], rad, fill=f, outline=l, width=w)

    def ell(self, x0, y0, x1, y1, f=None, l=None, w=1):
        self.d.ellipse([x0, y0, x1 - 1, y1 - 1], fill=f, outline=l, width=w)

    def circ(self, cx, cy, r, f=None, l=None, w=1):
        self.d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=f, outline=l, width=w)

    def line(self, pts, v, w=1):
        self.d.line(pts, fill=v, width=w)

    def poly(self, pts, f=None, l=None):
        self.d.polygon(pts, fill=f, outline=l)

    def pt(self, x, y, v):
        if 0 <= x < GW and 0 <= y < GH:
            self.d.point((x, y), v)

    def dots(self, x0, y0, x1, y1, v, p, jitter=0):
        """sparse random dots — texture for shadows / glow"""
        for y in range(y0, y1):
            for x in range(x0, x1):
                if self.r.random() < p:
                    self.pt(x, y, max(1, v + self.r.randint(-jitter, jitter)))

    def fade(self, x0, y0, x1, y1, v0, v1, p0=1.0, p1=1.0):
        """vertical gradient, value and density interpolated"""
        for y in range(y0, y1):
            k = (y - y0) / max(1, y1 - y0 - 1)
            v, p = int(v0 + (v1 - v0) * k), p0 + (p1 - p0) * k
            for x in range(x0, x1):
                if self.r.random() < p:
                    self.pt(x, y, max(1, v))

    # tinted drawing (coloured dots)
    def tpoly(self, pts, v, col):
        self.d.polygon(pts, fill=v); self.td.polygon(pts, fill=col); self.md.polygon(pts, fill=255)

    def trect(self, x0, y0, x1, y1, v, col):
        b = [x0, y0, x1 - 1, y1 - 1]
        self.d.rectangle(b, fill=v); self.td.rectangle(b, fill=col); self.md.rectangle(b, fill=255)

    def tpt(self, x, y, v, col):
        if 0 <= x < GW and 0 <= y < GH:
            self.d.point((x, y), v); self.td.point((x, y), col); self.md.point((x, y), 255)

    def note(self, x, y, v=230):
        self.rect(x + 2, y, x + 3, y + 5, f=v)
        self.rect(x, y + 4, x + 3, y + 6, f=v)
        self.rect(x + 3, y, x + 5, y + 1, f=v)
        self.pt(x + 5, y + 1, v)


# ───────────────────────── clawd sprite ─────────────────────────

O = (217, 119, 87)
K = (18, 18, 18)
OX, OY, SW, SH = 22, 18, 72, 52


def clawd(eyes="open", acc=()):
    im = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)

    def R(x0, y0, x1, y1, c):
        d.rectangle([OX + x0, OY + y0, OX + x1 - 1, OY + y1 - 1], fill=c)

    behind = [a for a in acc if a in ("basket_back",)]
    for a in behind:
        ACC[a](R)
    R(4, 0, 24, 12, O)
    R(0, 4, 28, 8, O)
    for lx in (4, 8, 18, 22):
        R(lx, 12, lx + 2, 16, O)
    if eyes == "open":
        R(8, 2, 10, 4, K); R(18, 2, 20, 4, K)
    elif eyes == "closed":
        R(7, 3, 11, 4, K); R(17, 3, 21, 4, K)
    elif eyes == "happy":                       # ^ ^
        R(7, 3, 11, 4, K); R(17, 3, 21, 4, K)
    elif eyes == "down":
        R(8, 3, 10, 5, K); R(18, 3, 20, 5, K)
    for a in acc:
        if a not in behind:
            ACC[a](R)
    return im


def acc_headphones(R):
    B, B2 = (52, 98, 176), (36, 70, 132)
    R(7, -5, 21, -4, B)
    R(5, -4, 8, -3, B); R(20, -4, 23, -3, B)
    R(3, -3, 6, -1, B); R(22, -3, 25, -1, B)
    R(3, -1, 5, 1, B); R(23, -1, 25, 1, B)
    R(2, 0, 6, 6, B2); R(22, 0, 26, 6, B2)
    R(2, 1, 3, 5, B); R(25, 1, 26, 5, B)


def acc_chef(R):
    W, W2 = (228, 236, 248), (190, 206, 230)
    R(5, -3, 23, 0, W2)
    R(4, -9, 24, -3, W)
    R(5, -11, 11, -9, W); R(11, -12, 18, -9, W); R(18, -11, 23, -9, W)
    R(11, -8, 12, -3, W2); R(17, -8, 18, -3, W2)


def acc_pan(R):
    G, P, P2 = (128, 132, 140), (78, 80, 86), (58, 60, 64)
    R(-7, 5, 0, 6, G)
    R(-18, 5, -7, 7, P); R(-17, 7, -8, 8, P2)
    R(-16, 4, -9, 5, (238, 238, 232)); R(-14, 3, -11, 5, (246, 190, 60))
    Gr = (60, 170, 80)
    R(-15, -6, -13, -4, Gr); R(-13, -7, -12, -5, Gr); R(-10, -3, -9, -2, Gr)
    R(-17, -2, -16, -1, (170, 190, 220)); R(-12, 0, -11, 1, (170, 190, 220))


def acc_glasses(R):
    M = (112, 30, 48)
    for x0 in (6, 16):
        R(x0, -1, x0 + 6, 0, M); R(x0, 5, x0 + 6, 6, M)
        R(x0, -1, x0 + 1, 6, M); R(x0 + 5, -1, x0 + 6, 6, M)
    R(12, 1, 16, 2, M)
    R(4, 1, 6, 2, M); R(22, 1, 24, 2, M)


def acc_book(R):
    BK, BK2 = (82, 68, 168), (60, 50, 130)
    R(23, 3, 30, 13, BK)
    R(23, 3, 24, 13, BK2)
    R(24, 3, 30, 4, (236, 234, 228))
    R(29, 4, 30, 12, (236, 234, 228))


def acc_basket(R):
    BR, BRd = (176, 120, 66), (128, 84, 44)
    R(28, 0, 29, 9, BR); R(37, 0, 38, 9, BR); R(29, -1, 37, 0, BR)
    RD, GN = (218, 52, 64), (70, 160, 80)
    R(29, 6, 32, 9, RD); R(32, 5, 35, 9, RD); R(35, 7, 37, 9, RD)
    R(30, 5, 31, 6, GN); R(33, 4, 34, 5, GN); R(35, 6, 36, 7, GN)
    R(27, 9, 39, 16, BR)
    R(27, 11, 39, 12, BRd); R(27, 14, 39, 15, BRd)
    R(28, 16, 38, 17, BRd)


def acc_laptop(R):
    L, L2 = (176, 180, 188), (130, 134, 142)
    R(1, 7, 27, 16, L)
    R(1, 7, 27, 8, L2)
    R(-1, 16, 29, 17, L2)
    R(12, 10, 16, 13, (238, 238, 238))


def acc_beanie(R):
    Y, Y2 = (236, 186, 70), (196, 148, 46)
    R(6, -6, 22, -4, Y); R(4, -4, 24, -1, Y)
    R(4, -1, 24, 1, Y2)
    for x in range(5, 24, 3):
        R(x, -1, x + 1, 1, Y)
    R(12, -9, 16, -6, (240, 240, 236))


def acc_mug(R):
    W = (238, 236, 230)
    R(-6, 2, -1, 9, W)
    R(-8, 3, -6, 4, W); R(-8, 7, -6, 8, W); R(-9, 4, -8, 7, W)
    R(-5, 2, -2, 3, (120, 74, 48))
    S = (150, 150, 150)
    R(-5, -1, -4, 1, S); R(-4, -3, -3, -1, S); R(-3, -2, -2, 0, S)


def acc_umbrella(R):
    U, U2 = (64, 140, 150), (44, 110, 120)
    R(-4, -5, 36, -3, U); R(0, -7, 32, -5, U); R(6, -9, 26, -7, U)
    R(15, -10, 17, -9, U2)
    for x in (-4, 6, 16, 26):
        R(x, -3, x + 6, -2, U2)
    R(29, -3, 30, 6, (200, 200, 200))
    R(28, 5, 29, 7, (200, 200, 200))


def acc_zzz(R):
    Z = (200, 200, 210)
    for (x, y, s) in ((31, -3, 4), (37, -9, 5), (44, -17, 6)):
        R(x, y, x + s, y + 1, Z); R(x, y + s - 1, x + s, y + s, Z)
        for i in range(s):
            R(max(x, x + s - 2 - i), y + i, x + s - i, y + i + 1, Z)


ACC = dict(headphones=acc_headphones, chef=acc_chef, pan=acc_pan, glasses=acc_glasses,
           book=acc_book, basket=acc_basket, laptop=acc_laptop, beanie=acc_beanie,
           mug=acc_mug, umbrella=acc_umbrella, zzz=acc_zzz)


def acc_can(R):
    G, G2, WB = (96, 156, 120), (70, 120, 92), (120, 180, 240)
    R(29, 4, 37, 11, G); R(29, 4, 37, 5, G2)
    R(31, 2, 35, 3, G2); R(30, 3, 31, 4, G2); R(35, 3, 36, 4, G2)
    for i in range(5):
        R(37 + i, 6 - i, 38 + i, 7 - i, G)
    R(42, 0, 44, 2, G2)
    for (x, y) in ((44, 4), (43, 7), (45, 9), (44, 12), (46, 14)):
        R(x, y, x + 1, y + 2, WB)


def acc_nightcap(R):
    C, C2, W = (70, 92, 170), (52, 70, 140), (236, 236, 240)
    R(6, -5, 22, -2, C); R(10, -7, 24, -5, C); R(20, -6, 28, -4, C2)
    R(26, -4, 29, 1, C2)
    R(4, -2, 24, 0, W)
    R(27, 1, 31, 4, W)


def acc_blanket(R):
    B1, B2, B3 = (150, 70, 80), (200, 110, 100), (236, 222, 200)
    R(-8, 9, 36, 18, B1)
    for x in range(-8, 36, 6):
        R(x, 9, x + 3, 12, B2); R(x + 3, 12, x + 6, 15, B2); R(x, 15, x + 3, 18, B2)
    R(-8, 8, 36, 9, B3)


def acc_beret(R):
    Rd, Rd2 = (196, 52, 62), (150, 36, 46)
    R(4, -3, 22, 0, Rd); R(6, -5, 26, -3, Rd); R(22, -3, 26, -1, Rd2)
    R(13, -6, 15, -5, Rd2)


def acc_palette(R):
    P, P2 = (196, 160, 116), (160, 126, 86)
    R(-12, 3, -1, 10, P); R(-11, 2, -3, 3, P); R(-11, 10, -2, 11, P2)
    R(-10, 6, -8, 8, (22, 22, 22))
    for (x, y, c) in ((-11, 3, (220, 60, 60)), (-7, 3, (240, 200, 60)), (-4, 4, (70, 120, 220)),
                      (-6, 8, (80, 170, 90)), (-3, 7, (240, 240, 240))):
        R(x, y, x + 2, y + 2, c)


def acc_brush(R):
    R(28, -2, 29, 6, (170, 120, 70))
    R(28, -4, 29, -2, (200, 200, 200))
    R(28, -6, 29, -4, (70, 120, 220))


def acc_rod(R):
    Rd = (150, 104, 60)
    for i in range(21):
        R(27 + i, 6 - i, 28 + i, 7 - i, Rd)
    R(30, 2, 33, 5, (90, 90, 96)); R(31, 3, 32, 4, (180, 180, 186))


def acc_scarf(R):
    Sc, Sc2 = (196, 52, 62), (150, 36, 46)
    R(4, 4, 24, 7, Sc)
    for x in range(6, 24, 4):
        R(x, 4, x + 1, 7, Sc2)
    R(17, 7, 21, 13, Sc); R(17, 12, 21, 13, Sc2)


def acc_helmet(R):
    W, Gl = (232, 236, 244), (150, 190, 230)
    R(2, -7, 26, -6, W); R(0, -6, 2, -4, W); R(26, -6, 28, -4, W)
    R(-1, -4, 0, 4, W); R(28, -4, 29, 4, W)
    R(0, 4, 28, 5, W)
    R(4, -5, 6, -4, Gl); R(3, -4, 4, -1, Gl)
    R(13, -10, 15, -7, W); R(12, -12, 16, -10, (232, 120, 90))


def acc_controller(R):
    C, C2 = (60, 62, 72), (40, 42, 50)
    R(5, 6, 23, 10, C); R(3, 8, 8, 12, C); R(20, 8, 25, 12, C)
    R(7, 7, 8, 10, C2); R(6, 8, 9, 9, C2)
    R(19, 7, 20, 8, (220, 70, 80)); R(21, 8, 22, 9, (80, 140, 230))


ACC.update(can=acc_can, nightcap=acc_nightcap, blanket=acc_blanket, beret=acc_beret,
           palette=acc_palette, brush=acc_brush, rod=acc_rod, scarf=acc_scarf,
           helmet=acc_helmet, controller=acc_controller)


# ───────────────────────── scenes ─────────────────────────

def scene_vinyl():
    s = S(1)
    # floor + rug
    s.rect(0, 128, 256, 144, f=26)
    for x in range(-40, 256, 14):
        s.line([(x, 144), (x + 10, 128)], 46)
    s.ell(70, 125, 172, 141, f=60)
    s.ell(74, 127, 168, 139, l=110)
    # shelf unit
    s.rect(0, 40, 54, 128, l=200, w=2)
    for y in (62, 84, 106):
        s.rect(0, y, 54, y + 2, f=200)
    for i, x in enumerate(range(4, 28, 2)):
        h = s.r.randint(11, 18)
        s.rect(x, 62 - h, x + 1, 62, f=210 if i % 2 else 140)
    s.rect(31, 45, 49, 62, f=100, l=210)
    s.circ(40, 50, 3, l=230); s.circ(40, 57, 2, f=230)
    xs = 4
    for w, h, lean in ((4, 16, 0), (3, 14, 0), (5, 17, 0), (3, 12, 0), (4, 15, 2), (6, 6, 0)):
        if lean:
            s.poly([(xs, 84), (xs + w, 84), (xs + w + 5, 84 - h), (xs + 5, 84 - h)], f=170, l=220)
            xs += w + 6
        else:
            s.rect(xs, 84 - h, xs + w, 84, f=150, l=220); xs += w + 1
    s.rect(40, 76, 50, 84, f=120, l=210)  # pot
    for (a, b) in (((45, 76), (38, 66)), ((45, 76), (45, 64)), ((45, 76), (51, 68)), ((45, 76), (42, 62))):
        s.line([a, b], 200)
    s.rect(4, 92, 50, 106, l=200)
    for x in range(7, 48, 3):
        s.rect(x, 89, x + 2, 106, f=160)
    s.rect(4, 110, 24, 128, f=90, l=210); s.circ(14, 116, 4, l=230); s.circ(14, 124, 2, f=230)
    s.rect(30, 110, 50, 128, f=90, l=210); s.circ(40, 116, 4, l=230); s.circ(40, 124, 2, f=230)
    # turntable on top
    s.rect(6, 32, 46, 40, f=110, l=220)
    s.ell(10, 33, 32, 39, f=200); s.ell(19, 35, 23, 37, f=60)
    s.line([(40, 34), (36, 37)], 230)
    # wall art
    s.rect(4, 4, 46, 26, f=30, l=200)
    for i in range(4):
        s.poly([(9 + i * 9, 23), (16 + i * 9, 7), (20 + i * 9, 7), (13 + i * 9, 23)], f=210)
    s.rect(58, 10, 92, 42, f=50, l=200)
    s.poly([(60, 40), (70, 24), (76, 31), (83, 19), (90, 40)], f=170)
    s.circ(64, 17, 2, f=230)
    s.rect(62, 50, 92, 80, l=200)
    s.circ(77, 65, 11, f=150); s.circ(77, 65, 7, l=90); s.circ(77, 65, 2, f=40)
    # disco ball
    s.line([(130, 0), (130, 14)], 180)
    cx, cy, r = 130, 34, 19
    for y in range(cy - r, cy + r + 1):
        for x in range(cx - r, cx + r + 1):
            dx, dy = x - cx, y - cy
            if dx * dx + dy * dy <= r * r:
                facet = ((x - cx + 30) // 3 + (y - cy + 30) // 3) % 2
                shade = 1 - (dx + dy) / (2.2 * r)
                v = (55 + 200 * facet) * min(1, max(0.3, shade))
                s.pt(x, y, int(v))
    s.circ(cx, cy, r, l=230)
    for (x, y) in ((104, 18), (158, 22), (112, 58), (150, 60), (96, 40), (166, 44), (122, 6), (142, 64)):
        s.pt(x, y, 255); s.pt(x - 1, y, 120); s.pt(x + 1, y, 120); s.pt(x, y - 1, 120); s.pt(x, y + 1, 120)
    # window
    s.rect(176, 8, 244, 70, l=210, w=2)
    s.rect(209, 8, 211, 70, f=210); s.rect(176, 38, 244, 40, f=210)
    s.circ(228, 22, 7, f=230); s.circ(225, 20, 6, f=0)
    s.dots(178, 10, 242, 68, 120, 0.03)
    s.rect(172, 70, 248, 73, f=200)
    # floor lamp
    s.poly([(144, 54), (160, 54), (164, 66), (140, 66)], f=190, l=240)
    s.rect(151, 66, 153, 126, f=170); s.rect(144, 126, 160, 128, f=200)
    s.fade(138, 67, 166, 90, 70, 20, 0.5, 0.1)
    # sofa
    s.rrect(170, 86, 250, 112, 4, f=90, l=170)
    s.rect(209, 88, 210, 110, f=150)
    s.rrect(164, 98, 178, 126, 3, f=110, l=180); s.rrect(242, 98, 256, 126, 3, f=110, l=180)
    s.rect(176, 110, 244, 122, f=130, l=180)
    s.rect(168, 126, 171, 128, f=200); s.rect(250, 126, 253, 128, f=200)
    s.rrect(186, 92, 204, 108, 3, f=150, l=210)
    # notes
    s.note(92, 96); s.note(132, 90); s.note(140, 102, 170)
    return s, dict(x=98, y=112, eyes="closed", acc=("headphones",),
                   label="clawd — lo-fi beats to refactor to")


def scene_kitchen():
    s = S(2)
    # floor tiles
    for y in range(128, 144):
        for x in range(GW):
            s.pt(x, y, 70 if ((x // 4 + y // 4) % 2) else 30)
    # upper cabinets
    for x0 in (0, 36):
        s.rect(x0 + 2, 0, x0 + 34, 46, f=110, l=220, w=2)
        s.rect(x0 + 7, 5, x0 + 29, 41, f=40, l=180)
    s.rect(30, 20, 32, 28, f=240); s.rect(40, 20, 42, 28, f=240)
    s.rect(74, 0, 100, 46, f=110, l=220, w=2)
    s.circ(87, 14, 6, l=230); s.rect(84, 26, 90, 40, l=200)
    # rail + utensils
    s.rect(0, 54, 60, 55, f=220)
    for x, kind in ((8, 0), (20, 1), (32, 0), (46, 2)):
        s.rect(x, 55, x + 1, 68, f=200)
        if kind == 0:
            s.ell(x - 3, 66, x + 4, 72, l=220)
        elif kind == 1:
            s.rect(x - 2, 66, x + 3, 74, f=170, l=220)
        else:
            for k in range(-2, 3, 2):
                s.rect(x + k, 66, x + k + 1, 72, f=210)
    # stove + oven
    s.rect(0, 80, 58, 128, f=110, l=220, w=2)
    s.rect(0, 80, 58, 86, f=170)
    for x in (10, 22, 34, 46):
        s.circ(x, 83, 2, f=60)
    s.rect(5, 92, 53, 122, f=40, l=200, w=2)
    s.rect(10, 96, 48, 98, f=210)
    s.fade(8, 100, 50, 120, 50, 120, 0.4, 0.9)
    # stool
    s.rect(60, 110, 96, 113, f=220)
    for x in (63, 91):
        s.rect(x, 113, x + 2, 128, f=200)
    s.rect(63, 120, 93, 121, f=170)
    # counter
    s.rect(104, 82, 256, 86, f=230)
    s.rect(106, 86, 256, 128, f=100, l=210, w=2)
    for x0 in (110, 160, 210):
        s.rect(x0, 94, x0 + 42, 124, f=40, l=200)
        s.rect(x0 + 18, 98, x0 + 24, 100, f=240)
    s.rect(106, 88, 256, 92, f=150)
    # sink + faucet
    s.rect(150, 74, 152, 82, f=210)
    s.line([(151, 74), (151, 66), (156, 62), (162, 62), (166, 66), (166, 70)], 230, 2)
    s.rect(140, 78, 144, 82, f=200); s.rect(172, 78, 176, 82, f=200)
    # knife block + jars
    s.poly([(112, 82), (124, 82), (122, 68), (114, 70)], f=160, l=220)
    for x in (115, 118, 121):
        s.rect(x, 62, x + 1, 70, f=220)
    s.rect(128, 72, 134, 82, f=120, l=220); s.rect(128, 70, 134, 72, f=230)
    # bowl with salad
    s.poly([(208, 74), (240, 74), (234, 82), (214, 82)], f=170, l=230)
    for x in range(210, 238, 3):
        s.pt(x, 72 - (x % 2), 220); s.pt(x + 1, 71, 160)
    # window + plants
    s.rect(150, 6, 236, 56, l=220, w=2)
    s.rect(192, 6, 194, 56, f=220)
    s.dots(152, 8, 234, 54, 70, 0.08)
    s.rect(146, 56, 240, 59, f=230)
    for px in (158, 176, 206, 222):
        s.rect(px, 48, px + 8, 56, f=170, l=230)
        s.rect(px + 3, 36, px + 5, 48, f=210)
        s.rect(px + 1, 40, px + 3, 42, f=210); s.rect(px + 5, 38, px + 7, 40, f=210)
    # right upper cabinet
    s.rect(240, 0, 256, 60, f=110, l=220, w=2)
    return s, dict(x=64, y=94, eyes="open", acc=("chef", "pan"),
                   label="clawd — mise en place", fg=(178, 198, 232), bg=(26, 28, 34))


def scene_fireplace():
    s = S(3)
    # floor
    s.rect(0, 128, 256, 144, f=30)
    for x in range(0, 256, 6):
        s.rect(x, 130, x + 1, 144, f=120)
    s.rect(0, 128, 256, 130, f=200)
    # window
    s.rect(4, 4, 76, 66, l=220, w=2)
    s.rect(39, 4, 41, 66, f=210)
    s.rect(4, 26, 76, 27, f=210); s.rect(4, 46, 76, 47, f=210)
    s.line([(8, 20), (20, 14), (30, 16)], 90); s.line([(20, 14), (24, 8)], 90)
    s.line([(48, 60), (58, 52), (70, 52)], 80)
    s.dots(6, 6, 74, 64, 90, 0.04)
    s.rect(0, 66, 80, 69, f=210)
    # armchair
    s.rrect(6, 70, 72, 104, 8, f=120, l=210, w=2)
    s.rrect(0, 92, 16, 120, 4, f=150, l=210)
    s.rrect(62, 92, 78, 120, 4, f=150, l=210)
    s.rect(14, 102, 64, 118, f=170, l=210)
    for x in (4, 72):
        s.rect(x, 120, x + 3, 128, f=200)
    for y in range(74, 100, 4):
        s.rect(10, y, 68, y + 1, f=150)
    # side table + plant
    s.rect(86, 104, 108, 106, f=220)
    s.rect(96, 106, 98, 128, f=200); s.rect(90, 126, 104, 128, f=200)
    s.rect(90, 96, 104, 104, f=150, l=230)
    s.circ(97, 92, 2, f=240)            # mug-ish / candle flame
    s.tpt(97, 89, 200, (240, 170, 90)); s.tpt(97, 88, 140, (240, 170, 90))
    # chimney breast
    s.rect(132, 0, 220, 48, f=50, l=110)
    for y in range(4, 48, 6):
        off = 0 if (y // 6) % 2 else 6
        s.rect(132, y, 220, y + 1, f=80)
        for x in range(132 + off, 220, 12):
            s.rect(x, y - 5, x + 1, y, f=80)
    # mantel
    s.rect(116, 48, 236, 54, f=225)
    # surround
    s.rect(124, 54, 228, 128, f=120, l=210, w=2)
    s.d.pieslice([142, 64, 210, 130], 180, 360, fill=0)
    s.rect(142, 97, 211, 128, f=0)
    s.d.arc([142, 64, 210, 130], 180, 360, fill=230, width=2)
    s.rect(142, 97, 144, 128, f=230); s.rect(208, 97, 210, 128, f=230)
    s.fade(145, 72, 208, 128, 30, 70, 0.2, 0.6)
    for y in range(58, 126, 6):
        s.rect(126, y, 140, y + 1, f=170); s.rect(212, y, 226, y + 1, f=170)
    # fire
    FC, FY = (232, 128, 64), (250, 196, 96)
    s.rect(156, 120, 198, 124, f=180)
    s.line([(158, 124), (196, 116)], 200, 2); s.line([(158, 116), (196, 124)], 200, 2)
    for (x, h) in ((164, 14), (172, 22), (180, 18), (188, 12)):
        s.tpoly([(x - 6, 118), (x + 6, 118), (x + 1, 118 - h), (x - 1, 118 - h)], 200, FC)
        s.tpoly([(x - 3, 118), (x + 3, 118), (x, 118 - h // 2)], 250, FY)
    for _ in range(14):
        s.tpt(s.r.randint(158, 196), s.r.randint(84, 100), s.r.randint(120, 230), FC)
    # mantel decor
    for (a, b) in (((124, 46), (116, 30)), ((124, 46), (124, 26)), ((124, 46), (132, 32)), ((124, 46), (120, 36))):
        s.line([a, b], 210)
    for (x, y) in ((116, 30), (124, 26), (132, 32), (120, 36), (128, 30)):
        s.circ(x, y, 2, f=200)
    s.rect(120, 40, 129, 48, f=150, l=230)
    s.rect(150, 36, 152, 48, f=220); s.rect(156, 32, 158, 48, f=220)
    s.tpt(151, 34, 230, FY); s.tpt(157, 30, 230, FY)
    s.circ(184, 40, 7, f=120, l=230); s.line([(184, 40), (184, 35)], 240); s.line([(184, 40), (188, 40)], 240)
    s.rect(212, 30, 224, 48, f=140, l=220); s.rect(215, 26, 221, 30, f=200)
    # glow on floor
    s.fade(150, 130, 206, 144, 160, 60, 0.4, 0.1)
    return s, dict(x=22, y=86, eyes="open", acc=("glasses", "book"),
                   label="clawd — chapter eleven")


def scene_strawberry():
    s = S(4)
    RD, GN = (210, 56, 66), (82, 150, 84)
    # sun + clouds
    s.circ(36, 26, 13, l=170, w=2)
    s.dots(24, 14, 49, 39, 70, 0.6)
    for a in range(0, 360, 30):
        import math
        x1 = 36 + 17 * math.cos(math.radians(a)); y1 = 26 + 17 * math.sin(math.radians(a))
        x2 = 36 + 21 * math.cos(math.radians(a)); y2 = 26 + 21 * math.sin(math.radians(a))
        s.line([(x1, y1), (x2, y2)], 160)
    for (x, y, w) in ((84, 16, 40), (140, 30, 30), (226, 12, 26)):
        s.ell(x, y, x + w, y + 10, f=60)
        s.ell(x + w // 4, y - 5, x + w * 3 // 4, y + 6, f=60)
    # hills
    s.ell(-60, 72, 140, 120, f=70, l=150)
    s.ell(90, 66, 320, 124, f=50, l=130)
    s.rect(0, 92, 256, 144, f=0)
    # fence
    s.rect(0, 92, 256, 93, f=180); s.rect(0, 100, 256, 101, f=180)
    for x in range(4, 256, 18):
        s.rect(x, 88, x + 3, 110, f=200)
        s.pt(x + 1, 87, 200)
    # sign
    s.rect(196, 74, 199, 110, f=210)
    s.rrect(176, 34, 220, 76, 5, f=40, l=200, w=2)
    sb = [(188, 46), (208, 46), (206, 56), (198, 68), (190, 56)]
    s.tpoly(sb, 210, RD)
    s.tpoly([(189, 47), (193, 41), (198, 45), (203, 41), (207, 47)], 220, GN)
    s.tpoly([(197, 45), (199, 45), (199, 38), (197, 38)], 220, GN)
    for (x, y) in ((193, 51), (198, 50), (203, 51), (195, 56), (201, 56), (198, 62)):
        s.tpt(x, y, 255, (250, 220, 120))
    # field rows
    s.rect(0, 110, 256, 144, f=20)
    for i, y in enumerate((112, 120, 130, 141)):
        h = 3 + i
        for x in range(-4 + (i % 2) * 6, 260, 11 + i):
            s.ell(x, y - h, x + 8 + i * 2, y + 1, f=130 + i * 15, l=200)
            if s.r.random() < 0.45:
                bx = x + s.r.randint(1, 6 + i)
                s.tpt(bx, y, 230, RD); s.tpt(bx + 1, y, 230, RD); s.tpt(bx, y + 1, 230, RD)
                s.tpt(bx, y - 1, 200, GN)
        s.rect(0, y + 1, 256, y + 2, f=90)
    # birds
    for (x, y) in ((120, 22), (128, 18), (160, 12)):
        s.pt(x, y, 180); s.pt(x + 1, y + 1, 180); s.pt(x + 2, y, 180); s.pt(x + 3, y - 1, 180); s.pt(x - 1, y - 1, 180)
    return s, dict(x=82, y=96, eyes="open", acc=("basket",),
                   label="clawd — picking season", light=True)


def scene_desk():
    s = S(5)
    # floor
    s.rect(0, 128, 256, 144, f=24)
    s.rect(0, 128, 256, 129, f=150)
    # window with city
    s.rect(6, 6, 74, 70, l=220, w=2)
    s.rect(39, 6, 41, 70, f=210)
    s.circ(22, 20, 6, f=230); s.circ(25, 18, 6, f=0)
    s.dots(8, 8, 72, 40, 170, 0.03)
    xb = 8
    for w, h in ((8, 18), (10, 28), (6, 14), (9, 34), (7, 20), (10, 26), (8, 16)):
        if xb >= 72:
            break
        x1 = min(72, xb + w)
        s.rect(xb, 68 - h, x1, 68, f=55)
        for wy in range(70 - h, 66, 4):
            for wx in range(xb + 2, x1 - 1, 3):
                if s.r.random() < 0.4:
                    s.pt(wx, wy, 210)
        xb = x1 + 1
    s.rect(2, 70, 78, 73, f=210)
    # clock
    s.circ(98, 18, 9, f=40, l=220, w=2)
    s.line([(98, 18), (98, 12)], 240); s.line([(98, 18), (102, 20)], 240)
    # sticky notes + poster
    s.rect(140, 14, 182, 44, f=50, l=200)
    s.line([(154, 22), (148, 29), (154, 36)], 230, 2)
    s.line([(165, 20), (159, 38)], 230, 2)
    s.line([(170, 22), (176, 29), (170, 36)], 230, 2)
    for (x, y) in ((116, 32), (124, 40), (110, 44)):
        s.rect(x, y, x + 7, y + 7, f=170)
    # monitor
    s.rect(116, 56, 164, 90, f=40, l=230, w=2)
    yy = 60
    for indent, ln in ((0, 18), (4, 24), (4, 14), (8, 20), (8, 10), (4, 6), (0, 4), (0, 0), (0, 22), (4, 16)):
        if ln:
            s.rect(120 + indent, yy, 120 + indent + ln, yy + 1, f=150 if indent else 210)
        yy += 3
    s.rect(138, 90, 142, 97, f=200); s.rect(132, 96, 148, 98, f=220)
    s.rect(118, 98, 162, 100, f=150, l=220)
    # desk
    s.rect(30, 100, 196, 104, f=230)
    s.rect(34, 104, 38, 128, f=200)
    s.rect(156, 104, 194, 128, f=110, l=210)
    for y in (110, 118):
        s.rect(156, y, 194, y + 1, f=210)
    for y in (106, 113, 122):
        s.rect(172, y, 178, y + 1, f=240)
    # lamp
    # book stack
    for i, (x0, w, v) in enumerate(((38, 24, 170), (40, 20, 120), (37, 22, 200), (41, 18, 140))):
        y = 96 - i * 4
        s.rect(x0, y, x0 + w, y + 4, f=v, l=230)
        s.rect(x0 + w - 3, y + 1, x0 + w - 2, y + 3, f=240)
    # plant on desk
    s.rect(176, 90, 186, 100, f=150, l=230)
    for (a, b) in (((181, 90), (176, 80)), ((181, 90), (182, 78)), ((181, 90), (188, 82))):
        s.line([a, b], 210)
    # bookshelf
    s.rect(204, 6, 252, 128, l=210, w=2)
    for y in (34, 62, 90):
        s.rect(204, y, 252, y + 2, f=210)
    for (y0, y1) in ((8, 34), (36, 62), (64, 90), (92, 128)):
        x = 207
        while x < 248:
            w = s.r.choice((2, 3, 3, 4))
            h = s.r.randint(int((y1 - y0) * 0.55), y1 - y0 - 3)
            if s.r.random() < 0.12 and x < 238:
                x += 4
                continue
            s.rect(x, y1 - h, min(249, x + w), y1, f=s.r.choice((110, 150, 190)), l=220)
            x += w + 1
    s.rect(228, 0, 232, 6, f=0)
    return s, dict(x=76, y=84, eyes="open", acc=("mug",),
                   label="clawd — compiling at 2am", fg=(228, 222, 210), bg=(20, 19, 18))


def scene_camp():
    import math
    s = S(6)
    FC, FY = (234, 132, 60), (252, 200, 100)
    # sky
    for _ in range(260):
        x, y = s.r.randrange(GW), s.r.randrange(0, 70)
        s.pt(x, y, s.r.randint(70, 220))
    for (x, y) in ((40, 14), (180, 10), (220, 34), (110, 8), (70, 40)):
        s.pt(x, y, 255)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            s.pt(x + dx, y + dy, 150)
    s.circ(200, 22, 10, f=230); s.circ(205, 18, 9, f=0)
    # mountains
    s.poly([(-10, 96), (40, 44), (70, 70), (110, 36), (160, 80), (196, 52), (266, 96)], f=40, l=130)
    for (px, py) in ((40, 44), (110, 36), (196, 52)):
        s.poly([(px - 7, py + 7), (px, py), (px + 7, py + 7), (px + 3, py + 5), (px, py + 8), (px - 3, py + 5)], f=180)
    s.poly([(-10, 100), (30, 74), (80, 92), (140, 70), (210, 90), (266, 76), (266, 104), (-10, 104)], f=70, l=150)
    # trees
    def pine(x, base, h):
        w = h // 3
        for k in range(3):
            top = base - h + k * h // 4
            bot = top + h // 2
            ww = w * (k + 2) // 3
            s.poly([(x - ww, bot), (x, top), (x + ww, bot)], f=110, l=190)
        s.rect(x - 1, base - h // 4, x + 2, base, f=150)
    for (x, h) in ((8, 54), (24, 40), (40, 60), (226, 58), (242, 44), (254, 66), (210, 36)):
        pine(x, 110, h)
    # ground
    s.rect(0, 108, 256, 144, f=26)
    s.dots(0, 108, 256, 144, 70, 0.15, 20)
    for x in range(2, 256, 9):
        y = 112 + (x * 7) % 30
        s.pt(x, y, 160); s.pt(x - 1, y - 1, 140); s.pt(x + 1, y - 1, 140)
    # tent
    s.poly([(156, 120), (186, 74), (216, 120)], f=110, l=230)
    s.poly([(178, 120), (186, 98), (194, 120)], f=0, l=200)
    s.line([(186, 74), (186, 70)], 220)
    s.line([(156, 120), (148, 124)], 160); s.line([(216, 120), (226, 124)], 160)
    s.rect(204, 112, 206, 114, f=230)
    # log
    s.rrect(68, 118, 116, 124, 2, f=150, l=210)
    s.circ(114, 121, 2, l=230)
    # campfire
    s.line([(124, 124), (146, 116)], 200, 2); s.line([(124, 116), (146, 124)], 200, 2)
    for i in range(10):
        a = math.pi * i / 9
        s.pt(int(135 + 14 * math.cos(a)), int(125 - 3 * math.sin(a)) + 1, 170)
    for (x, h) in ((129, 12), (135, 20), (141, 14)):
        s.tpoly([(x - 5, 120), (x + 5, 120), (x + 1, 120 - h), (x - 1, 120 - h)], 210, FC)
        s.tpoly([(x - 2, 120), (x + 2, 120), (x, 120 - h // 2)], 250, FY)
    for _ in range(16):
        s.tpt(s.r.randint(126, 146), s.r.randint(84, 100), s.r.randint(110, 240), FC)
    # glow
    for y in range(108, 144):
        for x in range(96, 176):
            dd = ((x - 135) ** 2 / 4 + (y - 122) ** 2) ** 0.5
            if dd < 20 and s.r.random() < 0.5 * (1 - dd / 20) and s.v.getpixel((x, y)) < 60:
                s.tpt(x, y, 90, FC)
    return s, dict(x=78, y=102, eyes="happy", acc=("beanie", "mug"),
                   label="clawd — embers", fg=(206, 214, 228), bg=(14, 16, 22))


def scene_rain():
    s = S(7)
    # skyline
    xb = 0
    while xb < GW:
        w = s.r.randint(10, 22); h = s.r.randint(30, 90)
        s.rect(xb, 118 - h, xb + w, 118, f=40, l=90)
        for wy in range(122 - h, 114, 5):
            for wx in range(xb + 3, xb + w - 2, 4):
                if s.r.random() < 0.3:
                    s.pt(wx, wy, 190); s.pt(wx + 1, wy, 190)
        if s.r.random() < 0.3:
            s.rect(xb + w // 2, 108 - h, xb + w // 2 + 1, 118 - h, f=150)
            s.tpt(xb + w // 2, 107 - h, 230, (230, 90, 80))
        xb += w + s.r.randint(1, 4)
    # street + puddles
    s.rect(0, 118, 256, 144, f=24)
    s.rect(0, 118, 256, 120, f=170)
    for (x, w) in ((20, 40), (150, 60), (220, 30)):
        s.ell(x, 132, x + w, 140, f=60, l=130)
    # lamp post
    s.rect(196, 54, 198, 120, f=200)
    s.rect(190, 50, 204, 54, f=220)
    s.fade(186, 58, 208, 118, 90, 30, 0.35, 0.1)
    s.tpoly([(192, 54), (202, 54), (200, 57), (194, 57)], 250, (250, 210, 120))
    # rain
    for _ in range(420):
        x, y = s.r.randrange(GW), s.r.randrange(GH)
        if s.v.getpixel((x, y)) == 0 or y < 118:
            s.pt(x, y, 150); s.pt(x - 1, y + 1, 100)
    # splashes
    for x in range(4, 256, 13):
        s.pt(x, 121, 200); s.pt(x - 1, 120, 140); s.pt(x + 1, 120, 140)
    return s, dict(x=96, y=104, eyes="open", acc=("umbrella",),
                   label="clawd — rainy commute", fg=(200, 206, 220), bg=(18, 20, 26))


def tcirc(s, cx, cy, r, v, col):
    b = [cx - r, cy - r, cx + r, cy + r]
    s.d.ellipse(b, fill=v); s.td.ellipse(b, fill=col); s.md.ellipse(b, fill=255)


def untint(s, x0, y0, x1, y1):
    s.md.rectangle([x0, y0, x1 - 1, y1 - 1], fill=0)


def scene_garden():
    s = S(8)
    YL, BRN, PK, RD, GN, VI = (236, 186, 50), (120, 80, 40), (230, 120, 160), (214, 60, 66), (86, 156, 84), (140, 110, 210)
    for (x, y, w) in ((20, 14, 36), (110, 8, 30), (170, 20, 24)):
        s.ell(x, y, x + w, y + 10, f=55)
        s.ell(x + w // 4, y - 5, x + w * 3 // 4, y + 6, f=55)
    # back fence
    s.rect(0, 84, 256, 85, f=120); s.rect(0, 96, 256, 97, f=120)
    for x in range(2, 192, 7):
        s.poly([(x, 104), (x, 80), (x + 2, 77), (x + 4, 80), (x + 4, 104)], f=30, l=130)
    # shed
    s.poly([(190, 56), (222, 34), (254, 56)], f=120, l=210)
    s.rect(194, 56, 250, 118, f=50, l=190)
    for x in range(198, 250, 5):
        s.rect(x, 57, x + 1, 117, f=90)
    s.rect(216, 78, 234, 118, f=110, l=210); s.pt(230, 98, 240)
    s.rect(200, 64, 212, 74, f=20, l=210); s.rect(205, 64, 207, 74, f=210); s.rect(200, 68, 212, 70, f=210)
    for x in (198, 238):
        s.rect(x, 108, x + 8, 118, f=150, l=220)
        tcirc(s, x + 4, 105, 3, 220, PK if x < 200 else VI)
    # ground
    s.rect(0, 118, 256, 144, f=24)
    s.dots(0, 118, 256, 144, 80, 0.12, 20)
    s.rect(0, 118, 256, 119, f=150)
    # raised beds
    for (x0, x1) in ((6, 72), (124, 152)):
        s.rect(x0, 108, x1, 120, f=140, l=220)
        s.rect(x0, 113, x1, 114, f=200)
    for i, x in enumerate(range(10, 70, 6)):
        h = 10 + (i * 7) % 8
        s.line([(x, 108), (x, 108 - h)], 170)
        s.pt(x - 1, 104 - h // 3, 180); s.pt(x + 1, 102 - h // 2, 180)
        col = (RD, YL, PK, VI)[i % 4]
        s.tpoly([(x - 2, 106 - h), (x + 2, 106 - h), (x + 2, 109 - h), (x - 2, 109 - h)], 230, col)
        s.tpt(x - 1, 105 - h, 230, col); s.tpt(x + 1, 105 - h, 230, col)
    for x in range(128, 150, 5):
        s.line([(x, 108), (x, 104)], 190)
        s.tpt(x - 1, 103, 220, GN); s.tpt(x + 1, 103, 220, GN)
    # sunflowers
    for (x, top) in ((162, 58), (174, 66), (184, 54)):
        s.line([(x, 118), (x, top)], 170, 1)
        s.poly([(x, top + 22), (x - 6, top + 18), (x, top + 20)], f=180)
        s.poly([(x, top + 32), (x + 6, top + 28), (x, top + 30)], f=180)
        tcirc(s, x, top, 5, 230, YL)
        tcirc(s, x, top, 2, 200, BRN)
    # butterflies
    for (x, y, c) in ((120, 64, PK), (60, 52, VI), (140, 40, YL)):
        for dx, dy in ((-2, -1), (-1, 0), (1, 0), (2, -1), (-2, 0), (2, 0), (-1, 1), (1, 1)):
            s.tpt(x + dx, y + dy, 230, c)
        s.pt(x, y, 200)
    return s, dict(x=96, y=102, eyes="happy", acc=("can",),
                   label="clawd — tending the garden", light=True)


def scene_bedroom():
    s = S(9)
    WY = (240, 200, 110)
    s.rect(0, 128, 256, 144, f=26)
    s.rect(0, 128, 256, 129, f=140)
    s.ell(40, 128, 170, 142, f=60, l=110)
    # window + curtains
    s.rect(160, 12, 222, 70, f=10, l=220, w=2)
    s.rect(190, 12, 192, 70, f=210); s.rect(160, 40, 222, 42, f=210)
    s.circ(176, 26, 6, f=230); s.circ(179, 24, 6, f=10)
    s.dots(162, 14, 220, 68, 200, 0.04)
    s.rect(150, 6, 232, 9, f=200)
    for x0 in (152, 222):
        s.rect(x0, 9, x0 + 10, 80, f=80, l=150)
        for x in range(x0 + 2, x0 + 10, 3):
            s.rect(x, 10, x + 1, 80, f=130)
    # picture over bed
    s.rect(62, 22, 108, 50, f=30, l=200)
    s.poly([(66, 46), (78, 32), (86, 40), (94, 30), (104, 46)], f=130)
    s.circ(98, 28, 2, f=220)
    # bed
    s.rrect(36, 66, 134, 108, 6, f=90, l=210, w=2)
    for x in range(46, 128, 10):
        s.rect(x, 72, x + 1, 104, f=150)
    s.rrect(48, 88, 78, 102, 3, f=200, l=240)
    s.rect(30, 104, 142, 122, f=150, l=220)
    s.rect(30, 108, 142, 109, f=200)
    for x in (32, 136):
        s.rect(x, 122, x + 4, 128, f=200)
    # nightstand
    s.rect(148, 98, 176, 128, f=100, l=210)
    s.rect(148, 110, 176, 111, f=200); s.rect(160, 103, 164, 105, f=240); s.rect(160, 116, 164, 118, f=240)
    s.rect(152, 88, 166, 98, f=40, l=200)
    for (x, y) in ((154, 92), (155, 92), (157, 91), (157, 93), (159, 92), (160, 92), (162, 91), (162, 93), (163, 92)):
        s.tpt(x, y, 240, (230, 90, 80))
    s.rect(168, 92, 174, 98, f=150, l=220)
    s.poly([(166, 82), (176, 82), (174, 74), (168, 74)], f=110, l=200)
    s.rect(170, 82, 172, 92, f=180)
    # slippers
    s.rrect(120, 136, 132, 140, 1, f=200); s.rrect(134, 137, 146, 141, 1, f=200)
    # shelf
    s.rect(196, 90, 250, 92, f=210)
    x = 200
    for w, h in ((3, 12), (4, 14), (3, 10), (5, 13), (3, 11)):
        s.rect(x, 90 - h, x + w, 90, f=150, l=220); x += w + 1
    s.rect(232, 82, 242, 90, f=120, l=220)
    s.tpt(237, 79, 200, WY)
    return s, dict(x=88, y=86, eyes="closed", acc=("nightcap", "blanket", "zzz"),
                   label="clawd — sleep mode", fg=(196, 204, 232), bg=(15, 17, 27))


def scene_pier():
    s = S(10)
    SUN, SUN2, RB = (240, 140, 80), (250, 196, 110), (220, 70, 70)
    for _ in range(90):
        s.pt(s.r.randrange(GW), s.r.randrange(0, 40), s.r.randint(60, 180))
    s.fade(0, 30, 256, 84, 20, 90, 0.02, 0.5)
    tcirc(s, 186, 84, 22, 220, SUN)
    tcirc(s, 186, 84, 14, 250, SUN2)
    s.rect(0, 84, 256, 144, f=0); untint(s, 0, 84, 256, 144)
    s.poly([(0, 84), (0, 74), (20, 70), (46, 76), (70, 72), (96, 84)], f=60, l=130)
    s.poly([(220, 84), (240, 76), (256, 78), (256, 84)], f=60, l=130)
    s.rect(0, 84, 256, 85, f=170)
    # water
    for y in range(87, 144, 3):
        x = s.r.randint(-6, 0)
        while x < GW:
            ln = s.r.randint(2, 7)
            s.rect(x, y, x + ln, y + 1, f=s.r.randint(50, 120))
            x += ln + s.r.randint(3, 10)
        half = max(0, int(22 - (y - 86) * 0.35))
        if half:
            for k in range(-half, half, 4):
                if s.r.random() < 0.7:
                    for j in range(s.r.randint(1, 3)):
                        s.tpt(186 + k + j, y, 200, SUN if abs(k) > half // 2 else SUN2)
    # pier
    s.rect(0, 100, 122, 104, f=200, l=230)
    for x in range(0, 122, 6):
        s.rect(x, 100, x + 1, 104, f=120)
    for x in range(4, 122, 16):
        s.rect(x, 104, x + 3, 140, f=150)
        s.rect(x - 2, 139, x + 5, 140, f=90)
    s.rect(0, 112, 122, 113, f=140)
    s.rect(4, 82, 6, 100, f=200); s.rect(36, 82, 38, 100, f=200); s.rect(4, 84, 38, 86, f=200)
    s.rect(46, 92, 56, 100, f=150, l=220); s.rect(46, 91, 56, 92, f=230)
    s.rect(20, 74, 22, 100, f=200); s.rect(17, 70, 25, 74, f=180, l=230)
    s.tpt(21, 72, 255, SUN2)
    # line + bobber
    tipx, tipy = 70 + 47, 84 - 14
    for i in range(1, 80):
        t = i / 80
        x = tipx + (150 - tipx) * t
        y = tipy + (97 - tipy) * t * t
        s.pt(int(x), int(y), 170)
    s.trect(149, 94, 152, 96, 250, RB); s.trect(149, 96, 152, 98, 250, (240, 240, 240))
    s.rect(146, 99, 155, 100, f=150)
    for (x, y) in ((60, 40), (68, 36), (140, 30)):
        s.pt(x, y, 200); s.pt(x + 1, y + 1, 200); s.pt(x + 2, y, 200); s.pt(x - 1, y - 1, 200); s.pt(x + 3, y - 1, 200)
    return s, dict(x=70, y=84, eyes="open", acc=("rod",),
                   label="clawd — waiting for ci", fg=(236, 216, 204), bg=(24, 18, 22))


def scene_studio():
    s = S(11)
    PAL = [(220, 60, 60), (240, 200, 60), (70, 120, 220), (80, 170, 90), (230, 120, 160)]
    s.rect(0, 128, 256, 144, f=30)
    s.rect(0, 128, 256, 129, f=170)
    for _ in range(26):
        x, y = s.r.randrange(0, 256), s.r.randrange(130, 144)
        c = s.r.choice(PAL)
        s.tpt(x, y, 200, c); s.tpt(x + 1, y, 160, c)
    # window
    s.rect(8, 6, 92, 62, f=10, l=220, w=2)
    for x in (36, 64):
        s.rect(x, 6, x + 2, 62, f=210)
    s.rect(8, 33, 92, 35, f=210)
    s.dots(10, 8, 90, 60, 90, 0.05)
    s.rect(4, 62, 96, 65, f=210)
    # shelf with jars
    s.rect(8, 82, 70, 84, f=210)
    for i, x in enumerate((12, 26, 40, 54)):
        s.rect(x, 72, x + 10, 82, f=80, l=220)
        for k in range(3):
            bx = x + 2 + k * 3
            s.rect(bx, 64 + k, bx + 1, 72, f=200)
            s.tpt(bx, 63 + k, 230, PAL[(i + k) % 5])
    # paint cans
    for i, x in enumerate((40, 58)):
        s.rect(x, 116, x + 14, 128, f=150, l=220)
        s.trect(x, 114, x + 14, 116, 220, PAL[i + 1])
        s.trect(x + 3, 116, x + 5, 121, 200, PAL[i + 1])
    # easel + canvas
    s.line([(150, 128), (171, 36)], 200, 2); s.line([(192, 128), (171, 36)], 200, 2)
    s.line([(171, 40), (176, 128)], 120, 1)
    s.rect(140, 92, 202, 95, f=220)
    s.rect(144, 48, 198, 92, f=40, l=235, w=2)
    s.trect(146, 50, 196, 70, 120, (110, 150, 220))
    tcirc(s, 184, 58, 5, 240, (245, 200, 80))
    s.tpoly([(146, 78), (160, 64), (172, 74), (184, 62), (196, 76), (196, 90), (146, 90)], 190, (80, 160, 96))
    s.tpoly([(146, 82), (196, 80), (196, 90), (146, 90)], 220, (60, 130, 80))
    s.trect(162, 72, 164, 82, 200, (130, 90, 60))
    tcirc(s, 163, 70, 3, 210, (60, 140, 70))
    # leaning canvases
    s.poly([(212, 128), (218, 84), (246, 84), (240, 128)], f=90, l=210)
    s.poly([(226, 128), (236, 96), (256, 96), (256, 128)], f=130, l=220)
    s.line([(222, 94), (240, 118)], 200); s.line([(240, 92), (220, 118)], 200)
    # stool
    s.rect(96, 120, 120, 122, f=200)
    return s, dict(x=106, y=112, eyes="open", acc=("beret", "palette", "brush"),
                   label="clawd — happy little commits")


def scene_snow():
    s = S(12)
    WY, OR = (246, 200, 110), (240, 140, 60)
    # house
    s.poly([(14, 70), (52, 42), (90, 70)], f=110, l=210)
    s.poly([(14, 70), (52, 42), (90, 70), (86, 70), (52, 46), (18, 70)], f=240)
    s.rect(70, 46, 78, 60, f=90, l=200); s.rect(69, 44, 79, 47, f=240)
    s.dots(66, 22, 84, 44, 110, 0.15)
    s.rect(20, 70, 84, 112, f=55, l=170)
    for (x0, y0) in ((28, 78), (60, 78)):
        s.trect(x0, y0, x0 + 14, y0 + 12, 210, WY)
        s.rect(x0 + 6, y0, x0 + 8, y0 + 12, f=60); untint(s, x0 + 6, y0, x0 + 8, y0 + 12)
        s.rect(x0, y0 + 5, x0 + 14, y0 + 7, f=60); untint(s, x0, y0 + 5, x0 + 14, y0 + 7)
    s.rect(46, 94, 58, 112, f=120, l=210)
    s.fade(26, 112, 80, 120, 120, 40, 0.5, 0.1)
    # pines
    def pine(x, base, h):
        for k in range(3):
            top = base - h + k * h // 4
            bot = top + h // 2
            ww = (h // 3) * (k + 2) // 3
            s.poly([(x - ww, bot), (x, top), (x + ww, bot)], f=80, l=180)
            s.poly([(x - ww // 2, top + h // 8), (x, top), (x + ww // 2, top + h // 8)], f=240)
        s.rect(x - 1, base - h // 4, x + 2, base, f=130)
    for (x, h) in ((218, 64), (236, 48), (252, 70), (96, 36)):
        pine(x, 112, h)
    s.circ(150, 20, 9, f=225)
    # ground snow
    s.rect(0, 110, 256, 144, f=110)
    s.dots(0, 110, 256, 144, 170, 0.2, 30)
    s.ell(-20, 104, 60, 118, f=140); s.ell(130, 106, 220, 118, f=140)
    for x in range(60, 160, 7):
        s.pt(x, 128 + (x % 3), 90); s.pt(x + 3, 130 + (x % 3), 90)
    # snowman
    for (cy, r) in ((112, 11), (95, 8), (82, 6)):
        s.circ(170, cy, r, f=245, l=255)
    for y in (92, 97, 102):
        s.pt(170, y, 40)
    s.pt(168, 80, 30); s.pt(172, 80, 30)
    s.tpoly([(170, 81), (180, 83), (170, 85)], 250, OR)
    s.line([(162, 94), (152, 86)], 154); s.line([(156, 89), (154, 84)], 154)
    s.line([(178, 94), (188, 86)], 154)
    s.rect(164, 72, 176, 74, f=60); s.rect(166, 64, 174, 72, f=60, l=144)
    # snowfall
    for _ in range(320):
        x, y = s.r.randrange(GW), s.r.randrange(0, 110)
        if s.v.getpixel((x, y)) < 40:
            s.pt(x, y, s.r.randint(120, 240))
    return s, dict(x=112, y=102, eyes="happy", acc=("beanie", "scarf"),
                   label="clawd — let it snow", fg=(214, 224, 244), bg=(15, 19, 31))


def scene_moon():
    s = S(13)
    for _ in range(300):
        s.pt(s.r.randrange(GW), s.r.randrange(0, 100), s.r.randint(60, 230))
    for (x, y) in ((40, 20), (120, 12), (90, 50), (240, 70)):
        s.pt(x, y, 255)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            s.pt(x + dx, y + dy, 140)
    # earth
    tcirc(s, 196, 34, 16, 200, (70, 130, 220))
    for (pts) in ([(186, 24), (194, 22), (198, 30), (190, 36), (184, 32)],
                  [(200, 38), (208, 34), (210, 42), (202, 46)],
                  [(198, 20), (204, 20), (202, 24)]):
        s.tpoly(pts, 220, (90, 170, 100))
    s.d.chord([180, 18, 212, 50], 300, 120, fill=60)
    s.dots(194, 20, 210, 50, 120, 0.0)
    # surface
    pts = [(0, 104)]
    for x in range(0, 264, 8):
        pts.append((x, 100 + int(4 * ((x * 37) % 11) / 11)))
    pts += [(256, 144), (0, 144)]
    s.poly(pts, f=0)
    for y in range(96, 144):
        for x in range(GW):
            if s.v.getpixel((x, y)) == 0 and y >= 100 + int(4 * ((x // 8 * 8 * 37) % 11) / 11):
                s.pt(x, y, s.r.randint(80, 140))
    for (cx, cy, rx, ry) in ((30, 124, 14, 4), (200, 132, 22, 5), (150, 112, 8, 2), (236, 110, 9, 2), (80, 136, 10, 3)):
        s.ell(cx - rx, cy - ry, cx + rx, cy + ry, f=40, l=210)
        s.ell(cx - rx + 2, cy - ry - 1, cx + rx - 2, cy, l=240)
    # lander
    G = (220, 176, 80)
    s.line([(22, 112), (30, 96)], 200); s.line([(66, 112), (58, 96)], 200)
    s.rect(18, 112, 26, 113, f=220); s.rect(62, 112, 70, 113, f=220)
    s.trect(28, 88, 60, 100, 200, G)
    s.rect(32, 70, 56, 88, f=150, l=230)
    s.rect(38, 76, 44, 82, f=40, l=220)
    s.line([(44, 70), (44, 62)], 200); s.circ(44, 60, 2, l=230)
    for y in range(101, 112, 3):
        s.rect(34, y, 40, y + 1, f=180)
    # flag
    s.rect(150, 66, 151, 108, f=230)
    s.trect(151, 66, 170, 78, 230, (217, 119, 87))
    # footprints
    for i, x in enumerate(range(76, 112, 5)):
        s.pt(x, 114 + (i % 2) * 2, 230); s.pt(x + 1, 114 + (i % 2) * 2, 230)
    return s, dict(x=110, y=92, eyes="happy", acc=("helmet",),
                   label="clawd — deployed to prod", fg=(222, 222, 228), bg=(9, 9, 13))


def scene_gaming():
    s = S(14)
    SKY, GR, CO, HE, BL = (80, 130, 230), (80, 170, 90), (246, 200, 70), (230, 90, 100), (190, 120, 70)
    s.rect(0, 128, 256, 144, f=28)
    s.rect(0, 128, 256, 129, f=150)
    # posters + shelf
    s.rect(8, 12, 44, 58, f=40, l=200)
    tcirc(s, 21, 28, 5, 230, HE); tcirc(s, 31, 28, 5, 230, HE)
    s.tpoly([(16, 29), (36, 29), (26, 42)], 230, HE)
    s.rect(52, 18, 92, 44, f=40, l=200)
    s.rrect(60, 26, 84, 36, 3, f=170); s.rect(64, 29, 66, 33, f=40); s.rect(63, 30, 67, 32, f=40)
    s.pt(78, 30, 40); s.pt(80, 32, 40)
    s.rect(8, 70, 48, 72, f=210)
    for x in range(10, 46, 4):
        s.rect(x, 60, x + 3, 70, f=150, l=220)
    # tv
    s.rect(116, 30, 232, 98, f=20, l=230, w=2)
    sx0, sy0, sx1, sy1 = 120, 34, 228, 94
    s.trect(sx0, sy0, sx1, sy1, 70, SKY)
    for (x, y, w) in ((130, 44, 22), (190, 42, 16)):
        s.trect(x, y, x + w, y + 5, 150, (230, 236, 250)); s.trect(x + 4, y - 3, x + w - 4, y, 150, (230, 236, 250))
    s.trect(sx0, 84, sx1, 94, 200, GR); s.trect(sx0, 88, sx1, 94, 200, BL)
    for x0 in (150, 200):
        s.trect(x0, 66, x0 + 18, 70, 220, BL)
        for k in range(3):
            s.trect(x0 + 2 + k * 6, 60, x0 + 4 + k * 6, 63, 240, CO)
    s.trect(172, 76, 180, 84, 230, HE)
    s.tpt(174, 78, 40, (20, 20, 20)); s.tpt(178, 78, 40, (20, 20, 20))
    s.trect(208, 74, 214, 84, 200, GR); s.trect(206, 72, 216, 76, 220, GR)
    # stand
    s.rect(110, 104, 238, 128, f=100, l=210)
    s.rect(110, 100, 238, 104, f=210)
    s.rect(120, 108, 150, 116, f=60, l=220); s.tpt(146, 112, 240, (90, 230, 120))
    s.rect(196, 108, 230, 124, f=60, l=200)
    for x in range(200, 228, 4):
        s.rect(x, 110, x + 3, 122, f=160)
    # tv glow
    for y in range(100, 144):
        for x in range(100, 250):
            dd = ((x - 174) ** 2 / 9 + (y - 130) ** 2) ** 0.5
            if dd < 14 and s.v.getpixel((x, y)) < 40 and s.r.random() < 0.35:
                s.tpt(x, y, 80, SKY)
    # beanbag
    s.ell(46, 104, 112, 136, f=110, l=200)
    s.line([(60, 112), (70, 120)], 160); s.line([(96, 110), (90, 120)], 160)
    # snacks
    s.poly([(20, 124), (36, 124), (33, 130), (23, 130)], f=180, l=230)
    for x in range(22, 35, 3):
        s.tpt(x, 123, 220, CO)
    return s, dict(x=64, y=96, eyes="open", acc=("controller",),
                   label="clawd — one more level", fg=(214, 206, 236), bg=(19, 16, 27))


SCENES = dict(vinyl=scene_vinyl, kitchen=scene_kitchen, fireplace=scene_fireplace,
              strawberry=scene_strawberry, desk=scene_desk, camp=scene_camp, rain=scene_rain,
              garden=scene_garden, bedroom=scene_bedroom, pier=scene_pier, studio=scene_studio,
              snow=scene_snow, moon=scene_moon, gaming=scene_gaming)


# ───────────────────────── render ─────────────────────────

def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def render(name):
    s, c = SCENES[name]()
    light = c.get("light", False)
    bg = c.get("bg", (240, 238, 233) if light else (22, 22, 22))
    fg = c.get("fg", (64, 62, 60) if light else (226, 226, 226))
    W, H = GW * CELL, GH * CELL
    im = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(im)
    rng = random.Random(zlib.crc32(name.encode()) & 0xFFFF)
    vp, tp, mp = s.v.load(), s.t.load(), s.m.load()
    rad = CELL * 0.23
    for y in range(GH):
        for x in range(GW):
            v = vp[x, y] / 255
            if v == 0:
                if rng.random() > 0.05:
                    continue
                b = 0.05 + 0.08 * rng.random()
            else:
                b = min(1.0, v * (0.84 + 0.2 * rng.random()))
            col = lerp(bg, tp[x, y], b) if mp[x, y] else lerp(bg, fg, b)
            cx, cy = (x + 0.5) * CELL, (y + 0.5) * CELL
            d.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill=col)
    # clawd
    spr = clawd(c.get("eyes", "open"), c.get("acc", ()))
    spr = spr.resize((SW * CELL, SH * CELL), Image.NEAREST)
    im.paste(spr, ((c["x"] - OX) * CELL, (c["y"] - OY) * CELL), spr)
    # label
    if c.get("label"):
        f, glyph = load_font(int(CELL * 1.9))
        txt = "\U000f075a  " + c["label"] if glyph else c["label"].replace("\u2014", "-")
        tw = d.textlength(txt, font=f)
        tx, ty = W - tw - CELL * 8, CELL * 6
        bb = d.textbbox((tx, ty), txt, font=f)
        pad = CELL * 1.2
        d.rounded_rectangle([bb[0] - pad, bb[1] - pad, bb[2] + pad, bb[3] + pad], CELL * 0.6,
                            fill=bg, outline=lerp(bg, fg, 0.18), width=max(2, CELL // 10))
        d.text((tx, ty), txt, font=f, fill=lerp(bg, fg, 0.85))
    return im


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "wallpapers")
    names = sys.argv[2:] or list(SCENES)
    os.makedirs(out, exist_ok=True)
    for i, n in enumerate(SCENES):
        if n not in names:
            continue
        master = render(n)
        for (w, h) in SIZES:
            path = os.path.join(out, f"{i + 1:02d}-{n}-{w}x{h}.png")
            master.resize((w, h), Image.LANCZOS).save(path, optimize=True)
            print(path)


if __name__ == "__main__":
    main()
