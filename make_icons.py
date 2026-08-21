#!/usr/bin/env python3
"""Draw the app icon as a real PNG, with no image library —
a rounded square in the brand blue plus a white plug mark."""
import struct, zlib, os, math, sys
sys.stdout.reconfigure(encoding="utf-8")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons")
os.makedirs(OUT, exist_ok=True)

BG   = (10, 107, 255)      # --accent sapphire
BG2  = (49, 217, 255)      # --accent-2, used for a soft diagonal
FG   = (255, 255, 255)

def rounded(x, y, w, h, r):
    """inside a rounded rectangle?"""
    if x < r and y < r:            return (x-r)**2 + (y-r)**2 <= r*r
    if x > w-r-1 and y < r:        return (x-(w-r-1))**2 + (y-r)**2 <= r*r
    if x < r and y > h-r-1:        return (x-r)**2 + (y-(h-r-1))**2 <= r*r
    if x > w-r-1 and y > h-r-1:    return (x-(w-r-1))**2 + (y-(h-r-1))**2 <= r*r
    return True

def plug(px, py, s):
    """A simple plug: body + two prongs + cable. Coordinates are 0..1."""
    x, y = px/s, py/s
    # body
    if 0.30 <= x <= 0.70 and 0.42 <= y <= 0.66: return True
    # rounded bottom of the body
    if 0.30 <= x <= 0.70 and 0.66 < y <= 0.72:
        cx = 0.5; return abs(x-cx) <= 0.20 - (y-0.66)*1.6
    # prongs
    if 0.28 <= y < 0.42 and (0.375 <= x <= 0.435 or 0.565 <= x <= 0.625): return True
    # cable
    if 0.72 < y <= 0.78 and 0.465 <= x <= 0.535: return True
    return False

def png(size, path, maskable=False):
    pad = int(size*0.14) if maskable else 0     # safe zone for Android masks
    inner = size - pad*2
    radius = int(inner*0.22)
    rows = bytearray()
    for y in range(size):
        rows.append(0)                          # filter byte
        for x in range(size):
            ix, iy = x-pad, y-pad
            if 0 <= ix < inner and 0 <= iy < inner and rounded(ix, iy, inner, inner, radius):
                t = (ix+iy)/(inner*2)           # diagonal blend
                r = int(BG[0]+(BG2[0]-BG[0])*t*0.55)
                g = int(BG[1]+(BG2[1]-BG[1])*t*0.55)
                b = int(BG[2]+(BG2[2]-BG[2])*t*0.55)
                if plug(ix, iy, inner): r, g, b = FG
                rows += bytes((r, g, b, 255))
            else:
                rows += bytes((0, 0, 0, 0))
    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag+data) & 0xffffffff)
    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    blob = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(bytes(rows), 9)) + chunk(b"IEND", b""))
    open(path, "wb").write(blob)
    return len(blob)

for s in (180, 192, 512):
    n = png(s, os.path.join(OUT, f"icon-{s}.png"))
    print(f"icon-{s}.png       {n//1024} KB")
n = png(512, os.path.join(OUT, "icon-maskable-512.png"), maskable=True)
print(f"icon-maskable-512.png {n//1024} KB")
