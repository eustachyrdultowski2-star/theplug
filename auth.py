#!/usr/bin/env python3
"""Accounts, sessions and saved items.

Passwords are never stored — only a PBKDF2 hash with a per-user salt.
Sessions are random tokens kept server-side, handed out in an HttpOnly cookie.
"""
import hashlib, hmac, json, os, re, secrets, time, urllib.parse, urllib.request
import store

ITERATIONS = 240_000          # deliberately slow, so a stolen file is not a password list
SESSION_DAYS = 60
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")


# ---------- passwords ----------
def hash_password(password: str, salt: bytes = None) -> str:
    salt = salt or secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    return f"pbkdf2${ITERATIONS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, iters, salt_hex, hash_hex = stored.split("$")
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(),
                                 bytes.fromhex(salt_hex), int(iters))
        return hmac.compare_digest(dk.hex(), hash_hex)     # constant time
    except Exception:
        return False


# ---------- accounts ----------
def _users():
    return store.load("users", [])


def find_user(email: str):
    e = (email or "").strip().lower()
    return next((u for u in _users() if u["email"] == e), None)


def register(email: str, password: str):
    email = (email or "").strip().lower()
    if not EMAIL_RE.match(email):
        return None, "bad_email"
    if len(password or "") < 8:
        return None, "weak_password"          # 8 is the floor, not a suggestion
    if find_user(email):
        return None, "exists"

    user = {
        "id": secrets.token_hex(8),
        "email": email,
        "name": email.split("@")[0][:24],
        "password": hash_password(password),
        "plus": False,
        "shared": False,          # a wardrobe is private until its owner says otherwise
        "created": int(time.time()),
    }
    user["handle"] = free_handle(email.split("@")[0])
    store.update("users", [], lambda us: us + [user])
    return public(user), None


def login(email: str, password: str):
    user = find_user(email)
    # run the hash even when the user is missing, so timing says nothing
    stored = user["password"] if user else hash_password("dummy")
    if not verify_password(password or "", stored) or not user:
        return None, "bad_credentials"
    return public(user), None


def public(user):
    return {"id": user["id"], "email": user["email"],
            "name": user.get("name"), "plus": bool(user.get("plus")),
            "handle": user.get("handle") or handle_for(user),
            "shared": bool(user.get("shared"))}


