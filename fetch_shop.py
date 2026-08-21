#!/usr/bin/env python3
"""Pull REAL product data (name, price, image) straight from brand shops.
Most indie labels run Shopify, which exposes /products.json publicly."""
import json, sys, urllib.request, urllib.error

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"

DOMAINS = {
    "Scuffers": "scuffers.com",
    "Unfounded Studios": "unfoundedstudios.com",
    "Maison North": "maisonnorth.shop",
    "Society de Nobodies": "societydenobodies.com",
    "Corteiz": "crtz.xyz",
}

def try_shopify(domain, limit=8):
    url = f"https://{domain}/products.json?limit={limit}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=25) as r:
        data = json.load(r)
    out = []
    for p in data.get("products", []):
        imgs = p.get("images") or []
        variants = p.get("variants") or []
        if not imgs:
            continue
        out.append({
            "title": p.get("title"),
            "type": p.get("product_type") or "",
            "handle": p.get("handle"),
            "price": (variants[0].get("price") if variants else None),
            "image": imgs[0].get("src"),
            "url": f"https://{domain}/products/{p.get('handle')}",
        })
    return out

if __name__ == "__main__":
    results = {}
    for brand, dom in DOMAINS.items():
        try:
            items = try_shopify(dom)
            results[brand] = items
            print(f"OK   {brand:22} {dom:28} {len(items)} products")
            for it in items[:3]:
                print(f"       - {it['title'][:45]}  {it['price']}")
        except Exception as e:
            print(f"FAIL {brand:22} {dom:28} {type(e).__name__}: {str(e)[:60]}")
    with open("shop_data.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=1)
    print("\nsaved -> shop_data.json")
