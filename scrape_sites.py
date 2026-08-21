#!/usr/bin/env python3
"""Pull products from the brands whose shops are NOT plain Shopify.

Tries, in order: Shopify alt paths -> WooCommerce Store API -> Squarespace JSON
-> schema.org JSON-LD -> generic HTML (product links + images).
Writes brands_scraped.json (same shape as brands_full.json).
"""
import json, os, re, sys, time, gzip, io, urllib.parse, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
from html import unescape

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
HDRS = {"User-Agent": UA, "Accept": "*/*", "Accept-Language": "en;q=0.9",
        "Accept-Encoding": "gzip"}


def get(url, timeout=7, as_json=False):
    req = urllib.request.Request(url, headers=HDRS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read(3_500_000)
        if r.headers.get("Content-Encoding") == "gzip":
            raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
        text = raw.decode("utf-8", "ignore")
    return json.loads(text) if as_json else text


def absolutise(u, base):
    if not u:
        return None
    if u.startswith("//"):
        return "https:" + u
    if u.startswith("http"):
        return u
    return urllib.parse.urljoin(base, u)


def price_str(v):
    if v in (None, "", 0):
        return None
    s = str(v)
    m = re.search(r"\d+(?:[.,]\d+)?", s)
    return m.group(0) if m else None


# ---------- strategies ----------
def try_shopify_alt(base):
    for path in ("/collections/all/products.json?limit=12",
                 "/products.json?limit=12&page=1",
                 "/en/products.json?limit=12"):
        try:
            d = get(base + path, as_json=True)
        except Exception:
            continue
        out = []
        for p in d.get("products", []):
            imgs, vs = p.get("images") or [], p.get("variants") or []
            if not imgs:
                continue
            out.append({"title": p.get("title", ""), "type": p.get("product_type", ""),
                        "tags": "", "price": (vs[0].get("price") if vs else None),
                        "image": imgs[0].get("src"),
                        "url": base + "/products/" + str(p.get("handle"))})
        if out:
            return out, "shopify-alt"
    return [], None


def try_woocommerce(base):
    for path in ("/wp-json/wc/store/v1/products?per_page=12",
                 "/wp-json/wc/store/products?per_page=12"):
        try:
            d = get(base + path, as_json=True)
        except Exception:
            continue
        out = []
        for p in d if isinstance(d, list) else []:
            imgs = p.get("images") or []
            if not imgs:
                continue
            out.append({"title": unescape(re.sub("<[^>]+>", "", p.get("name", ""))),
                        "type": "", "tags": "",
                        "price": price_str((p.get("prices") or {}).get("price")),
                        "image": imgs[0].get("src"), "url": p.get("permalink")})
        if out:
            return out, "woocommerce"
    return [], None


def try_squarespace(base):
    for path in ("/shop?format=json", "/store?format=json", "/products?format=json"):
        try:
            d = get(base + path, as_json=True)
        except Exception:
            continue
        items = d.get("items") or []
        out = []
        for p in items:
            img = p.get("assetUrl") or ((p.get("items") or [{}])[0].get("assetUrl"))
            if not img:
                continue
            sv = (p.get("structuredContent") or {}).get("variants") or []
            out.append({"title": p.get("title", ""), "type": "", "tags": "",
                        "price": price_str(sv[0].get("price") if sv else None),
                        "image": img,
                        "url": absolutise(p.get("fullUrl"), base)})
        if out:
            return out, "squarespace"
    return [], None


JSONLD_RE = re.compile(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
                       re.S | re.I)


def _ld_products(node, base, out):
    if isinstance(node, list):
        for n in node:
            _ld_products(n, base, out)
        return
    if not isinstance(node, dict):
        return
    t = node.get("@type")
    types = t if isinstance(t, list) else [t]
    if "Product" in types:
        img = node.get("image")
        if isinstance(img, list):
            img = img[0] if img else None
        if isinstance(img, dict):
            img = img.get("url")
        offers = node.get("offers") or {}
        if isinstance(offers, list):
            offers = offers[0] if offers else {}
        if img and node.get("name"):
            out.append({"title": str(node["name"]), "type": "", "tags": "",
                        "price": price_str(offers.get("price")),
                        "image": absolutise(img, base),
                        "url": absolutise(node.get("url") or offers.get("url"), base) or base})
    for key in ("itemListElement", "hasPart", "mainEntity", "item", "@graph"):
        if key in node:
            _ld_products(node[key], base, out)


def try_jsonld(base, paths):
    out = []
    for path in paths:
        try:
            html = get(base + path)
        except Exception:
            continue
        for block in JSONLD_RE.findall(html):
            try:
                _ld_products(json.loads(block.strip()), base + path, out)
            except Exception:
                continue
        if len(out) >= 4:
            break
    return (out[:12], "json-ld") if out else ([], None)


IMG_RE = re.compile(r'<img[^>]+>', re.I)
SRC_RE = re.compile(r'(?:data-src|data-srcset|srcset|src)=["\']([^"\']+)["\']', re.I)
ALT_RE = re.compile(r'alt=["\']([^"\']{3,80})["\']', re.I)
LINK_RE = re.compile(r'<a[^>]+href=["\']([^"\']*(?:/product|/products|/shop/|/item)[^"\']*)["\'][^>]*>(.{0,400}?)</a>', re.S | re.I)


def try_html(base, paths):
    out, seen = [], set()
    for path in paths:
        try:
            html = get(base + path)
        except Exception:
            continue
        for href, inner in LINK_RE.findall(html):
            im = IMG_RE.search(inner)
            if not im:
                continue
            src = SRC_RE.search(im.group(0))
            if not src:
                continue
            img = absolutise(src.group(1).split()[0], base + path)
            if not img or img in seen or img.endswith(".svg"):
                continue
            alt = ALT_RE.search(im.group(0))
            title = unescape(alt.group(1)).strip() if alt else \
                re.sub(r"[-_/]+", " ", href.rstrip("/").split("/")[-1]).strip()
            title = re.sub(r"\s+", " ", title)[:60]
            if len(title) < 3:
                continue
            seen.add(img)
            out.append({"title": title, "type": "", "tags": "", "price": None,
                        "image": img, "url": absolutise(href, base + path)})
            if len(out) >= 12:
                return out, "html"
    return (out, "html") if out else ([], None)


SHOP_PATHS = ["/shop", "/products", "/collections/all", "/store", "/all",
              "/shop/all", "/collections", "/en/shop", "", "/product-category/all"]


SHOP_LINK_RE = re.compile(
    r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(?:(?!</a>).){0,60}?'
    r'(shop|store|products|collection|catalog|sklep|boutique)', re.I | re.S)


def host_variants(site: str):
    """Some hosts only answer on www (or only without it, or on http)."""
    if not site.startswith("http"):
        site = "https://" + site
    p = urllib.parse.urlparse(site)
    host = p.netloc
    alt = host[4:] if host.startswith("www.") else "www." + host
    out = [f"https://{host}", f"https://{alt}", f"http://{host}"]
    seen, uniq = set(), []
    for u in out:
        if u not in seen:
            seen.add(u); uniq.append(u.rstrip("/"))
    return uniq


def discover_shop_paths(base):
    """Landing pages often just link to the real shop — follow one level."""
    try:
        html = get(base + "/")
    except Exception:
        return []
    found = []
    for href, _ in SHOP_LINK_RE.findall(html):
        u = absolutise(href, base + "/")
        if not u or urllib.parse.urlparse(u).netloc not in (urllib.parse.urlparse(base).netloc, ""):
            continue
        path = urllib.parse.urlparse(u).path.rstrip("/")
        if path and path not in found and len(path) < 40:
            found.append(path)
        if len(found) >= 5:
            break
    return found


def scrape_base(brand, base, deadline=None):
    over = lambda: deadline is not None and time.time() > deadline
    for fn in (try_shopify_alt, try_woocommerce, try_squarespace):
        if over():
            return [], None
        try:
            prods, how = fn(base)
        except Exception:
            prods, how = [], None
        if prods:
            return prods, how
    if over():
        return [], None
    paths = SHOP_PATHS + [p for p in discover_shop_paths(base) if p not in SHOP_PATHS]
    paths = paths[:8]                      # keep the tail bounded
    for fn in (try_jsonld, try_html):
        if over():
            return [], None
        try:
            prods, how = fn(base, paths)
        except Exception:
            prods, how = [], None
        if prods:
            return prods, how
    return [], None


BRAND_BUDGET = 45          # seconds per brand, hard stop


def scrape(brand):
    """Try a brand, but never spend more than BRAND_BUDGET on it.
    Without this a dead domain can burn 20 minutes on retries alone."""
    site = (brand.get("site") or "").strip()
    if not site:
        return brand
    deadline = time.time() + BRAND_BUDGET
    for base in host_variants(site):
        if time.time() > deadline:
            break
        try:
            prods, how = scrape_base(brand, base, deadline)
        except Exception:
            prods, how = [], None
        if prods:
            brand["products"] = prods
            brand["source"] = how
            brand["site"] = base
            return brand
    brand["source"] = None
    return brand


if __name__ == "__main__":
    brands = json.load(open(os.path.join(HERE, "brands_full.json"), encoding="utf-8"))
    todo = [b for b in brands if not b["products"]]
    print(f"scraping {len(todo)} sites…")
    with ThreadPoolExecutor(max_workers=12) as ex:
        done = list(ex.map(scrape, todo))

    by_name = {b["brand"]: b for b in done}
    got = 0
    how = {}
    for b in brands:
        if b["brand"] in by_name:
            b.update(by_name[b["brand"]])
        if b["products"]:
            got += 1
        s = b.get("source")
        if s:
            how[s] = how.get(s, 0) + 1

    json.dump(brands, open(os.path.join(HERE, "brands_full.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    newly = sum(1 for b in done if b["products"])
    print(f"\nnewly scraped: {newly}/{len(todo)}")
    print("methods:", how)
    print(f"brands with catalog now: {got}/{len(brands)}")
    print(f"total products: {sum(len(b['products']) for b in brands)}")