# ---------- sessions ----------
def open_session(user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    row = {"token": token, "user": user_id,
           "expires": int(time.time()) + SESSION_DAYS * 86400}
    store.update("sessions", [], lambda ss: [s for s in ss if s["expires"] > time.time()] + [row])
    return token


def session_user(token: str):
    if not token:
        return None
    now = time.time()
    row = next((s for s in store.load("sessions", [])
                if s["token"] == token and s["expires"] > now), None)
    if not row:
        return None
    user = next((u for u in _users() if u["id"] == row["user"]), None)
    return public(user) if user else None


def close_session(token: str):
    store.update("sessions", [], lambda ss: [s for s in ss if s["token"] != token])


# ---------- profiles and the wardrobe ----------
HANDLE_RE = re.compile(r"[^a-z0-9_]+")


def clean_handle(raw: str) -> str:
    h = HANDLE_RE.sub("", (raw or "").strip().lower())[:20]
    return h or "plug"


def free_handle(raw: str) -> str:
    """A handle nobody else holds. Two people called jan get jan and jan2."""
    base = clean_handle(raw)
    taken = {u.get("handle") for u in _users()}
    if base not in taken:
        return base
    n = 2
    while f"{base}{n}" in taken:
        n += 1
    return f"{base}{n}"


def handle_for(user):
    return clean_handle(user.get("name") or user.get("email", "").split("@")[0])


def by_handle(handle: str):
    h = clean_handle(handle)
    return next((u for u in _users() if (u.get("handle") or handle_for(u)) == h), None)


def set_profile(user_id: str, shared=None, handle=None, name=None):
    """Rename, re-handle, or flip a wardrobe between private and public."""
    err = [None]

    def upd(users):
        for u in users:
            if u["id"] != user_id:
                continue
            if handle is not None:
                want = clean_handle(handle)
                clash = next((o for o in users
                              if o["id"] != user_id and o.get("handle") == want), None)
                if clash:
                    err[0] = "handle_taken"
                    return users
                u["handle"] = want
            if name is not None:
                u["name"] = name.strip()[:24] or u["name"]
            if shared is not None:
                u["shared"] = bool(shared)
            return users
        err[0] = "no_user"
        return users

    users = store.update("users", [], upd)
    if err[0]:
        return None, err[0]
    user = next((u for u in users if u["id"] == user_id), None)
    return public(user), None


def closet(user_id: str):
    return store.load("closet", {}).get(user_id, [])


def closet_add(user_id: str, item: dict):
    """Anything can land on the shelf: a catalog piece, a link, a Lens match.

    Whatever the source, only these fields are kept — the rest of whatever the
    client sent is dropped rather than stored unread.
    """
    row = {
        "key":   secrets.token_hex(6),
        "title": (item.get("title") or "").strip()[:80],
        "brand": (item.get("brand") or "").strip()[:60],
        "photo": (item.get("photo") or "").strip()[:600],
        "link":  (item.get("link") or "").strip()[:600],
        "price": (item.get("price") or "").strip()[:24],
        "note":  (item.get("note") or "").strip()[:140],
        "at":    int(time.time()),
    }
    if not row["title"] and not row["photo"]:
        return None, "empty"
    for field in ("photo", "link"):
        if row[field] and not row[field].startswith(("http://", "https://")):
            row[field] = ""

    def upd(all_closets):
        shelf = all_closets.get(user_id, [])
        if len(shelf) >= 300:
            shelf = shelf[-299:]          # a shelf, not a warehouse
        all_closets[user_id] = shelf + [row]
        return all_closets

    store.update("closet", {}, upd)
    return row, None


def closet_remove(user_id: str, key: str):
    def upd(all_closets):
        all_closets[user_id] = [r for r in all_closets.get(user_id, [])
                                if r.get("key") != key]
        return all_closets
    store.update("closet", {}, upd)
    return closet(user_id)


def profile_view(handle: str):
    """What a visitor is allowed to see. None when it is private or missing."""
    user = by_handle(handle)
    if not user or not user.get("shared"):
        return None
    return {
        "name":   user.get("name"),
        "handle": user.get("handle") or handle_for(user),
        "since":  user.get("created"),
        "score":  score_row(user["id"]),
        "closet": closet(user["id"]),
        "wishlist": saved_ids(user["id"]),
    }


# ---------- contribution score ----------
# Rows are keyed by account id, not by display name: a name can be changed or
# copied, and the whole point of a rank is that it was earned by one person.
def score_row(user_id: str):
    row = next((r for r in store.load("leaderboard", [])
                if r.get("id") == user_id), None)
    return {"points": row.get("points", 0), "ids": row.get("ids", 0)} if row \
        else {"points": 0, "ids": 0}


def add_score(user_id: str, name: str, points: int):
    def bump(rows):
        for r in rows:
            if r.get("id") == user_id:
                r["points"] = r.get("points", 0) + points
                r["ids"] = r.get("ids", 0) + 1
                r["user"] = name          # keep the display name current
                return rows
        rows.append({"id": user_id, "user": name, "points": points, "ids": 1})
        return rows

    store.update("leaderboard", [], bump)
    return score_row(user_id)


# ---------- closing an account ----------
def delete_user(user_id: str) -> bool:
    """Remove the account and everything attached to it.

    The privacy policy promises deletion on request, so this really deletes:
    the row, every session (so any other device is signed out immediately) and
    the saved list. There is no soft-delete flag to forget about later.
    """
    found = [False]

    def drop_user(users):
        keep = [u for u in users if u["id"] != user_id]
        found[0] = len(keep) != len(users)
        return keep

    store.update("users", [], drop_user)
    if not found[0]:
        return False

    store.update("sessions", [], lambda ss: [x for x in ss if x["user"] != user_id])

    def drop_saved(all_saved):
        all_saved.pop(user_id, None)
        return all_saved

    store.update("saved", {}, drop_saved)
    store.update("leaderboard", [], lambda rs: [r for r in rs if r.get("id") != user_id])

    def drop_closet(all_closets):
        all_closets.pop(user_id, None)
        return all_closets

    store.update("closet", {}, drop_closet)
    return True


def delete_by_email(email: str) -> bool:
    user = find_user(email)
    return delete_user(user["id"]) if user else False


# ---------- saved items ----------
def saved_ids(user_id: str):
    return store.load("saved", {}).get(user_id, [])


def toggle_saved(user_id: str, item_id, on: bool):
    def upd(all_saved):
        ids = [i for i in all_saved.get(user_id, []) if str(i) != str(item_id)]
        if on:
            ids.append(str(item_id))
        all_saved[user_id] = ids
        return all_saved
    return store.update("saved", {}, upd).get(user_id, [])


# ---------- sign in with Google ----------
# The ID token is verified by Google's own tokeninfo endpoint, so we do not
# have to implement RS256 verification (and cannot get it subtly wrong).
def google_login(id_token: str):
    client_id = (os.environ.get("GOOGLE_CLIENT_ID") or "").strip()
    if not client_id:
        return None, "google_not_configured"
    if not id_token or len(id_token) > 4096:
        return None, "bad_token"
    try:
        url = ("https://oauth2.googleapis.com/tokeninfo?id_token="
               + urllib.parse.quote(id_token, safe=""))
        with urllib.request.urlopen(url, timeout=10) as r:
            info = json.load(r)
    except Exception:
        return None, "bad_token"

    # the token must have been minted for *us*, and the address must be verified
    if info.get("aud") != client_id:
        return None, "wrong_audience"
    if str(info.get("email_verified", "")).lower() not in ("true", "1"):
        return None, "email_unverified"
    email = (info.get("email") or "").strip().lower()
    if not EMAIL_RE.match(email):
        return None, "bad_email"

    user = find_user(email)
    if user:
        return public(user), None

    user = {
        "id": secrets.token_hex(8),
        "email": email,
        "name": (info.get("given_name") or email.split("@")[0])[:24],
        "password": hash_password(secrets.token_urlsafe(32)),  # unusable, they use Google
        "google": True,
        "plus": False,
        "created": int(time.time()),
    }
    store.update("users", [], lambda us: us + [user])
    return public(user), None
