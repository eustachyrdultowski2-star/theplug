#!/usr/bin/env python3
"""Import the 170-brand spreadsheet into The Plug.

- every brand is kept (searchable), classified clothing / footwear / bags / art-decor
- for each shop we try Shopify's public /products.json to pull REAL products
- products are classified too, so non-apparel (prints, posters, homeware) lands
  in the art-decor bucket instead of polluting the clothing feed
"""
import json, os, re, sys, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

sys.stdout.reconfigure(encoding="utf-8")
from read_xlsx import read

HERE = os.path.dirname(os.path.abspath(__file__))
XLSX = sys.argv[1] if len(sys.argv) > 1 else \
    r"C:/Users/eusta/Downloads/underground_streetwear_brand_database_v1.xlsx"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

# ---------- classification ----------
ART_WORDS   = ["print", "poster", "artwork", "canvas", "sticker", "zine", "book",
               "magazine", "rug", "candle", "mug", "cushion", "vase", "frame",
               "incense", "ashtray", "keychain", "pin badge", "towel", "blanket",
               "lamp", "chair", "figure", "toy", "wallpaper", "sculpture"]
FOOT_WORDS  = ["shoe", "sneaker", "boot", "trainer", "loafer", "sandal", "clog", "mule"]
BAG_WORDS   = ["bag", "tote", "backpack", "pouch", "wallet", "sling", "duffel", "case"]
CLOTH_WORDS = ["tee", "shirt", "hoodie", "jacket", "pant", "trouser", "jean", "denim",
               "short", "knit", "sweater", "coat", "vest", "cap", "hat", "beanie",
               "sock", "belt", "scarf", "glove", "jumper", "cardigan", "top", "skirt",
               "dress", "polo", "crewneck", "zip", "parka", "gilet", "balaclava"]

def classify(text: str, fallback="clothing") -> str:
    s = (text or "").lower()
    # whole words only — "rug" must not match "rugby", "print" not "printed denim"
    def hit(words):
        return any(re.search(r"\b" + re.escape(w) + r"s?\b", s) for w in words)
    # a garment noun beats an art noun ("printed tee" is a tee, not a print)
    if hit(FOOT_WORDS):  return "footwear"
    if hit(BAG_WORDS):   return "bags"
    if hit(CLOTH_WORDS): return "clothing"
    if hit(ART_WORDS):   return "art-decor"
    return fallback

def brand_kind(niche: str) -> str:
    s = (niche or "").lower()
    if "footwear" in s or "sneaker" in s or "shoe" in s: return "footwear"
    if "bag" in s or "eyewear" in s:                     return "bags"
    if s.startswith("art ") or "fashion media" in s:     return "art-decor"
    return "clothing"

STYLE_MAP = [
    (["minimal", "contemporary", "tailor", "conceptual", "scandinav"], "minimalist"),
    (["technical", "tech", "outdoor", "running", "trail", "utility", "military", "tactical"], "gorpcore"),
    (["vintage", "archive", "americana", "heritage", "workwear", "upcycl", "craft", "denim"], "vintage"),
    (["avant", "deconstruct", "experimental", "artisanal", "leather", "luxury"], "classy"),
]
def style_of(niche: str) -> str:
    s = (niche or "").lower()
    for words, style in STYLE_MAP:
        if any(w in s for w in words): return style
    return "streetwear"

CURRENCY = {"USD": "$", "GBP": "£", "EUR": "€", "PLN": " zł", "AUD": "A$",
            "CAD": "C$", "SEK": " kr", "DKK": " kr", "JPY": "¥", "KRW": "₩"}

# ---------- shopify ----------
def shopify(domain, limit=12):
    url = f"https://{domain.rstrip('/')}/products.json?limit={limit}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        if "json" not in (r.headers.get("Content-Type") or ""):
            raise ValueError("not json")
        data = json.load(r)
    out = []
    for p in data.get("products", []):
        imgs, vars_ = p.get("images") or [], p.get("variants") or []
        if not imgs: continue
        out.append({
            "title": re.sub(r"\s+", " ", p.get("title") or "").strip(),
            "type": p.get("product_type") or "",
            "tags": " ".join(p.get("tags") or []) if isinstance(p.get("tags"), list) else "",
            "price": (vars_[0].get("price") if vars_ else None),
            "image": imgs[0].get("src"),
            "url": f"https://{domain.rstrip('/')}/products/{p.get('handle')}",
        })
    return out

def host_of(url):
    if not url: return None
    if not url.startswith("http"): url = "https://" + url
    return urllib.parse.urlparse(url).netloc.replace("www.", "") or None

def work(row):
    name  = row[1].strip()
    niche = row[2].strip() if len(row) > 2 else ""
    country = row[3].strip() if len(row) > 3 else ""
    site  = row[4].strip() if len(row) > 4 else ""
    ig    = row[5].strip() if len(row) > 5 else ""
    handle = None
    m = re.search(r"instagram\.com/([A-Za-z0-9._]+)", ig or "")
    # v3 fills this column with search urls (…/explore/search/keyword/?q=…),
    # which is not a profile — don't turn every brand into "@explore"
    if m and m.group(1) not in ("explore", "p", "reel", "reels", "accounts", "search"):
        handle = "@" + m.group(1)
    brand = {"brand": name, "niche": niche, "country": country,
             "site": site or None, "handle": handle,
             "kind": brand_kind(niche), "style": style_of(niche), "products": []}
    host = host_of(site)
    if host:
        try:
            for p in shopify(host):
                kind = classify(f"{p['title']} {p['type']} {p['tags']}", fallback=brand["kind"])
                brand["products"].append({**p, "kind": kind})
        except Exception:
            pass
    return brand

if __name__ == "__main__":
    rows = read(XLSX)["Brands"]
    data = [r for r in rows[1:] if len(r) > 1 and r[1].strip()]
    print(f"importing {len(data)} brands…")
    with ThreadPoolExecutor(max_workers=16) as ex:
        brands = list(ex.map(work, data))

    withp = [b for b in brands if b["products"]]
    prods = sum(len(b["products"]) for b in brands)
    kinds = {}
    for b in brands: kinds[b["kind"]] = kinds.get(b["kind"], 0) + 1
    pk = {}
    for b in brands:
        for p in b["products"]: pk[p["kind"]] = pk.get(p["kind"], 0) + 1

    json.dump(brands, open(os.path.join(HERE, "brands_full.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"\nbrands: {len(brands)}   with live catalog: {len(withp)}   products: {prods}")
    print("brand kinds :", kinds)
    print("product kinds:", pk)
    print("-> brands_full.json")
