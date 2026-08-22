#!/usr/bin/env python3
"""Turn brands_full.json into a JS catalog the app can search."""
import json, os, re, sys, random
sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
brands = json.load(open(os.path.join(HERE, "brands_full.json"), encoding="utf-8"))

CUR = {"usd": "$", "gbp": "£", "eur": "€", "pln": "zł", "aud": "A$", "cad": "C$"}
CCY_BY_COUNTRY = {"USA": "$", "UK": "£", "Australia": "A$", "Canada": "C$",
                  "Japan": "¥", "Korea": "₩", "South Korea": "₩", "Poland": "zł"}

from import_brands import classify

# The shop's own product_type is far more reliable than guessing from a name,
# so it wins when present. Otherwise we read the title, taking the LAST match:
# in English the head noun comes last ("Gator shoes hooded sweatshirt" is a
# sweatshirt, not a shoe).
CAT_WORDS = [
    ("Sneakers", r"sneakers?|shoes?|boots?|trainers?|loafers?|sandals?|clogs?|mules?|"
                 r"runners?|slides?|footwear|jordan|dunk|vans|superstar|samba|gazelle|"
                 r"air\s?force|air\s?max|new\s?balance|asics|salomon"),
    ("Bags",     r"bags?|totes?|backpacks?|rucksack|pouch|wallets?|slings?|duffels?|"
                 r"cases?|purse|satchel|holdall|crossbody"),
    ("Accessories", r"caps?|hats?|beanies?|belts?|socks?|scarf|scarves|gloves?|balaclava|"
                 r"rings?|necklaces?|chains?|bracelets?|earrings?|jewell?ery|keychains?|"
                 r"sunglasses|eyewear|glasses|ties?|headband|bandana|lanyard|watch|"
                 r"accessor|wristband|gaiter|mittens?"),
    ("Jackets",  r"jackets?|coats?|parkas?|vests?|gilets?|overshirts?|blazers?|puffers?|"
                 r"anoraks?|bombers?|windbreaker|shell|trench|outerwear|raincoat"),
    ("Knitwear", r"hoodies?|hoody|knits?|knitwear|sweaters?|jumpers?|cardigans?|crewnecks?|"
                 r"fleece|sweatshirts?|pullovers?|zip[\s-]?up|turtleneck|mohair"),
    ("Denim",    r"jeans?|denim|pants?|trousers?|shorts?|cargos?|joggers?|sweatpants?|"
                 r"slacks?|chinos?|bottoms?|tracksuits?|leggings|jorts|skirt"),
    ("Tees",     r"tees?|t[\s-]?shirts?|shirts?|polos?|jerseys?|tanks?|tops?|"
                 r"longsleeves?|long\s?sleeve|beaters?|blouse|singlet"),
    ("Art",      r"prints?|posters?|artwork|canvas|stickers?|zines?|books?|magazines?|"
                 r"rugs?|candles?|mugs?|cushions?|vases?|incense|ashtrays?|towels?|"
                 r"blankets?|figures?|toys?|puzzles?|ceramics?"),
]
CAT_RE = [(c, __import__("re").compile(rx, __import__("re").I)) for c, rx in CAT_WORDS]

TYPE_MAP = {
    "shoes": "Sneakers", "footwear": "Sneakers", "sneakers": "Sneakers", "boots": "Sneakers",
    "bags": "Bags", "bag": "Bags", "accessories": "Accessories", "hats": "Accessories",
    "headwear": "Accessories", "jewelry": "Accessories", "jewellery": "Accessories",
    "eyewear": "Accessories", "outerwear": "Jackets", "jackets": "Jackets", "coats": "Jackets",
    "knitwear": "Knitwear", "hoodies": "Knitwear", "sweatshirts": "Knitwear",
    "sweaters": "Knitwear", "pants": "Denim", "trousers": "Denim", "shorts": "Denim",
    "bottoms": "Denim", "denim": "Denim", "jeans": "Denim",
    "t-shirts": "Tees", "t-shirt": "Tees", "tshirts": "Tees", "tees": "Tees",
    "shirts": "Tees", "tops": "Tees", "polos": "Tees",
    "home": "Art", "prints": "Art", "objects": "Art",
}

def cat_from_text(text):
    """Last keyword wins — the head noun sits at the end."""
    best, pos = None, -1
    for cat, rx in CAT_RE:
        for m in rx.finditer(text or ""):
            if m.start() > pos:
                best, pos = cat, m.start()
    return best

def cat_of(p, brand_kind="clothing"):
    ptype = (p.get("type") or "").strip().lower()
    if ptype in TYPE_MAP:
        cat = TYPE_MAP[ptype]
    else:
        cat = cat_from_text(f"{ptype} {p.get('title','')}") or cat_from_text(p.get("tags", ""))
    if not cat:
        # nothing said what it is — do not dump it in Tees, say so honestly
        cat = "Other"
    p["kind"] = {"Sneakers": "footwear", "Bags": "bags",
                 "Art": "art-decor"}.get(cat, "clothing")
    return cat

# The generic HTML scraper sometimes grabs banners and template debris
# ("?goods status id=2", "ALL ITEMS SALE 30%OFF"). Better to show nothing
# for a brand than to show junk.
JUNK_PATTERNS = [
    r"^\?", r"status\s*id", r"goods\s*status", r"=\d", r"undefined", r"null",
    r"^\W*$", r"^(shop|store|home|index|menu|cart|search|login|account|all)",
    r"(sale|off|discount|free shipping|new arrivals?|coming soon|lookbook|newsletter)",
    r"^\d+%", r"%\s*off", r"\.(jpg|png|webp|html?)$", r"^https?:",
    r"^(all items?|view all|see all|shop all|collection)",
]
JUNK_RE = re.compile("|".join(JUNK_PATTERNS), re.I)

