#!/usr/bin/env python3
"""Brand plus garment -> the actual product, with its photo and shop link.

Knowing that the jeans are Elysian only half-answers the question; people
still have to go and find them. We already hold 2100+ real products scraped
from brand shops, so answer from those first, and fall back to a live read of
the shop's public Shopify catalog for brands we never scraped.
"""
import json, os, re, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, ".cache")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
SHOP_TTL = 60 * 60 * 24        # a shop's catalog is worth re-reading once a day

# the detector's garment keys, said the way a shop says them
GARMENT_WORDS = {
    "jeans":   ["jean", "denim", "pant", "trouser", "cargo", "jogger", "sweatpant",
                "short", "chino", "slack", "bottom"],
    "shoes":   ["shoe", "sneaker", "boot", "trainer", "loafer", "runner", "sandal", "clog"],
    "belt":    ["belt", "buckle"],
    "shirt":   ["shirt", "tee", "t-shirt", "polo", "jersey", "top", "tank", "flannel"],
    "jacket":  ["jacket", "coat", "hoodie", "puffer", "parka", "bomber", "vest",
                "blazer", "trench", "overshirt", "anorak", "windbreaker"],
    "knit":    ["knit", "sweater", "jumper", "cardigan", "fleece", "pullover", "crewneck"],
    "scarf":   ["scarf", "scarves", "shawl", "snood"],
    "hat":     ["cap", "hat", "beanie", "balaclava", "bucket"],
    "bag":     ["bag", "tote", "backpack", "purse", "satchel", "pouch", "duffel"],
    "glasses": ["glasses", "sunglasses", "shades", "eyewear", "frame"],
    "jewelry": ["ring", "necklace", "chain", "bracelet", "earring", "pendant"],
    "watch":   ["watch"],
}

CCY_BY_COUNTRY = {"USA": "$", "UK": "£", "Australia": "A$", "Canada": "C$",
                  "Japan": "¥", "Korea": "₩", "South Korea": "₩", "Poland": "zł"}

_brands = None


def brands():
    global _brands
    if _brands is None:
        with open(os.path.join(HERE, "brands_full.json"), encoding="utf-8") as f:
            _brands = json.load(f)
    return _brands


def key(name):
    return re.sub(r"[^a-z0-9]", "", (name or "").lower())


def find_brand(name):
    """The brand row for a name written any which way, or None."""
    k = key(name)
    if len(k) < 3:
        return None
    rows = brands()
    for b in rows:                                    # exact first
        if key(b.get("brand")) == k or key(b.get("handle")) == k:
            return b
    for b in rows:                                    # then a clear containment
        bk = key(b.get("brand"))
        if len(bk) >= 4 and (bk in k or k in bk):
            return b
    return None


def score(product, garment):
    """How well one product answers "the <garment> in this video"."""
    words = GARMENT_WORDS.get(garment) or []
    if not words:
        return 0
    title = (product.get("title") or "").lower()
    ptype = (product.get("type") or "").lower()
    s = 0
    for w in words:
        if w in ptype:
            s += 6                                    # the shop's own label wins
        if w in title:
            s += 3
    if s and product.get("image"):
        s += 2                                        # a card with no photo is no answer
    # a hoodie is not a hoodie-print tee: let a rival category veto the match
    for other, ws in GARMENT_WORDS.items():
        if other == garment:
            continue
        for w in ws:
            if w in ptype:
                s -= 5
                break
    return s


def shopify(domain, limit=250):
    """The shop's public catalog, cached on disk for a day."""
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, "shop_" + key(domain) + ".json")
    if os.path.exists(path) and time.time() - os.path.getmtime(path) < SHOP_TTL:
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    url = "https://" + domain.replace("https://", "").replace("http://", "").strip("/")
    req = urllib.request.Request(url + "/products.json?limit=" + str(limit),
                                 headers={"User-Agent": UA})
    out = []
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.load(r)
        for p in data.get("products", []):
            imgs = p.get("images") or []
            variants = p.get("variants") or []
            if not imgs:
                continue
            out.append({
                "title": p.get("title"),
                "type": p.get("product_type") or "",
                "price": (variants[0].get("price") if variants else None),
                "image": imgs[0].get("src"),
                "url": url + "/products/" + str(p.get("handle")),
                "kind": "clothing",
            })
    except Exception:
        out = []                                      # not Shopify, or simply not answering
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(out, f)                         # cache the empty answer too
    except Exception:
        pass
    return out


def find(brand_name, garment):
    """The single best product, or None when we would only be guessing."""
    row = find_brand(brand_name)
    if not row:
        return None
    products = row.get("products") or []
    if not products and row.get("site"):
        products = shopify(row["site"])
    if not products:
        return None

    best, best_score = None, 0
    for p in products:
        s = score(p, garment)
        if s > best_score:
            best, best_score = p, s
    if not best or best_score < 5:                    # a weak match is worse than none
        return None

    ccy = CCY_BY_COUNTRY.get(row.get("country"), "$")
    price = best.get("price")
    return {
        "brand": row.get("brand"),
        "name": best.get("title"),
        "price": (ccy + str(price)) if price else None,
        "image": best.get("image"),
        "url": best.get("url"),
        "site": row.get("site"),
        "shop": (row.get("site") or "").replace("https://", "").replace("http://", "").strip("/"),
    }


if __name__ == "__main__":
    import sys
    b = sys.argv[1] if len(sys.argv) > 1 else "Mutimer"
    g = sys.argv[2] if len(sys.argv) > 2 else "shirt"
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(find(b, g), ensure_ascii=False, indent=1))
