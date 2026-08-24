#!/usr/bin/env python3
"""The v3 sheet has no websites for the new brands, only search links.
Guess likely shop domains from the brand name and keep the ones that
actually answer with a real catalog."""
import json, os, re, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")


def slugs(name):
    base = re.sub(r"[^a-z0-9 ]", "", name.lower()).strip()
    flat = base.replace(" ", "")
    dash = base.replace(" ", "-")
    out = [flat, dash]
    if " " in base:                       # first word alone, e.g. "Half Evil" -> half
        out.append(base.split()[0])
    return [s for s in dict.fromkeys(out) if len(s) > 2]


def candidates(name):
    doms = []
    for s in slugs(name):
        doms += [f"{s}.com", f"{s}.co", f"{s}.shop", f"{s}.store",
                 f"shop{s}.com", f"{s}worldwide.com", f"{s}.us", f"{s}.eu"]
    return doms[:10]


def shopify(domain, limit=10, timeout=6):
    url = f"https://{domain}/products.json?limit={limit}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        if "json" not in (r.headers.get("Content-Type") or ""):
            raise ValueError("not json")
        data = json.load(r)
    out = []
    for p in data.get("products", []):
        imgs, vs = p.get("images") or [], p.get("variants") or []
        if not imgs:
            continue
        out.append({"title": p.get("title", ""), "type": p.get("product_type", ""),
                    "tags": "", "price": (vs[0].get("price") if vs else None),
                    "image": imgs[0].get("src"),
                    "url": f"https://{domain}/products/{p.get('handle')}"})
    return out


# Guessing a domain from a name lands on the wrong shop often enough that the
# catalog has to be read before it is believed. "Drescode" resolved to a
# dropshipping store selling lubricant and phone cases under a streetwear name,
# and nothing in the old check would have noticed.
DROPSHIP = re.compile(r"""
    shipping\s*protection | discreet\s*shipping
  | lubricant | lube | masturbat | vibrator | penis | sex\s*toy
  | teeth\s*whiten | hair\s*removal | posture\s*corrector
  | iphone\s*case | screen\s*protector | car\s*mount
  | as\s*seen\s*on\s*tv | the\s*\#1
""", re.I | re.X)


def looks_like_a_clothing_shop(prods) -> bool:
    """One junk title is a stray product; a quarter of them is the whole shop."""
    if not prods:
        return False
    junk = sum(1 for p in prods if DROPSHIP.search(p.get("title") or ""))
    return junk / len(prods) < 0.25


def find(brand):
    """Return (domain, products) for the first candidate that answers."""
    for dom in candidates(brand["brand"]):
        try:
            prods = shopify(dom)
        except Exception:
            continue
        if len(prods) < 3:                # a parked page, not a shop
            continue
        if not looks_like_a_clothing_shop(prods):
            print(f"  skip {brand['brand'][:24]:24} -> {dom} (dropshipping catalog)")
            continue
        return dom, prods
    return None, []


# v3 fills the website column with search links, not shops
PLACEHOLDER = re.compile(
    r"(google\.[a-z.]+/search|bing\.com/search|duckduckgo|"
    r"instagram\.com/explore|tiktok\.com/search|/search\?q=)", re.I)


def real_site(b) -> bool:
    s = (b.get("site") or "").strip()
    return bool(s) and not PLACEHOLDER.search(s)


def enrich(b):
    if b.get("products") or real_site(b):
        return b
    if PLACEHOLDER.search(b.get("site") or ""):
        b["site"] = None          # drop the fake link so the UI never links to a search page
    dom, prods = find(b)
    if prods:
        b["site"] = "https://" + dom
        b["products"] = prods
        b["source"] = "guessed-shopify"
    return b


if __name__ == "__main__":
    brands = json.load(open(os.path.join(HERE, "brands_full.json"), encoding="utf-8"))
    todo = [b for b in brands if not b["products"] and not real_site(b)]
    sample = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    target = todo[:sample] if sample else todo
    print(f"brands without any url: {len(todo)} | trying: {len(target)}")

    with ThreadPoolExecutor(max_workers=16) as ex:
        done = list(ex.map(enrich, target))

    hits = [b for b in done if b["products"]]
    for b in hits:
        print(f"  OK  {b['brand'][:26]:26} -> {b['site']}  ({len(b['products'])} products)")
    print(f"\nfound {len(hits)}/{len(target)}")

    if not sample:
        by = {b["brand"]: b for b in done}
        for i, b in enumerate(brands):
            if b["brand"] in by:
                brands[i] = by[b["brand"]]
        json.dump(brands, open(os.path.join(HERE, "brands_full.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print("saved -> brands_full.json")
