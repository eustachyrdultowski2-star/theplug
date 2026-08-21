#!/usr/bin/env python3
"""Pull a contact address off each brand's own site (footer / contact page).
No sending — this only builds a list you can decide what to do with."""
import json, os, re, sys, gzip, io, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
MAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
JUNK = re.compile(r"(sentry|wixpress|example|\.png|\.jpg|\.webp|godaddy|shopify\.com|@2x)", re.I)
PAGES = ["", "/pages/contact", "/contact", "/pages/contact-us", "/contact-us",
         "/pages/about", "/about", "/pages/faq"]


def get(url, timeout=7):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read(900_000)
        if r.headers.get("Content-Encoding") == "gzip":
            raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
    return raw.decode("utf-8", "ignore")


def find(brand):
    site = (brand.get("site") or "").strip()
    if not site:
        return None
    base = site.rstrip("/")
    host = urllib.parse.urlparse(base).netloc.replace("www.", "")
    for path in PAGES:
        try:
            html = get(base + path)
        except Exception:
            continue
        for m in MAIL.findall(html):
            if JUNK.search(m):
                continue
            # prefer an address on the brand's own domain
            return {"brand": brand["brand"], "site": base, "email": m.lower(),
                    "own_domain": host.split(".")[0] in m.lower(),
                    "instagram": brand.get("handle")}
    return {"brand": brand["brand"], "site": base, "email": None,
            "instagram": brand.get("handle")}


if __name__ == "__main__":
    brands = json.load(open(os.path.join(HERE, "brands_full.json"), encoding="utf-8"))
    withsite = [b for b in brands if (b.get("site") or "").strip()]
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    target = withsite[:limit] if limit else withsite
    print(f"brands with a site: {len(withsite)} | checking: {len(target)}")

    with ThreadPoolExecutor(max_workers=12) as ex:
        rows = [r for r in ex.map(find, target) if r]

    found = [r for r in rows if r["email"]]
    print(f"\nfound {len(found)}/{len(rows)} addresses")
    for r in found[:15]:
        print(f"  {r['brand'][:24]:24} {r['email']}")
    if not limit:
        json.dump(rows, open(os.path.join(HERE, "contacts.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print("saved -> contacts.json")
