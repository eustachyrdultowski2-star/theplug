#!/usr/bin/env python3
"""Download real product images from shop_data.json and emit a JS ITEMS array."""
import json, os, re, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
PHOTOS = os.path.join(HERE, "assets", "photos")
os.makedirs(PHOTOS, exist_ok=True)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"

SLUG = {"Scuffers": "scuf", "Unfounded Studios": "unf",
        "Society de Nobodies": "sdn", "Corteiz": "crtz"}
META = {  # handle, indie?, style, currency symbol
    "Scuffers":            ("@scuffers", True,  "streetwear", "€"),
    "Unfounded Studios":   ("@unfoundedstudios", True, "streetwear", "£"),
    "Society de Nobodies": ("@society.de.nobodies", True, "minimalist", "€"),
    "Corteiz":             ("@corteiz", False, "streetwear", "£"),
}

def category(title, ptype):
    s = (title + " " + ptype).lower()
    if any(k in s for k in ["hoodie", "knit", "sweat", "jumper", "cardigan"]): return "Knitwear"
    if any(k in s for k in ["jacket", "coat", "overshirt", "puffer", "vest"]):  return "Jackets"
    if any(k in s for k in ["jean", "pant", "trouser", "short", "cargo", "denim"]): return "Denim"
    if any(k in s for k in ["tee", "shirt", "polo", "top", "jersey"]):          return "Tees"
    if any(k in s for k in ["cap", "hat", "beanie", "belt", "sock", "scarf"]):  return "Accessories"
    if any(k in s for k in ["bag", "tote", "pouch"]):                            return "Bags"
    if any(k in s for k in ["shoe", "sneaker", "trainer", "boot"]):              return "Sneakers"
    return "Tees"

def clean(t):
    t = re.sub(r"\s+", " ", t).strip()
    return t.title() if t.isupper() else t

data = json.load(open(os.path.join(HERE, "shop_data.json"), encoding="utf-8"))
items, idx = [], 100
for brand, products in data.items():
    if brand not in META:
        continue
    handle, indie, style, cur = META[brand]
    kept = 0
    for p in products:
        if kept >= 5 or not p.get("image"):
            continue
        idx += 1
        fname = f"{SLUG[brand]}{idx}.jpg"
        try:
            req = urllib.request.Request(p["image"], headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                blob = r.read()
            if len(blob) < 4000:      # skip broken/tiny images
                continue
            open(os.path.join(PHOTOS, fname), "wb").write(blob)
        except Exception as e:
            print("skip", brand, p["title"][:30], type(e).__name__)
            continue
        price = p.get("price")
        items.append({
            "brand": brand, "name": clean(p["title"])[:38],
            "cat": category(p["title"], p.get("type", "")), "style": style,
            "price": f"{cur}{int(float(price))}" if price else None,
            "indie": indie, "src": handle, "photo": f"assets/photos/{fname}",
            "link": p["url"],
        })
        kept += 1
        print(f"OK {brand[:18]:18} {clean(p['title'])[:34]:34} -> {fname}")

lines = []
for i, it in enumerate(items, start=1):
    price = f'"{it["price"]}"' if it["price"] else "null"
    lines.append(
        f'  {{id:{i}, brand:"{it["brand"]}", name:"{it["name"]}", cat:"{it["cat"]}", '
        f'style:"{it["style"]}", price:{price}, indie:{str(it["indie"]).lower()}, '
        f'src:"{it["src"]}", likes:{200 + i * 37 % 2600}, photo:"{it["photo"]}", '
        f'link:"{it["link"]}", seed:"s{i}"}},'
    )
open(os.path.join(HERE, "items_generated.js"), "w", encoding="utf-8").write("\n".join(lines))
print(f"\n{len(items)} products -> items_generated.js")
