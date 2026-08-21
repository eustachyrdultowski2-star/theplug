#!/usr/bin/env python3
"""Collect just the public files into dist/ — ready to drag onto a host.
Anything secret (.env, scraped contacts, watch data) is left behind."""
import os, shutil, sys
sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(HERE, "dist")
API  = os.environ.get("PLUG_API", "")     # e.g. https://theplug-api.onrender.com

FILES = ["index.html", "manifest.webmanifest", "sw.js"]
DIRS  = ["assets"]

if os.path.isdir(DIST):
    shutil.rmtree(DIST)
os.makedirs(DIST)

for f in FILES:
    shutil.copy2(os.path.join(HERE, f), DIST)
for d in DIRS:
    shutil.copytree(os.path.join(HERE, d), os.path.join(DIST, d))

# client-side routes must fall back to index.html; /api goes to the real server
rules = []
if API:
    rules.append(f"/api/*  {API.rstrip('/')}/api/:splat  200")
rules.append("/*      /index.html                  200")
open(os.path.join(DIST, "_redirects"), "w").write("\n".join(rules) + "\n")

size = sum(os.path.getsize(os.path.join(r, f))
           for r, _, fs in os.walk(DIST) for f in fs)
n = sum(len(fs) for _, _, fs in os.walk(DIST))
print(f"dist/ ready — {n} files, {size//1024} KB")
print("api proxy :", API or "(none set — detection will not work until you set PLUG_API)")
print("\nnext: drag the dist folder onto https://app.netlify.com/drop")
