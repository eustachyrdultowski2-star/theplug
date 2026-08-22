#!/usr/bin/env python3
"""The Plug — dev server: serves the static site AND a /api/detect endpoint
that runs the brand detector (Apify comments -> brand guess)."""
import http.server, socketserver, json, os
import time
import brand_detect
import image_search
import hmac, time as _t
import store
import auth

PORT = int(os.environ.get("PORT", 4190))   # hosts assign the port
DIR = os.path.dirname(os.path.abspath(__file__))


def admin_stats():
    """Everything the owner might want to know, read straight off the store."""
    users   = store.load("users", [])
    saved   = store.load("saved", {})
    watches = store.load("watches", [])
    alerts  = store.load("alerts", [])
    subs    = store.load("subscribers", [])
    board   = store.load("leaderboard", [])
    now     = _t.time()

    def since(days):
        return sum(1 for u in users if u.get("created", 0) > now - days * 86400)

    # which pieces get saved the most
    counts = {}
    for ids in saved.values():
        for i in ids:
            counts[i] = counts.get(i, 0) + 1
    top = sorted(counts.items(), key=lambda kv: -kv[1])[:10]

    return {
        "users":       {"total": len(users), "last7": since(7), "last30": since(30),
                        "plus": sum(1 for u in users if u.get("plus"))},
        "saved":       {"people": len([k for k, v in saved.items() if v]),
                        "pieces": sum(len(v) for v in saved.values()),
                        "top": [{"id": i, "n": n} for i, n in top]},
        "watches":     len(watches),
        "alerts":      len(alerts),
        "subscribers": len(subs),
        "spotters":    sorted(board, key=lambda r: -r.get("points", 0))[:10],
        "recent":      [{"email": u["email"], "created": u.get("created")}
                        for u in sorted(users, key=lambda u: -u.get("created", 0))[:10]],
        "storage":     store.BACKEND,   # "postgres" = accounts survive a deploy
    }


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        self._extra_headers = []      # per request, never shared between users
        super().__init__(*a, directory=DIR, **k)

    # ---------- helpers ----------
    def _token(self):
        raw = self.headers.get("Cookie") or ""
        for part in raw.split(";"):
            k, _, v = part.strip().partition("=")
            if k == "plug_session":
                return v
        return None

    def _me(self):
        return auth.session_user(self._token())

    def _set_cookie(self, token, clear=False):
        attrs = "Path=/; HttpOnly; SameSite=Lax"
        if clear:
            self._extra_headers.append(("Set-Cookie", f"plug_session=; Max-Age=0; {attrs}"))
        else:
            self._extra_headers.append(
                ("Set-Cookie", f"plug_session={token}; Max-Age={60*60*24*60}; {attrs}"))

    def do_GET(self):
        if self.path.startswith("/api/"):
            name = self.path.split("?")[0]
            if name.startswith("/api/admin/stats"):
                # Render's value box is a textarea, so a stray newline is easy
                key = (os.environ.get("ADMIN_KEY") or "").strip()
                if not key:
                    return self._json(404, {"error": "admin_disabled"})
                given = ""
                if "?" in self.path:
                    from urllib.parse import parse_qs
                    given = (parse_qs(self.path.split("?", 1)[1]).get("key") or [""])[0]
                if not hmac.compare_digest(given.strip(), key):
                    return self._json(401, {"error": "bad_key"})
                return self._json(200, admin_stats())

            if name == "/api/config":
                return self._json(200, {"googleClientId":
                                        (os.environ.get("GOOGLE_CLIENT_ID") or "").strip()})

            if name == "/api/me":
                me = self._me()
                return self._json(200, {"user": me,
                                        "saved": auth.saved_ids(me["id"]) if me else []})
            if name == "/api/alerts":
                return self._json(200, {"alerts": store.load("alerts", [])[::-1][:40],
                                        "watches": store.load("watches", [])})
            if name == "/api/leaderboard":
                rows = sorted(store.load("leaderboard", []), key=lambda r: -r["points"])
                return self._json(200, {"board": rows[:20]})
            return self._json(404, {"error": "not found"})
        """Client-side routes (/feed, /brand/x, /item/1) have no file on disk —
        hand them index.html and let the router take over."""
        path = self.path.split("?")[0]
        real = os.path.join(DIR, path.lstrip("/").replace("/", os.sep))
        if path != "/" and not os.path.exists(real) and not path.startswith("/api"):
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        if self.path not in ("/api/detect", "/api/image", "/api/watch",
                             "/api/subscribe", "/api/score",
                             "/api/auth/register", "/api/auth/login",
                             "/api/auth/logout", "/api/save", "/api/auth/google"):
            return self._json(404, {"error": "not found"})
        try:
            n = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(n) or b"{}")
            if self.path == "/api/auth/register":
                user, err = auth.register(body.get("email"), body.get("password"))
                if err:
                    return self._json(400, {"error": err})
                self._set_cookie(auth.open_session(user["id"]))
                return self._json(200, {"user": user, "saved": []})

            if self.path == "/api/auth/login":
                user, err = auth.login(body.get("email"), body.get("password"))
                if err:
                    return self._json(401, {"error": err})
                self._set_cookie(auth.open_session(user["id"]))
                return self._json(200, {"user": user, "saved": auth.saved_ids(user["id"])})

            if self.path == "/api/auth/google":
                user, err = auth.google_login(body.get("credential"))
                if err:
                    return self._json(401, {"error": err})
                self._set_cookie(auth.open_session(user["id"]))
                return self._json(200, {"user": user, "saved": auth.saved_ids(user["id"])})

            if self.path == "/api/auth/logout":
                auth.close_session(self._token())
                self._set_cookie(None, clear=True)
                return self._json(200, {"ok": True})

            if self.path == "/api/save":
                me = self._me()
                if not me:
                    return self._json(401, {"error": "sign_in_required"})
                ids = auth.toggle_saved(me["id"], body.get("id"), bool(body.get("on", True)))
                return self._json(200, {"saved": ids})

            if self.path == "/api/watch":          # follow a piece for restock / price drops
                item = body.get("item") or {}
                on = bool(body.get("on", True))
                def upd(ws):
                    ws = [w for w in ws if str(w.get("id")) != str(item.get("id"))]
                    if on:
                        ws.append({**item, "at": int(time.time())})
                    return ws
                ws = store.update("watches", [], upd)
                return self._json(200, {"watching": on, "count": len(ws)})

            if self.path == "/api/subscribe":      # weekly drop mailing list
                email = (body.get("email") or "").strip()
                if "@" not in email or "." not in email:
                    return self._json(400, {"error": "bad_email"})
                def add(subs):
                    if email.lower() not in [s.lower() for s in subs]:
                        subs.append(email)
                    return subs
                subs = store.update("subscribers", [], add)
                return self._json(200, {"ok": True, "count": len(subs)})

            if self.path == "/api/score":          # a confirmed ID earns points
                who = (body.get("user") or "you").strip()[:24]
                pts = int(body.get("points") or 1)
                def bump(rows):
                    for r in rows:
                        if r["user"].lower() == who.lower():
                            r["points"] += pts; r["ids"] = r.get("ids", 0) + 1
                            return rows
                    rows.append({"user": who, "points": pts, "ids": 1})
                    return rows
                return self._json(200, {"board": store.update("leaderboard", [], bump)})

            if self.path == "/api/image":
                img = body.get("image") or ""
                if not img:
                    return self._json(400, {"error": "no_image"})
                return self._json(200, {"matches": image_search.search_data_url(img)})
            url = (body.get("url") or "").strip()
            if "tiktok.com" not in url and "instagram.com" not in url:
                return self._json(400, {"error": "bad_url"})
            bundle = brand_detect.fetch_bundle(url)
            res = brand_detect.detect_brand(bundle)
            res["items"] = brand_detect.detect_items(bundle)   # per-garment breakdown
            res["comment_count"] = len(bundle.get("comments", []))
            res["cached"] = bool(bundle.get("_cached"))
            self._json(200, res)
        except Exception as e:
            self._json(500, {"error": str(e)})

    def _json(self, code, obj):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        for k, v in self._extra_headers:
            self.send_header(k, v)
        self._extra_headers = []
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    os.chdir(DIR)
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(("0.0.0.0", PORT), Handler) as httpd:
        print(f"The Plug server on :{PORT}")
        httpd.serve_forever()
