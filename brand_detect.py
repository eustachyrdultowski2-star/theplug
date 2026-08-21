#!/usr/bin/env python3
"""
The Plug — brand detector (text layer)
--------------------------------------
Given the TEXT around a TikTok/Reel (caption, hashtags, @mentions, comments and
creator replies), guess which clothing BRAND it is — fast, cheap, no computer vision.

Two layers:
  1) FETCH  — turn a URL into a text bundle. `fetch_oembed()` is real & free
              (caption/author only). Full comments need a paid provider — see
              `fetch_bundle()` seam.
  2) ANALYZE — `detect_brand()` scores candidates from the text and returns
              ranked guesses with confidence + human-readable evidence.

Run:  py brand_detect.py           # demo on built-in sample TikToks
      py brand_detect.py <ttURL>   # real oEmbed caption analysis (no comments)
"""

import re, os, json, sys, urllib.parse, urllib.request
try:
    sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1250
except Exception:
    pass

def load_dotenv():
    """Read KEY=VALUE lines from a local `.env` next to this script into env.
    Keeps your secret in a local file — never in the code or the chat."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

load_dotenv()

# --------------------------------------------------------------------------
# Known-brand dictionary. Indie IG brands live here too — but the detector
# also surfaces UNKNOWN @handles as candidates, which is how we catch tiny
# brands that aren't in any list yet.
# --------------------------------------------------------------------------
BRAND_DB = [
    {"name": "Maison North",        "handles": ["maisonnorthofficial", "maisonnorth"], "aliases": ["maison north"], "indie": True},
    {"name": "Society de Nobodies", "handles": ["society.de.nobodies"],                 "aliases": ["society de nobodies", "nobodies"], "indie": True},
    {"name": "Corteiz",             "handles": ["corteiz", "crtz"],                     "aliases": ["corteiz", "crtz", "4starz"], "indie": False},
    {"name": "Aimé Leon Dore",      "handles": ["aimeleondore"],                        "aliases": ["aime leon dore", "ald"], "indie": False},
    {"name": "Salomon",             "handles": ["salomon"],                             "aliases": ["salomon", "xt-6", "xt6"], "indie": False},
    {"name": "Stone Island",        "handles": ["stoneisland"],                         "aliases": ["stone island"], "indie": False},
    {"name": "Arc'teryx",           "handles": ["arcteryx"],                            "aliases": ["arcteryx", "arc'teryx", "beta lt"], "indie": False},
    {"name": "Acne Studios",        "handles": ["acnestudiosofficial", "acnestudios"],  "aliases": ["acne studios", "acne"], "indie": False},
    {"name": "Zara",                "handles": ["zara"],                                "aliases": ["zara"], "indie": False},
    {"name": "Uniqlo",              "handles": ["uniqlo"],                              "aliases": ["uniqlo"], "indie": False},
    {"name": "Carhartt",            "handles": ["carhartt", "carharttwip"],             "aliases": ["carhartt"], "indie": False},
    {"name": "Levi's",              "handles": ["levis"],                               "aliases": ["levis", "levi's"], "indie": False},
    {"name": "Our Legacy",          "handles": ["ourlegacy"],                           "aliases": ["our legacy"], "indie": False},
]

# question phrases that mean "where is this from?" (EN + PL)
QUESTION_HINTS = [
    "where", "link", "brand", "id on", "sauce", "plug", "where's", "where is",
    "who makes", "what brand", "drop the", "name of", "deadass where",
    "skąd", "gdzie kupić", "gdzie mogę", "jaka marka", "co to za", "link do",
]

# handle fragments that scream "this is a shop, not a friend"
BRAND_KEYWORDS = [
    "fashion", "official", "store", "shop", "brand", "wear", "clothing",
    "apparel", "atelier", "studio", "label", "boutique", "garment", "threads",
    "clo", "thelabel", "wardrobe", "collective", "archive", "goods", "supply",
    "mode", "gallery", "denim", "jeans", "worldwide", "paris", "milano", "nyc",
]

# a mention followed by words like these is naming the actual product
PRODUCT_RE = re.compile(
    r"@[a-zA-Z0-9._$&+\-]{2,30}\s+(.{4,60}?(?:jeans?|pants?|trousers?|hoodie|tee|"
    r"shirt|jacket|coat|knit|sweater|cap|shorts|boots?|shoes?|bag)\b)",
    re.I)

# Handles can be stylised: @A$APMODE, @off-white, @c&s. Allow those characters,
# then trim trailing punctuation. A plain [a-zA-Z0-9._] class silently dropped
# "@A$APMODE" down to "@A" and lost the brand entirely.
MENTION_RE = re.compile(r"@([a-zA-Z0-9._$&+\-]{2,30})")

def clean_handle(h: str) -> str:
    """Strip trailing punctuation a mention often collects."""
    return h.rstrip("._-+&$") or h

def handle_key(h: str) -> str:
    """Comparison key: $ reads as S, drop separators (A$APMODE == asapmode)."""
    return re.sub(r"[._\-+&]", "", h.lower().replace("$", "s"))
HASHTAG_RE = re.compile(r"#([a-zA-Z0-9_]{2,40})")
URL_RE     = re.compile(r"https?://[^\s]+")


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").lower()).strip()


def looks_brandy(handle: str) -> bool:
    h = handle.lower()
    return any(kw in h for kw in BRAND_KEYWORDS)


def match_known(token: str):
    """Return a BRAND_DB entry if token (handle/alias) matches a known brand."""
    t = token.lower().lstrip("@#").replace(" ", "")
    for b in BRAND_DB:
        for h in b["handles"]:
            if t == h.replace(".", "").replace("_", "") or t == h:
                return b
        for a in b["aliases"]:
            if norm(a).replace(" ", "") in t or t in norm(a).replace(" ", ""):
                if len(t) >= 4:
                    return b
    return None


def detect_brand(bundle: dict) -> dict:
    """
    bundle = {
      "caption": str,
      "comments": [ {"author": str, "text": str, "is_creator": bool, "likes": int} ]
    }
    Returns ranked candidates with confidence + evidence.
    """
    caption = bundle.get("caption", "") or ""
    comments = bundle.get("comments", []) or []
    creator = bundle.get("author")  # handle of the video's creator, if known

    # candidate -> {"score": float, "evidence": [str], "handle": str, "known": entry|None}
    cands = {}

    def bump(key, pts, why, handle=None, known=None):
        c = cands.setdefault(key, {"score": 0.0, "evidence": [], "handle": handle, "known": known})
        c["score"] += pts
        c["evidence"].append(why)
        if handle and not c["handle"]:
            c["handle"] = handle
        if known and not c["known"]:
            c["known"] = known

    # ---- 1) caption: mentions + hashtags + known aliases ----
    for m in MENTION_RE.findall(caption):
        known = match_known(m)
        key = known["name"] if known else "@" + m
        bump(key, 6 if known else 4, f"tagged in the caption (@{m})", handle=m, known=known)
    for h in HASHTAG_RE.findall(caption):
        known = match_known(h)
        if known:
            bump(known["name"], 4, f"caption hashtag (#{h})", known=known)
    for b in BRAND_DB:
        for a in b["aliases"]:
            if a in norm(caption):
                bump(b["name"], 4, f"brand name in caption (“{a}”)", known=b)
                break

    # ---- 2) comments ----
    asked = any(any(h in norm(c["text"]) for h in QUESTION_HINTS) for c in comments)

    # Aggregate every @mention across ALL comments first, so consensus (many
    # different people naming the same handle) can outweigh one friend-tag.
    agg = {}  # handle_lower -> data
    for c in comments:
        text = c["text"]
        author = c.get("author") or text[:12]
        is_creator = c.get("is_creator") or (creator and c.get("author") == creator)
        likes = c.get("likes", 0)
        for raw in MENTION_RE.findall(text):
            m = clean_handle(raw)
            if creator and handle_key(m) == handle_key(creator):
                continue  # ignore the creator self-tagging
            if m.lower().lstrip("@") in NOT_BRANDS:
                continue  # friend tags / confirmed non-brands
            d = agg.setdefault(handle_key(m), {
                "handle": m, "authors": set(), "creator": False,
                "brandy": looks_brandy(m), "known": match_known(m),
                "likes": 0, "example": text.strip()[:70],
            })
            d["authors"].add(author)
            d["creator"] = d["creator"] or is_creator
            d["likes"] = max(d["likes"], likes)
            if not d.get("product"):
                pm = PRODUCT_RE.search(text)
                if pm:
                    d["product"] = " ".join(pm.group(1).split())

    for h, d in agg.items():
        n = len(d["authors"])
        name = d["known"]["name"] if d["known"] else "@" + d["handle"]
        # base is deliberately LOW so a lone friend-tag stays near zero
        score = 2.0
        ev = []
        if d["creator"]:
            score += 12; ev.append(f"creator replied with @{d['handle']}")
        if d["brandy"]:
            score += 9;  ev.append(f"handle looks like a brand (@{d['handle']})")
        if d["known"]:
            score += 8
        if n > 1:
            score += min(n - 1, 6) * 4; ev.append(f"named by {n} different people")
        if asked:
            score += 2
        score += min(d["likes"] / 60.0, 4)
        if not ev:
            ev.append(f"mentioned once: “{d['example']}”")
        c0 = cands.setdefault(name, {"score": 0.0, "evidence": [], "handle": d["handle"], "known": d["known"]})
        c0["score"] += score
        c0["evidence"].extend(ev)
        if d.get("product") and not c0.get("product"):
            c0["product"] = d["product"]
            c0["evidence"].append(f"item named: “{d['product']}”")

    # brand names written out without an @, plus shop links
    for c in comments:
        text = c["text"]
        is_creator = c.get("is_creator") or (creator and c.get("author") == creator)
        for b in BRAND_DB:
            for a in b["aliases"]:
                if a in norm(text) and b["handles"][0] not in text.lower():
                    bump(b["name"], 7 if is_creator else 3, f"named in a comment (“{a}”)", known=b)
                    break
        for u in URL_RE.findall(text):
            host = urllib.parse.urlparse(u).netloc.replace("www.", "")
            if host:
                bump(host, 7, f"shop link posted: {host}", handle=host)

    if not cands:
        return {"guess": None, "confidence": 0, "candidates": [], "asked": asked}

    # ---- 3) rank + normalize to a 0-100 confidence ----
    ranked = sorted(cands.items(), key=lambda kv: kv[1]["score"], reverse=True)
    top_score = ranked[0][1]["score"]
    out = []
    for name, c in ranked[:5]:
        conf = round(min(c["score"] / (top_score + 4) * 100, 99))
        out.append({
            "brand": c["known"]["name"] if c["known"] else name,
            "handle": ("@" + c["handle"]) if c["handle"] else None,
            "known": bool(c["known"]),
            "indie": c["known"]["indie"] if c["known"] else True,   # unknown handle => likely indie
            "confidence": conf,
            "product": c.get("product"),
            "evidence": c["evidence"][:3],
        })
    return {"guess": out[0], "confidence": out[0]["confidence"], "candidates": out, "asked": asked}


# --------------------------------------------------------------------------
# Per-garment detection — one video usually hides several questions
# ("where are the jeans from?", "and the belt?", "those boots?"), each with
# its own answer. detect_items() groups the evidence per garment instead of
# collapsing everything into a single guess.
# --------------------------------------------------------------------------
GARMENTS = [
    ("jeans",   ["jeans", "jean", "denim", "bootcut", "baggy", "pants", "trousers",
                 "cargos", "cargo", "joggers", "sweatpants", "shorts", "slacks"]),
    ("shoes",   ["shoes", "shoe", "boots", "boot", "sneakers", "sneaker", "trainers",
                 "loafers", "kicks", "footwear", "mocassins", "moccasins"]),
    ("belt",    ["belt", "belts", "buckle"]),
    ("shirt",   ["shirt", "tee", "t-shirt", "tshirt", "top", "polo", "jersey",
                 "flannel", "flanel", "flanell", "buttonup", "button up", "button-up"]),
    ("jacket",  ["jacket", "coat", "hoodie", "hoody", "zip up", "zip-up", "zipup",
                 "overshirt", "outerwear", "puffer", "parka", "bomber", "vest",
                 "blazer", "trench"]),
    ("knit",    ["sweater", "knit", "jumper", "cardigan", "fleece", "knitwear", "pullover"]),
    ("scarf",   ["scarf", "scarves", "shawl", "snood"]),
    ("hat",     ["cap", "hat", "beanie", "balaclava"]),
    ("bag",     ["bag", "tote", "backpack", "purse", "satchel"]),
    ("glasses", ["glasses", "sunglasses", "shades", "eyewear", "frames"]),
    ("jewelry", ["ring", "necklace", "chain", "bracelet", "earring", "pendant"]),
    ("watch",   ["watch", "watches"]),
]

# words that look like brand answers but are not
NOT_BRANDS = {
    "menes",  # user confirmed: not a brand
    "the", "this", "that", "they", "them", "these", "those", "there", "here",
    "from", "same", "similar", "cheap", "some", "any", "idk", "bro", "fire",
    "amazon", "ebay", "depop", "vinted", "temu", "aliexpress", "shein",
    "thrift", "thrifted", "vintage", "custom", "handmade", "google", "tiktok",
    "loose", "fit", "baggy", "black", "white", "blue", "grey", "gray", "cream",
    "out", "of", "stock", "size", "sizing", "link", "bio", "dm", "comment",
    "someone", "everyone", "anyone", "please", "thanks", "bruh", "man", "guy",
    "company", "brand", "name", "style", "outfit", "fit", "drip", "look",
    "his", "her", "their", "your", "you", "who", "what", "where", "when", "why",
    "and", "with", "for", "not", "but", "все", "one", "two", "way", "got",
    "shop", "store", "place", "site", "website", "which", "how", "much",
    "bought", "buy", "get", "got", "find", "found", "know", "think", "same",
    "second", "hand", "cheap", "expensive", "school", "size", "code", "name",
    "first", "third", "fourth", "fifth", "sixth", "last", "next", "slide",
    "pic", "picture", "photo", "image", "left", "right", "middle", "bro", "gng",
    "is", "are", "was", "were", "be", "do", "does", "did", "can", "could",
    "this", "these", "those", "there", "here", "it", "its", "my", "mine",
    "need", "want", "love", "like", "please", "pls", "help", "tell", "say",
}
# the garment nouns themselves are never the brand ("Are the Jeans please" -> "Jeans")
GARMENT_WORDS = set()

# "they're from X", "it's X", "X jeans", "@X"
FROM_RE = re.compile(r"(?:from|by|it'?s|its|they'?re|thats|that'?s)\s+([A-Za-z][\w'&.\-]{2,24}(?:\s+[A-Z][\w'&.\-]{1,14})?)", re.I)
CAP_RE  = re.compile(r"\b([A-Z][a-zA-Z]{2,}(?:\s+[A-Z][a-zA-Z]{2,})?)\b")


for _c, _ws in GARMENTS:
    GARMENT_WORDS.update(_ws)
    GARMENT_WORDS.add(_c)


# Photo carousels: people ask per slide ("shoes from 2nd slide?", "slide 6 shirt?")
WORD_NUM = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6,
            "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10,
            "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
            "1st": 1, "2nd": 2, "3rd": 3, "4th": 4, "5th": 5, "6th": 6, "7th": 7}
SLIDE_WORDS = r"(?:slide|pic|picture|photo|image|fit|look|outfit)"
SLIDE_PATTERNS = [
    re.compile(SLIDE_WORDS + r"\s*(?:no\.?\s*)?(\d{1,2})\b", re.I),          # slide 4
    re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+" + SLIDE_WORDS, re.I),        # 2nd slide
    re.compile(r"\b(" + "|".join(WORD_NUM) + r")\s+" + SLIDE_WORDS, re.I),    # second slide
    re.compile(SLIDE_WORDS + r"\s+(" + "|".join(WORD_NUM) + r")\b", re.I),    # slide one
]
# "the first pants", "the black pants" -> ordinal without the word "slide"
ORDINAL_ONLY = re.compile(r"\bthe\s+(" + "|".join(WORD_NUM) + r")\s+\w+", re.I)

# promo spam repeated under every fit-check video
SPAM_RE = re.compile(r"(use\s*code|discount|promo|%\s*off|10%|link in bio|dm me)", re.I)


def slide_of(text: str):
    """Which carousel slide is this comment about, if any."""
    for pat in SLIDE_PATTERNS:
        m = pat.search(text or "")
        if m:
            tok = m.group(1).lower()
            n = WORD_NUM.get(tok) or (int(tok) if tok.isdigit() else None)
            if n and 1 <= n <= 20:
                return n
    m = ORDINAL_ONLY.search(text or "")
    if m:
        return WORD_NUM.get(m.group(1).lower())
    return None


def garment_of(text: str):
    """Which garment is this comment about? Returns a category or None."""
    low = norm(text)
    for cat, words in GARMENTS:
        for w in words:
            if re.search(r"\b" + re.escape(w) + r"\b", low):
                return cat
    return None


def brand_candidates(text: str):
    """Pull possible brand names out of a free-text comment."""
    out = []
    for m in MENTION_RE.findall(text):
        out.append((clean_handle(m), 6))            # @handles are the strongest
    for m in FROM_RE.findall(text):
        out.append((m.strip(), 4))                  # "they're from X"
    for b in BRAND_DB:                              # known names, however written
        for a in b["aliases"]:
            if a in norm(text):
                out.append((b["name"], 5))
                break
    for m in CAP_RE.findall(text):                  # capitalised words near a garment
        out.append((m.strip(), 2))

    clean = []
    for name, w in out:
        n = name.strip(" .,:;!?-'\"")
        key = n.lower().lstrip("@")
        parts = key.split()
        if len(n) < 3 or key in NOT_BRANDS or key in GARMENT_WORDS:
            continue
        # drop anything built purely from stop-words / garment nouns
        if all(p in NOT_BRANDS or p in GARMENT_WORDS for p in parts):
            continue
        clean.append((n, w))
    return clean


def detect_items(bundle: dict, min_score: float = 4.0):
    """Return one best brand per garment mentioned in the video."""
    comments = bundle.get("comments", []) or []
    creator = bundle.get("author")
    caption = bundle.get("caption", "") or ""

    # index the thread so a bare answer can borrow its question's garment
    by_cid = {c.get("cid"): c for c in comments if c.get("cid")}

    def inherit(c, fn, depth=0):
        """This comment's own value, else the value of the question it answers."""
        own = fn(c.get("text", ""))
        if own:
            return own
        parent = by_cid.get(c.get("parent"))
        if parent is not None and depth < 3:
            return inherit(parent, fn, depth + 1)
        return None

    # promo bots post the same line under every video — never an answer
    text_counts = {}
    for c in comments:
        k = norm(c.get("text", ""))[:40]
        text_counts[k] = text_counts.get(k, 0) + 1

    per = {}   # (slide, garment) -> {brandKey: {...}}
    for c in comments:
        text = c.get("text", "")
        if SPAM_RE.search(text) or text_counts.get(norm(text)[:40], 0) >= 3:
            continue
        cat = inherit(c, garment_of)
        if not cat:
            continue
        slide = inherit(c, slide_of)
        is_creator = c.get("is_creator") or (creator and c.get("author") == creator)
        likes = c.get("likes", 0) or 0
        asking = any(h in norm(text) for h in QUESTION_HINTS) and not brand_candidates(text)
        if asking:
            per.setdefault((slide, cat), {})     # register the question itself
            continue
        for name, weight in brand_candidates(text):
            if creator and handle_key(name) == handle_key(creator):
                continue
            key = handle_key(name)
            bucket = per.setdefault((slide, cat), {})
            # merge near-duplicates: "A$APMODE" / "APMODE" / "asapmode"
            for existing in list(bucket):
                if key != existing and (key in existing or existing in key) and min(len(key), len(existing)) >= 5:
                    key = existing if len(existing) >= len(key) else key
                    break
            slot = bucket.setdefault(
                key, {"name": name.lstrip("@"), "score": 0.0, "evidence": [],
                      "voices": set(), "mentioned": False})
            # weight 6 means it came from a real @handle, not free text
            if weight >= 6 or name.startswith("@"):
                slot["mentioned"] = True
            score = weight
            if is_creator:
                score += 8
            if looks_brandy(name):
                score += 4
            score += min(likes / 60.0, 4)
            slot["score"] += score
            slot["voices"].add(c.get("author") or text[:10])
            who = "creator" if is_creator else "commenter"
            slot["evidence"].append(f"{who}: “{' '.join(text.split())[:64]}”")

    results = []
    for (slide, cat), brands in per.items():
        if not brands:
            continue
        best_key, best = max(brands.items(), key=lambda kv: kv[1]["score"])
        if len(best["voices"]) > 1:
            best["score"] += 5                    # more than one person said it
        if best["score"] < min_score:
            continue
        top = max(b["score"] for b in brands.values()) + 4
        results.append({
            "category": cat,
            "slide": slide,
            "brand": best["name"],
            # only claim a profile when somebody actually @-tagged it —
            # guessing instagram.com/<name> sends people to a random stranger
            "handle": ("@" + handle_key(best["name"])) if best.get("mentioned") else None,
            "verified_handle": bool(best.get("mentioned")),
            "confidence": round(min(best["score"] / top * 100, 99)),
            "evidence": best["evidence"][:2],
            # only surface alternatives that are actually plausible
            "alternatives": [b["name"] for k, b in
                             sorted(brands.items(), key=lambda kv: -kv[1]["score"])[1:4]
                             if b["score"] >= max(min_score, best["score"] * 0.45)][:2],
        })
    # slide order first (unattributed pieces last), then confidence
    results.sort(key=lambda r: (r["slide"] if r["slide"] else 99, -r["confidence"]))
    return results


