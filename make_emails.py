#!/usr/bin/env python3
"""Turn outreach_list.csv into ready-to-send drafts.

Writes .eml files you can double-click (they open in your mail client already
addressed and filled in) plus a plain-text file for copy-paste.
Nothing is sent from here.
"""
import csv, os, re, sys
from email.message import EmailMessage

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "emails")
os.makedirs(OUT, exist_ok=True)

SITE   = os.environ.get("PLUG_SITE", "https://theplug.app")   # change when live
SENDER = os.environ.get("PLUG_FROM", "eustachyrdultowski2@gmail.com")
NAME   = os.environ.get("PLUG_NAME", "Eustachy")

SUBJECT = "Sending you traffic from TikTok — affiliate link?"

BODY = """Hi {brand} team,

I built The Plug, a search engine for clothes people spot in TikToks and reels.
Someone pastes a link, we read the comments, work out which brand each piece is,
and send them straight to the shop. We currently index 548 brands and 2,100+ products.

{brand} is already listed{piece_line} — here's your page:
{page}

Everything links back to your own site. There's no listing fee and we don't sell
anything ourselves.

Two quick questions:

1. Do you run an affiliate or referral programme I could join? If not, would you
   be open to a simple tracked link with a % on what we send you?
2. Is anything wrong on your listing — wrong pieces, old prices, photos you'd
   rather we didn't use? I'll fix it the same day.

If affiliate isn't for you, no problem, the listing stays either way.

Best,
{name}
{site}
"""

def slugfile(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40]

def main(limit=30):
    rows = list(csv.DictReader(open(os.path.join(HERE, "outreach_list.csv"), encoding="utf-8-sig")))
    rows = [r for r in rows if int(r["products"] or 0) > 0][:limit]

    txt = []
    for r in rows:
        piece = (r.get("piece") or "").strip()
        piece_line = f", including your {piece}" if piece else ""
        body = BODY.format(brand=r["brand"], piece_line=piece_line,
                           page=SITE + r["brand_page"], name=NAME, site=SITE)

        m = EmailMessage()
        m["To"] = r["email"]; m["From"] = SENDER
        m["Subject"] = SUBJECT
        m.set_content(body)
        with open(os.path.join(OUT, f"{slugfile(r['brand'])}.eml"), "wb") as f:
            f.write(bytes(m))

        txt.append(f"=== {r['brand']}  <{r['email']}>\nSubject: {SUBJECT}\n\n{body}\n")

    with open(os.path.join(HERE, "emails_preview.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(txt))

    print(f"drafts written : {len(rows)}  -> spotd/emails/*.eml")
    print(f"preview        : spotd/emails_preview.txt")
    print(f"from           : {SENDER}")
    print(f"site used      : {SITE}  (set PLUG_SITE to change)")

if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 30)
