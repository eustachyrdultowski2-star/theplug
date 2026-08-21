#!/usr/bin/env python3
"""Re-fetch the shops people are watching and raise an alert when a watched
piece drops in price or comes back in stock.

Run it on a schedule (Task Scheduler / cron):  py check_alerts.py
"""
import json, os, re, sys, time, urllib.parse
from concurrent.futures import ThreadPoolExecutor

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
import store
from fetch_shop import try_shopify          # reuse the working Shopify reader


def host_of(url):
    if not url:
        return None
    if not url.startswith("http"):
        url = "https://" + url
    return urllib.parse.urlparse(url).netloc.replace("www.", "") or None


def money(v):
    if v in (None, ""):
        return None
    m = re.search(r"\d+(?:[.,]\d+)?", str(v))
    return float(m.group(0).replace(",", ".")) if m else None


def snapshot(domain):
    """product-url -> {price, available, title, image}"""
    out = {}
    try:
        for p in try_shopify(domain, limit=250):
            out[p["url"]] = {"price": money(p.get("price")), "title": p.get("title"),
                             "image": p.get("image")}
    except Exception:
        pass
    return out


def run():
    watches = store.load("watches", [])          # [{id,name,brand,link,email,price}]
    if not watches:
        print("nobody is watching anything yet")
        return

    domains = sorted({host_of(w.get("link")) for w in watches if w.get("link")} - {None})
    print(f"watches: {len(watches)} | shops to check: {len(domains)}")

    with ThreadPoolExecutor(max_workers=10) as ex:
        snaps = dict(zip(domains, ex.map(snapshot, domains)))

    alerts = store.load("alerts", [])
    seen = {(a["watchId"], a["kind"], a.get("price")) for a in alerts}
    fired = 0

    for w in watches:
        dom = host_of(w.get("link"))
        snap = snaps.get(dom) or {}
        cur = snap.get(w.get("link"))
        was = money(w.get("price"))

        if cur is None:                          # gone from the catalogue
            continue
        now = cur["price"]

        kind = None
        if was is not None and now is not None and now < was - 0.01:
            kind = "price"
        elif w.get("soldOut") and now is not None:
            kind = "restock"

        if not kind:
            w["price"] = now if now is not None else w.get("price")
            continue

        key = (w["id"], kind, now)
        if key in seen:
            continue
        alerts.append({
            "watchId": w["id"], "kind": kind, "brand": w.get("brand"),
            "name": w.get("name") or cur.get("title"), "link": w.get("link"),
            "image": w.get("image") or cur.get("image"),
            "was": was, "price": now, "at": int(time.time()), "read": False,
        })
        w["price"] = now
        w["soldOut"] = False
        fired += 1

    store.save("watches", watches)
    store.save("alerts", alerts[-500:])
    print(f"new alerts: {fired}")
    for a in alerts[-fired:] if fired else []:
        print(f"  {a['kind']:8} {a['brand']} — {a['name'][:40]}  {a['was']} -> {a['price']}")


if __name__ == "__main__":
    run()
