#!/usr/bin/env python3
"""Brand plus garment -> the actual product, with its photo and shop link.

Knowing that the jeans are Elysian only half-answers the question; people
still have to go and find them. We already hold 2100+ real products scraped
from brand shops, so answer from those first, and fall back to a live read of
the shop's public Shopify catalog for brands we never scraped.
"""
import json, os, re, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, ".cache")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
SHOP_TTL = 60 * 60 * 24        # a shop's catalog is worth re-reading once a day
PROBE_TTL = 60 * 60 * 24 * 7   # where a brand sells changes far more slowly

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

# Zara and friends run no public catalogue, so there is no product row to link.
# The next best thing is their own search, pre-filled — one click instead of a
# brand homepage that makes you start again.
RETAIL_SEARCH = {
    "zara": "https://www.zara.com/pl/pl/search?searchTerm={q}",
    "uniqlo": "https://www.uniqlo.com/eu/en/search?q={q}",
    "hm": "https://www2.hm.com/pl_pl/search-results.html?q={q}",
    "handm": "https://www2.hm.com/pl_pl/search-results.html?q={q}",
    "bershka": "https://www.bershka.com/pl/search?q={q}",
    "pullbear": "https://www.pullandbear.com/pl/search?q={q}",
    "stradivarius": "https://www.stradivarius.com/pl/search?q={q}",
    "massimodutti": "https://www.massimodutti.com/pl/search?q={q}",
    "mango": "https://shop.mango.com/pl/search?q={q}",
    "cos": "https://www.cos.com/en_pln/search.html?q={q}",
    "arket": "https://www.arket.com/en_pln/search.html?q={q}",
    "weekday": "https://www.weekday.com/en_pln/search.html?q={q}",
    "monki": "https://www.monki.com/en_pln/search.html?q={q}",
    "reserved": "https://www.reserved.com/pl/pl/search?q={q}",
    "cropp": "https://www.cropp.com/pl/pl/search?q={q}",
    "houseofsunny": "https://houseofsunny.co.uk/search?q={q}",
    "carhartt": "https://www.carhartt-wip.com/en/search?q={q}",
    "levis": "https://www.levi.com/PL/en/search?q={q}",
    "acnestudios": "https://www.acnestudios.com/pl/en/search?q={q}",
    "stoneisland": "https://www.stoneisland.com/en-pl/search?q={q}",
    "arcteryx": "https://arcteryx.com/pl/en/search?q={q}",
    "salomon": "https://www.salomon.com/en-pl/search?q={q}",
}

GARMENT_QUERY = {
    "jeans": "jeans", "shoes": "shoes", "belt": "belt", "shirt": "shirt",
    "jacket": "jacket", "knit": "knitwear", "scarf": "scarf", "hat": "cap",
    "bag": "bag", "glasses": "sunglasses", "jewelry": "jewellery", "watch": "watch",
}


def retail_search(brand_name, garment=""):
    """A ready-made search on the label's own shop, or None."""
    tpl = RETAIL_SEARCH.get(key(brand_name))
    if not tpl:
        return None
    q = (brand_name + " " + GARMENT_QUERY.get(garment, garment or "")).strip()
    import urllib.parse as _u
    url = tpl.format(q=_u.quote_plus(GARMENT_QUERY.get(garment, garment) or ""))
    host = _u.urlparse(url).netloc.replace("www.", "")
    return {"url": url, "shop": host}


CCY_BY_COUNTRY = {"USA": "$", "UK": "£", "Australia": "A$", "Canada": "C$",
                  "Japan": "¥", "Korea": "₩", "South Korea": "₩", "Poland": "zł"}

_brands = None


