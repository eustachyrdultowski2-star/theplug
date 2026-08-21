#!/usr/bin/env python3
"""The Plug — dev server: serves the static site AND a /api/detect endpoint
that runs the brand detector (Apify comments -> brand guess)."""
import http.server, socketserver, json, os
import time
import brand_detect
import image_search
import store

PORT = 4190
DIR = os.path.dirname(os.path.abspath(__file__))


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=DIR, **k)

    def do_GET(self):
        if self.path.startswith("/api/"):
            name = self.path.split("?")[0]
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
                             "/api/subscribe", "/api/score"):
            return self._json(404, {"error": "not found"})
        try:
            n = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(n) or b"{}")
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
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    os.chdir(DIR)
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(("", PORT), Handler) as httpd:
        print(f"The Plug dev server -> http://localhost:{PORT}  (POST /api/detect)")
        httpd.serve_forever()
