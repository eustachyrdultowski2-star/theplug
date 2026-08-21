#!/usr/bin/env python3
"""Merge the v3 spreadsheet into brands_full.json.

Existing brands keep the catalogs already fetched; only brands that are new
(or still empty) get scraped, so a re-run is cheap.
"""
import json, os, re, sys
from concurrent.futures import ThreadPoolExecutor

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
from read_xlsx import read
from import_brands import work, brand_kind, style_of
from scrape_sites import scrape

XLSX = sys.argv[1] if len(sys.argv) > 1 else \
    r"C:/Users/eusta/Downloads/underground_streetwear_brand_database_v3.xlsx"

rows = list(read(XLSX).values())[0]
sheet = [r for r in rows[1:] if len(r) > 1 and r[1].strip()]

existing = json.load(open(os.path.join(HERE, "brands_full.json"), encoding="utf-8"))
by_name = {b["brand"].strip().lower(): b for b in existing}

def tiktok_of(row):
    tt = row[6].strip() if len(row) > 6 else ""
    m = re.search(r"tiktok\.com/@([A-Za-z0-9._]+)", tt or "")
    return "@" + m.group(1) if m else (tt or None)

fresh, updated = [], 0
for r in sheet:
    name = r[1].strip()
    key = name.lower()
    tt = tiktok_of(r)
    if key in by_name:
        if tt and not by_name[key].get("tiktok"):
            by_name[key]["tiktok"] = tt
            updated += 1
        continue
    fresh.append((r, tt))

print(f"sheet: {len(sheet)} | already known: {len(sheet)-len(fresh)} | new: {len(fresh)}")

def build(pair):
    row, tt = pair
    b = work(row)            # classify + try Shopify /products.json
    if not b["products"]:
        b = scrape(b)        # fall back to the generic site scraper
    if tt:
        b["tiktok"] = tt
    return b

with ThreadPoolExecutor(max_workers=14) as ex:
    built = list(ex.map(build, fresh))

merged = existing + built
json.dump(merged, open(os.path.join(HERE, "brands_full.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

withp = [b for b in merged if b["products"]]
print(f"\nbrands total : {len(merged)}  (+{len(built)} new, {updated} tiktok handles added)")
print(f"with catalog : {len(withp)}")
print(f"products     : {sum(len(b['products']) for b in merged)}")
