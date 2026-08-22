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
        "created": int(time.time()),
    }
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
            "name": user.get("name"), "plus": bool(user.get("plus"))}


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
