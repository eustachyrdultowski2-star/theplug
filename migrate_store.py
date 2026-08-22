#!/usr/bin/env python3
"""Copy the local data/*.json documents into Postgres, once.

    DATABASE_URL=postgresql://... py migrate_store.py          # copy, then list
    DATABASE_URL=postgresql://... py migrate_store.py --check   # only list

Existing rows are left alone unless --force is passed, so running this twice
cannot quietly overwrite live data with a stale laptop copy.
"""
import glob, json, os, sys

if not (os.environ.get("DATABASE_URL") or "").strip():
    sys.exit("Set DATABASE_URL first (the connection string from Neon).")

import store   # picks the Postgres backend because DATABASE_URL is set

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
NAMES = ["users", "sessions", "saved", "watches", "alerts", "subscribers", "leaderboard"]


def listing():
    print("\nIn Postgres now:")
    for name in NAMES:
        val = store.load(name, None)
        if val is None:
            print(f"  {name:<12} —")
        else:
            n = len(val) if isinstance(val, (list, dict)) else 1
            print(f"  {name:<12} {n} entries")


if "--check" in sys.argv:
    listing()
    raise SystemExit

force = "--force" in sys.argv
for path in sorted(glob.glob(os.path.join(DATA, "*.json"))):
    name = os.path.splitext(os.path.basename(path))[0]
    try:
        with open(path, encoding="utf-8") as f:
            value = json.load(f)
    except Exception as e:
        print(f"  skip {name}: {e}")
        continue
    if store.load(name, None) is not None and not force:
        print(f"  keep {name}: already in the database (--force to overwrite)")
        continue
    store.save(name, value)
    print(f"  copied {name}")

listing()
