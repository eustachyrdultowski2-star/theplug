#!/usr/bin/env python3
"""Tiny JSON store. A prototype does not need a database, but it does need
the data to survive a restart."""
import json, os, threading

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
os.makedirs(DATA, exist_ok=True)
_lock = threading.Lock()


def _path(name):
    return os.path.join(DATA, name + ".json")


def load(name, default):
    try:
        with open(_path(name), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save(name, value):
    with _lock:
        tmp = _path(name) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(value, f, ensure_ascii=False, indent=1)
        os.replace(tmp, _path(name))
    return value


def update(name, default, fn):
    """Read-modify-write under one lock."""
    with _lock:
        try:
            with open(_path(name), encoding="utf-8") as f:
                cur = json.load(f)
        except Exception:
            cur = default
        new = fn(cur)
        tmp = _path(name) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(new, f, ensure_ascii=False, indent=1)
        os.replace(tmp, _path(name))
        return new