def brands():
    """Every brand we know, with whatever products we hold for it.

    brands_full.json is the scraping working file and stays out of git, so on
    the server it simply is not there. The site ships the same catalogue as
    assets/js/catalog.js, which is committed — read that instead rather than
    answering "no idea" to every lookup in production.
    """
    global _brands
    if _brands is not None:
        return _brands

    full = os.path.join(HERE, "brands_full.json")
    if os.path.exists(full):
        with open(full, encoding="utf-8") as f:
            _brands = json.load(f)
        return _brands

    js = open(os.path.join(HERE, "assets", "js", "catalog.js"), encoding="utf-8").read()
    rows = json.loads(re.search(r"^const BRANDS=(.*);$", js, re.M).group(1))
    catalog = json.loads(re.search(r"^const CATALOG=(.*);$", js, re.M).group(1))

    by_brand = {}
    for it in catalog:
        by_brand.setdefault(it.get("brand"), []).append({
            "title": it.get("name"),
            "type": it.get("cat") or "",
            "price": it.get("price"),          # already carries its currency here
            "image": it.get("photo"),
            "url": it.get("link"),
            "kind": it.get("kind") or "clothing",
        })
    for b in rows:
        b["products"] = [p for p in by_brand.get(b.get("brand"), []) if p.get("url")]
    _brands = rows
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


def shopify(domain, limit=250, quiet=False):
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
        with urllib.request.urlopen(req, timeout=6 if quiet else 20) as r:
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


def probe(brand_name):
    """No row for this brand: work out where it actually sells.

    A TikTok bio link would be the obvious source, but TikTok serves logged-out
    requests a stripped profile with no link in it. So take the honest route —
    try the domains a brand of this name would plausibly own, and believe only
    the one that answers with a real catalog. A shop with three products is a
    shop; a parked page is not.
    """
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, "probe_" + key(brand_name) + ".json")
    if os.path.exists(path) and time.time() - os.path.getmtime(path) < PROBE_TTL:
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    base = re.sub(r"[^a-z0-9 ]", "", (brand_name or "").lower()).strip()
    if len(base) < 3:
        return {"domain": None, "products": []}
    stems = [base.replace(" ", ""), base.replace(" ", "-")]
    if " " in base:
        stems.append(base.split()[0])
    # brands rarely own the bare name: represent is represent-clo.com, broken
    # planet is brokenplanetmarket.com. Try the shapes labels actually use.
    doms = []
    for st in dict.fromkeys(stems):
        if len(st) > 2:
            doms += [st + ".com", st + ".co", st + ".shop", st + ".store",
                     "shop" + st + ".com", st + ".us", st + ".xyz", st + ".co.uk",
                     st + "clo.com", st + "-clo.com", st + "studios.com",
                     st + "market.com", st + "official.com", st + "worldwide.com"]
    doms = doms[:26]

    def one(dom):
        prods = shopify(dom, limit=250, quiet=True)
        return (dom, prods) if len(prods) >= 3 else (dom, None)

    found = {"domain": None, "products": []}
    with ThreadPoolExecutor(max_workers=6) as pool:
        for dom, prods in pool.map(one, doms):
            if prods and not found["domain"]:
                found = {"domain": dom, "products": prods}
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(found, f)                       # remember the misses too
    except Exception:
        pass
    return found


def find(brand_name, garment):
    """The single best product, or None when we would only be guessing."""
    row = find_brand(brand_name)
    site = (row or {}).get("site")
    products = (row or {}).get("products") or []
    if not products and site:
        products = shopify(site)
    if not products:
        # unknown brand, or one we hold a name for and nothing else
        hit = probe(brand_name)
        if hit.get("domain"):
            site = "https://" + hit["domain"]
            products = hit["products"]
    if not products:
        return None

    best, best_score = None, 0
    for p in products:
        s = score(p, garment)
        if s > best_score:
            best, best_score = p, s
    if not best or best_score < 5:                    # a weak match is worse than none
        return None

    ccy = CCY_BY_COUNTRY.get((row or {}).get("country"), "$")
    price = best.get("price")
    if price and str(price)[0].isdigit():
        price = ccy + str(price)                      # raw shop numbers need one
    return {
        "brand": (row or {}).get("brand") or brand_name,
        "name": best.get("title"),
        "price": str(price) if price else None,
        "image": best.get("image"),
        "url": best.get("url"),
        "site": site,
        "shop": (site or "").replace("https://", "").replace("http://", "").strip("/"),
    }


if __name__ == "__main__":
    import sys
    b = sys.argv[1] if len(sys.argv) > 1 else "Mutimer"
    g = sys.argv[2] if len(sys.argv) > 2 else "shirt"
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(find(b, g), ensure_ascii=False, indent=1))
