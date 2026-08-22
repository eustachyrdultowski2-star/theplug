#!/usr/bin/env python3
"""Key -> JSON document store.

Two backends behind the same three functions. When DATABASE_URL is set
(Render + Neon) the documents live in Postgres and survive a restart; without
it they are plain JSON files under data/, which is all a laptop needs.
"""
import json, os, threading

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
_lock = threading.Lock()

DB_URL = (os.environ.get("DATABASE_URL") or "").strip()


# --------------------------------------------------------------- Postgres ---
if DB_URL:
    import psycopg
    from psycopg.types.json import Json

    _conn = None

    def _fresh():
        conn = psycopg.connect(DB_URL, autocommit=True, connect_timeout=15)
        with conn.cursor() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS kv (
                             name    text PRIMARY KEY,
                             value   jsonb NOT NULL,
                             updated timestamptz NOT NULL DEFAULT now())""")
        return conn

    def _run(fn):
        """One database call, holding the lock, reconnecting if the socket died.

        Neon closes idle connections and Render puts the whole process to
        sleep, so a dead connection is normal rather than exceptional."""
        global _conn
        with _lock:
            for attempt in (1, 2):
                try:
                    if _conn is None or _conn.closed:
                        _conn = _fresh()
                    return fn(_conn)
                except (psycopg.OperationalError, psycopg.InterfaceError):
                    try:
                        _conn.close()
                    except Exception:
                        pass
                    _conn = None
                    if attempt == 2:
                        raise

    def load(name, default):
        def go(conn):
            with conn.cursor() as c:
                c.execute("SELECT value FROM kv WHERE name = %s", (name,))
                row = c.fetchone()
            return default if row is None else row[0]
        return _run(go)

    def save(name, value):
        def go(conn):
            with conn.cursor() as c:
                c.execute("""INSERT INTO kv (name, value) VALUES (%s, %s)
                             ON CONFLICT (name)
                             DO UPDATE SET value = EXCLUDED.value, updated = now()""",
                          (name, Json(value)))
            return value
        return _run(go)

    def update(name, default, fn):
        """Read-modify-write inside one transaction, so two requests landing at
        the same moment cannot overwrite each other."""
        def go(conn):
            with conn.transaction(), conn.cursor() as c:
                c.execute("SELECT value FROM kv WHERE name = %s FOR UPDATE", (name,))
                row = c.fetchone()
                new = fn(default if row is None else row[0])
                c.execute("""INSERT INTO kv (name, value) VALUES (%s, %s)
                             ON CONFLICT (name)
                             DO UPDATE SET value = EXCLUDED.value, updated = now()""",
                          (name, Json(new)))
            return new
        return _run(go)


# ------------------------------------------------------------- JSON files ---
else:
    os.makedirs(DATA, exist_ok=True)

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


BACKEND = "postgres" if DB_URL else "json-files"
