#!/usr/bin/env python3
"""Collect just the public files into dist/ — ready to drag onto a host.
Anything secret (.env, scraped contacts, watch data) is left behind."""
import json, os, re, shutil, sys, time
sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(HERE, "dist")
API  = os.environ.get("PLUG_API", "")            # e.g. https://theplug-api.onrender.com
# theplug.co belongs to somebody else; the sitemap pointed at their site.
SITE = os.environ.get(
    "PLUG_SITE", "https://theplug.plugfinds.workers.dev").rstrip("/")
BEACON = os.environ.get("PLUG_ANALYTICS", "")   # Cloudflare Web Analytics token

FILES = ["index.html", "manifest.webmanifest", "sw.js"]
DIRS  = ["assets"]

if os.path.isdir(DIST):
    shutil.rmtree(DIST)
os.makedirs(DIST)

for f in FILES:
    shutil.copy2(os.path.join(HERE, f), DIST)

for d in DIRS:
    shutil.copytree(os.path.join(HERE, d), os.path.join(DIST, d))

# Analytics is added at build time, so nothing is tracked while developing.
# Cloudflare Web Analytics sets no cookies, which is why it needs no consent
# banner.
if BEACON:
    page = os.path.join(DIST, "index.html")
    html = open(page, encoding="utf-8").read()
    beacon_cfg = '{"token": "' + BEACON + '"}'
    tag = ('<script defer src="https://static.cloudflareinsights.com/beacon.min.js" '
           "data-cf-beacon='" + beacon_cfg + "'></script>" + chr(10) + "</body>")
    html = html.replace("</body>", tag, 1)
    open(page, "w", encoding="utf-8").write(html)

# No _redirects file on purpose.
#
# Cloudflare rejects the whole file if a proxy rule points at an external
# address, and it does not need one: worker.js passes /api/* through to the
# API, and wrangler.jsonc turns every unmatched path into index.html so the
# client-side router can take it from there.
shutil.copy2(os.path.join(HERE, "_headers"), DIST)

# The worker keeps the shell in a named cache and never looks at it again, so
# a returning visitor kept the catalog they first downloaded. Stamp the cache
# name with this build and every deploy retires the old one.
sw = os.path.join(DIST, "sw.js")
if os.path.exists(sw):
    src = open(sw, encoding="utf-8").read()
    stamp = time.strftime("%Y%m%d%H%M%S")
    src = src.replace('const CACHE = "plug-v1";', 'const CACHE = "plug-' + stamp + '";', 1)
    open(sw, "w", encoding="utf-8").write(src)
    print("shell cache:", "plug-" + stamp)

# Search engines get a map of every public route. Brand pages are the whole
# point of the catalog being public, so all of them go in.
def slugify(name):
    out = "".join(c if c.isalnum() else "-" for c in (name or "").lower())
    while "--" in out:
        out = out.replace("--", "-")
    return out.strip("-")


js = open(os.path.join(HERE, "assets", "js", "catalog.js"), encoding="utf-8").read()
brands = json.loads(re.search(r"^const BRANDS=(.*);$", js, re.M).group(1))
routes = ["/", "/feed", "/saved", "/help-id"]
routes += ["/brand/" + slugify(b["brand"]) for b in brands]

NL = chr(10)
lines = ['<?xml version="1.0" encoding="UTF-8"?>',
         '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
lines += ["  <url><loc>" + SITE + r + "</loc></url>" for r in routes]
lines += ["</urlset>", ""]
open(os.path.join(DIST, "sitemap.xml"), "w", encoding="utf-8").write(NL.join(lines))
open(os.path.join(DIST, "robots.txt"), "w", encoding="utf-8").write(
    NL.join(["User-agent: *", "Allow: /", "Disallow: /admin", "",
             "Sitemap: " + SITE + "/sitemap.xml", ""]))

# A half-finished build once shipped without any images. Never again:
# check the essentials before calling it done.
missing = [need for need in ("index.html", "assets/js/catalog.js", "assets/icons/icon-512.png")
           if not os.path.exists(os.path.join(DIST, need))]
photos = len(os.listdir(os.path.join(DIST, "assets", "photos")))          if os.path.isdir(os.path.join(DIST, "assets", "photos")) else 0
if missing or photos == 0:
    raise SystemExit(f"BUILD INCOMPLETE — missing {missing or 'photos'}; dist not usable")

size = sum(os.path.getsize(os.path.join(r, f))
           for r, _, fs in os.walk(DIST) for f in fs)
n = sum(len(fs) for _, _, fs in os.walk(DIST))
print(f"dist/ ready — {n} files, {size//1024} KB")
print("api       :", API or "(worker.js proxies /api to Render)")
print("analytics :", (BEACON[:8] + "…") if BEACON else "(none set — PLUG_ANALYTICS)")
print("site      :", SITE, "(" + str(len(routes)) + " routes in sitemap.xml)")
print(chr(10) + "next: commit and push — Cloudflare publishes dist/ by itself")