# --------------------------------------------------------------------------
# FETCH layer
# --------------------------------------------------------------------------
def resolve_short(url: str) -> str:
    """vm.tiktok.com/XXXX -> the full /@user/video/123 url, so oEmbed can
    report the author (without it every reply looks like a stranger's)."""
    if not re.search(r"(vm|vt)\.tiktok\.com", url):
        return url
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.geturl() or url
    except Exception:
        return url


def fetch_oembed(url: str) -> dict:
    """Real & free: TikTok oEmbed gives caption(title)+author, NOT comments."""
    url = resolve_short(url)
    api = "https://www.tiktok.com/oembed?url=" + urllib.parse.quote(url, safe="")
    req = urllib.request.Request(api, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as r:
        data = json.load(r)
    author = data.get("author_unique_id")
    if not author:                       # photo posts often omit it — take it from the url
        m = re.search(r"tiktok\.com/@([A-Za-z0-9._]+)/", url)
        author = m.group(1) if m else None
    return {"caption": data.get("title", ""), "author": author, "comments": []}


# ---- Apify provider (comments) --------------------------------------------
# Setup (you do this once, I can't create the account for you):
#   1. Sign up at apify.com  →  Settings → Integrations → copy your API token
#   2. In Apify Store pick a "TikTok Comments Scraper" actor, copy its slug
#      (e.g. clockworks/tiktok-comments-scraper) and confirm its input field
#      names + output field names on the actor's page.
#   3. Set env vars before running:
#        setx APIFY_TOKEN "apify_api_xxx"        (Windows, new shell after)
#        setx APIFY_ACTOR "clockworks~tiktok-comments-scraper"
# The actor slug uses "~" (not "/") inside the API path.
APIFY_ACTOR = os.environ.get("APIFY_ACTOR", "clockworks~tiktok-comments-scraper")

def _g(d, *keys, default=None):
    for k in keys:
        if isinstance(d, dict) and d.get(k) not in (None, ""):
            return d[k]
    return default

def fetch_apify(url: str, max_comments: int = 100) -> dict:
    token = os.environ.get("APIFY_TOKEN")
    if not token:
        raise RuntimeError("APIFY_TOKEN not set")
    api = (f"https://api.apify.com/v2/acts/{APIFY_ACTOR}"
           f"/run-sync-get-dataset-items?token={urllib.parse.quote(token)}")
    # Common input keys across TikTok-comment actors; extras are usually ignored.
    payload = json.dumps({
        "postURLs": [url], "startUrls": [{"url": url}],
        "commentsPerPost": max_comments, "maxComments": max_comments,
        "maxRepliesPerComment": 10, "repliesPerComment": 10,  # creator answers live in replies
    }).encode()
    req = urllib.request.Request(api, data=payload,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        items = json.load(r)

    # caption + creator handle come cleanest from oEmbed; merge them in.
    try:
        meta = fetch_oembed(url)
    except Exception:
        meta = {"caption": "", "author": None}

    comments = []
    for it in items:
        text = _g(it, "text", "comment", "commentText", default="")
        if not text:
            continue
        author = _g(it, "uniqueId", "username", "user", "authorMeta", "nickname")
        if isinstance(author, dict):
            author = _g(author, "name", "uniqueId", "nickName")
        comments.append({
            "author": author,
            "text": text,
            "likes": int(_g(it, "diggCount", "likes", "likeCount", default=0) or 0),
            "is_creator": bool(author) and author == meta.get("author"),
            # thread structure: a creator's answer is usually a bare "Zara" that
            # only makes sense next to the question it replies to
            "cid": _g(it, "cid", "id", "commentId"),
            "parent": _g(it, "repliesToId", "replyToId", "parentId"),
        })
    return {"caption": meta.get("caption", ""), "author": meta.get("author"),
            "comments": comments}


import hashlib
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")

def _cache_path(url):
    return os.path.join(CACHE_DIR, hashlib.sha1(url.encode()).hexdigest() + ".json")

def fetch_bundle(url: str, use_cache: bool = True) -> dict:
    """Use Apify (full comments) when APIFY_TOKEN is set, else free oEmbed.
    Caches the fetched comments locally so re-runs of the same video cost $0 —
    this is the 'pay once per video, ever' database flywheel."""
    cp = _cache_path(url)
    if use_cache and os.path.exists(cp):
        with open(cp, encoding="utf-8") as f:
            b = json.load(f)
        b["_cached"] = True
        return b
    if os.environ.get("APIFY_TOKEN"):
        try:
            b = fetch_apify(url)
        except Exception as e:
            print(f"[apify failed: {e} — falling back to oEmbed caption]")
            b = fetch_oembed(url)
    else:
        b = fetch_oembed(url)
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(cp, "w", encoding="utf-8") as f:
            json.dump(b, f, ensure_ascii=False)
    except Exception:
        pass
    return b


# --------------------------------------------------------------------------
# Demo
# --------------------------------------------------------------------------
SAMPLES = [
    {
        "label": "Creator answers in comments (the common case)",
        "bundle": {
            "author": "fitgrails",
            "caption": "okay this coat changed my whole winter 🧥 #ootd #menswear",
            "comments": [
                {"author": "user_223", "text": "bro where is the coat from?? need it", "likes": 340},
                {"author": "fitgrails", "text": "@maisonnorthofficial the boxy wool one 🙌", "is_creator": True, "likes": 512},
                {"author": "drip_ana", "text": "so clean, saving this", "likes": 12},
            ],
        },
    },
    {
        "label": "Answer is a bare handle NOT in our database (indie catch)",
        "bundle": {
            "author": "streetnoise",
            "caption": "heavyweight tee season ☁️",
            "comments": [
                {"author": "k.owalski", "text": "skąd ta koszulka?? gdzie kupić", "likes": 88},
                {"author": "someone", "text": "@society.de.nobodies washed heavy tee", "likes": 140},
                {"author": "someone2", "text": "yeah it's society de nobodies", "likes": 60},
            ],
        },
    },
    {
        "label": "Everything is already in the caption",
        "bundle": {
            "author": "gorptrekker",
            "caption": "beta lt in black is unmatched @arcteryx #arcteryx #gorpcore",
            "comments": [{"author": "x", "text": "grail", "likes": 3}],
        },
    },
]


def show(res):
    if not res["guess"]:
        print("   → no brand signal in the text (fall back to visual search)\n")
        return
    g = res["guess"]
    tag = "indie" if g["indie"] else "known brand"
    print(f"   → BEST GUESS: {g['brand']}  ({g['confidence']}% · {tag})")
    if g["handle"]:
        print(f"     handle: {g['handle']}")
    for e in g["evidence"]:
        print(f"     • {e}")
    if len(res["candidates"]) > 1:
        others = ", ".join(f"{c['brand']} {c['confidence']}%" for c in res["candidates"][1:])
        print(f"     other candidates: {others}")
    print()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        url = sys.argv[1]
        print(f"\nFetching: {url}")
        print("APIFY_TOKEN detected:", bool(os.environ.get("APIFY_TOKEN")))
        try:
            b = fetch_bundle(url)
            print("source:", "cache ($0)" if b.get("_cached") else "Apify (paid)")
            print("comments fetched:", len(b.get("comments", [])))
            print("caption:", (b["caption"][:120] or "(empty)"))
            show(detect_brand(b))
        except Exception as e:
            print("fetch failed:", e)
    else:
        print("\n=== The Plug · brand detector — demo ===\n")
        for s in SAMPLES:
            print("•", s["label"])
            show(detect_brand(s["bundle"]))
