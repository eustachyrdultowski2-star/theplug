#!/usr/bin/env python3
"""Real visual search: upload an image -> Google Lens (via Apify) -> product matches.

Lens needs a PUBLIC url, and the user's file lives on their machine, so we park
the bytes in an Apify key-value store record (publicly readable) and hand Lens
that url.
"""
import os, json, time, base64, hashlib, urllib.parse, urllib.request

import brand_detect  # reuses .env loading

LENS_ACTOR = os.environ.get("LENS_ACTOR", "scrape.badger~google-lens-scraper")
STORE_NAME = "theplug-uploads"
_store_id = None


def _token():
    tok = os.environ.get("APIFY_TOKEN")
    if not tok:
        raise RuntimeError("APIFY_TOKEN not set")
    return tok


def _api(url, data=None, method=None, timeout=60, content_type="application/json"):
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", content_type)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read()
    return json.loads(body) if body and content_type == "application/json" else body


def get_store_id():
    """Get-or-create the uploads store (Apify returns the existing one by name)."""
    global _store_id
    if _store_id:
        return _store_id
    url = (f"https://api.apify.com/v2/key-value-stores?name={STORE_NAME}"
           f"&token={urllib.parse.quote(_token())}")
    res = _api(url, data=b"", method="POST")
    _store_id = res["data"]["id"]
    # Lens fetches the image anonymously, so the record must be readable
    # without a token. Default is RESTRICTED -> 403.
    if res["data"].get("generalAccess") != "ANYONE_WITH_ID_CAN_READ":
        try:
            _api(f"https://api.apify.com/v2/key-value-stores/{_store_id}"
                 f"?token={urllib.parse.quote(_token())}",
                 data=json.dumps({"generalAccess": "ANYONE_WITH_ID_CAN_READ"}).encode(),
                 method="PUT")
        except Exception as e:
            print("[warn: could not make the upload store public:", e, "]")
    return _store_id


def upload_image(raw: bytes, content_type="image/jpeg") -> str:
    """Store the bytes and return a public https url Lens can fetch."""
    store = get_store_id()
    key = "up-" + hashlib.sha1(raw + str(time.time()).encode()).hexdigest()[:16] + ".jpg"
    url = (f"https://api.apify.com/v2/key-value-stores/{store}/records/{key}"
           f"?token={urllib.parse.quote(_token())}")
    req = urllib.request.Request(url, data=raw, method="PUT")
    req.add_header("Content-Type", content_type)
    urllib.request.urlopen(req, timeout=90).read()
    return f"https://api.apify.com/v2/key-value-stores/{store}/records/{key}"


def lens_search(image_url: str, country="pl", limit=12):
    """Run Google Lens and return cleaned shopping matches."""
    payload = json.dumps({
        "image_url": image_url, "product": True,
        "visual_matches": True, "exact_matches": True, "country": country,
    }).encode()
    run_url = (f"https://api.apify.com/v2/acts/{LENS_ACTOR}/run-sync-get-dataset-items"
               f"?token={urllib.parse.quote(_token())}")
    items = _api(run_url, data=payload, method="POST", timeout=180)

    seen, out = set(), []
    for it in items:
        title = (it.get("title") or "").strip()
        link = it.get("link") or ""
        source = (it.get("source") or "").strip()
        if not title or not link:
            continue
        key = (source.lower(), title.lower()[:40])
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "title": title[:70],
            "source": source or urllib.parse.urlparse(link).netloc.replace("www.", ""),
            "link": link,
            "thumbnail": it.get("thumbnail") or it.get("original_thumbnail"),
            "price": it.get("price"),
            "exact": it.get("type") == "exact_match",
        })
        if len(out) >= limit:
            break
    return out


def search_bytes(raw: bytes):
    return lens_search(upload_image(raw))


def search_data_url(data_url: str):
    """Accept a browser FileReader data: URL."""
    if "," in data_url and data_url.startswith("data:"):
        head, b64 = data_url.split(",", 1)
        ctype = head.split(";")[0][5:] or "image/jpeg"
        return lens_search(upload_image(base64.b64decode(b64), ctype))
    return lens_search(data_url)  # already a public url


if __name__ == "__main__":
    import sys
    src = sys.argv[1] if len(sys.argv) > 1 else (
        "https://cdn.shopify.com/s/files/1/0035/9828/6912/files/"
        "BimboxBlackJacket_DROP0_1.jpg?v=1786525538")
    for i, m in enumerate(lens_search(src)[:8], 1):
        print(f"{i}. {m['source']:22} {m['title'][:52]}")
        print(f"   {m['link'][:95]}")