def looks_like_product(title: str) -> bool:
    t = (title or "").strip()
    if len(t) < 3 or len(t) > 70:
        return False
    if JUNK_RE.search(t):
        return False
    letters = sum(ch.isalpha() for ch in t)
    if letters < 3 or letters / len(t) < 0.45:
        return False
    if len(t.split()) > 12:
        return False
    return True


def price_of(p, country):
    v = p.get("price")
    if not v: return None
    try: n = float(v)
    except (TypeError, ValueError): return None
    sym = CCY_BY_COUNTRY.get(country, "€")
    n = int(round(n))
    return f"{n} {sym}" if sym == "zł" else f"{sym}{n}"

# Who a piece is cut for. Shops say it in the product type, the title or the
# tags ("Women's Cargo Pant", "Mens Tee"); a womenswear label says it once in
# its own description and means it for everything it makes. Anything that says
# nothing is unisex, which is most of streetwear and the honest default.
# Note the word boundary: "women" must never be read as "men".
W_RE = re.compile(r"\b(women'?s?|woman'?s?|ladies|female|girls?)\b"
                  r"|\b(dress|dresses|skirts?|blouses?|bralettes?|bodysuits?|corsets?"
                  r"|bikinis?|jumpsuits?|camisoles?|leotards?|heels)\b", re.I)
M_RE = re.compile(r"\b(men'?s?|man'?s?|male|boys?)\b|\b(boxers?|briefs)\b", re.I)


def gender_of(p, brand_default):
    text = " ".join(str(p.get(k) or "") for k in ("type", "title", "tags"))
    if W_RE.search(text):
        return "w"
    if M_RE.search(text):
        return "m"
    return brand_default


def brand_gender(b):
    text = " ".join(str(b.get(k) or "") for k in ("niche", "style", "brand"))
    if W_RE.search(text):
        return "w"
    if M_RE.search(text):
        return "m"
    return "u"


def esc(s):
    return (s or "").replace("\\", "").replace('"', "'").strip()

catalog, brand_rows = [], []
pid = 1000
dropped = 0
for b in brands:
    b_gender = brand_gender(b)
    brand_rows.append({
        "brand": esc(b["brand"]), "niche": esc(b["niche"]), "country": esc(b["country"]),
        "site": b.get("site"), "handle": b.get("handle"),
        "kind": b["kind"], "style": b["style"], "n": len(b["products"]),
        "g": b_gender,
    })
    for p in b["products"]:
        title = esc(p["title"])[:44]
        if not title or not p.get("image"): continue
        if not looks_like_product(title):
            dropped += 1
            continue
        pid += 1
        catalog.append({
            "id": pid, "brand": esc(b["brand"]), "name": title,
            "cat": cat_of(p, b["kind"]), "style": b["style"], "kind": p["kind"],
            "price": price_of(p, b["country"]), "indie": True,
            "src": b.get("handle") or ("@" + re.sub(r"[^a-z0-9]", "", b["brand"].lower())),
            "photo": p["image"], "link": p["url"],
            "g": gender_of(p, b_gender),
            "likes": random.randint(80, 3200),
        })

# a label may not say what it makes, but its rail does: when four out of five
# pieces are womenswear, the brand card belongs under Women too
counts = {}
for it in catalog:
    row = counts.setdefault(it["brand"], {"w": 0, "m": 0, "u": 0})
    row[it["g"]] += 1
for row in brand_rows:
    c = counts.get(row["brand"])
    if not c or row["g"] != "u":
        continue
    total = sum(c.values())
    if total >= 4:
        for g in ("w", "m"):
            if c[g] / total >= 0.7:
                row["g"] = g

# feed = a readable slice: max 3 items per brand, apparel first
random.seed(7)
by_brand = {}
for it in catalog:
    by_brand.setdefault(it["brand"], []).append(it)
feed = []
for items in by_brand.values():
    items.sort(key=lambda x: 0 if x["kind"] == "clothing" else 1)
    feed.extend(items[:3])
random.shuffle(feed)
feed_ids = [i["id"] for i in feed[:120]]

out = os.path.join(HERE, "assets", "js")
os.makedirs(out, exist_ok=True)
with open(os.path.join(out, "catalog.js"), "w", encoding="utf-8") as f:
    f.write("/* generated by build_app_data.py — do not edit by hand */\n")
    f.write("const BRANDS=" + json.dumps(brand_rows, ensure_ascii=False, separators=(",", ":")) + ";\n")
    f.write("const CATALOG=" + json.dumps(catalog, ensure_ascii=False, separators=(",", ":")) + ";\n")
    f.write("const FEED_IDS=" + json.dumps(feed_ids, separators=(",", ":")) + ";\n")

genders = {}
for it in catalog: genders[it["g"]] = genders.get(it["g"], 0) + 1
print(f"cut for  : {genders}   (w=women, m=men, u=either)")

kinds = {}
for it in catalog: kinds[it["kind"]] = kinds.get(it["kind"], 0) + 1
cats = {}
for it in catalog: cats[it["cat"]] = cats.get(it["cat"], 0) + 1
size = os.path.getsize(os.path.join(out, "catalog.js")) // 1024
print(f"junk dropped: {dropped}")
print(f"brands   : {len(brand_rows)}")
print(f"products : {len(catalog)}  (feed shows {len(feed_ids)})")
print(f"kinds    : {kinds}")
print(f"categories: {cats}")
print(f"-> assets/js/catalog.js  ({size} KB)")
