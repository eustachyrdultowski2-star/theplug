#!/usr/bin/env python3
"""Product shots straight off a shop CDN are often 10-18 MB. Nobody needs that
on a phone. Resize to a sane width and re-encode."""
import os, sys
from PIL import Image
sys.stdout.reconfigure(encoding="utf-8")

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "photos")
MAX_W, QUALITY = 1000, 82

before = after = 0
for name in sorted(os.listdir(SRC)):
    if not name.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
        continue
    path = os.path.join(SRC, name)
    b = os.path.getsize(path); before += b
    try:
        im = Image.open(path)
        im = im.convert("RGB")
        if im.width > MAX_W:
            im = im.resize((MAX_W, round(im.height * MAX_W / im.width)), Image.LANCZOS)
        out = os.path.splitext(path)[0] + ".jpg"
        im.save(out, "JPEG", quality=QUALITY, optimize=True, progressive=True)
        if out != path:
            os.remove(path)
        a = os.path.getsize(out); after += a
        if b > 1_000_000:
            print(f"  {name:16} {b//1024//1024:>3} MB -> {a//1024:>4} KB")
    except Exception as e:
        after += b
        print(f"  skip {name}: {e}")

print(f"\ntotal: {before//1024//1024} MB -> {after//1024//1024} MB "
      f"({100 - after*100//max(before,1)}% smaller)")
