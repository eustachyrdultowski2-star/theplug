#!/usr/bin/env python3
"""Ask the room what a piece is: a photo, a note, and answers underneath.

Nothing a stranger uploads appears on the site before somebody approves it,
so the queue holds three states — pending, open, rejected — and only open
ones are ever handed to the public endpoint.

Photos live in their own rows (`ask_photo_<id>`) rather than inside the index,
because the index is rewritten on every answer and a rewrite that drags a
hundred base64 images with it is a rewrite nobody wants.
"""
import base64, re, time, uuid

import store

MAX_PHOTO = 400_000        # characters of data URL, about 290 KB of image
MAX_PENDING = 5            # per person, so one bored visitor cannot flood it
MAX_OPEN = 300             # the queue is a queue, not an archive
CATS = ("jeans", "shoes", "belt", "shirt", "jacket", "knit", "scarf", "hat",
        "bag", "glasses", "jewelry", "watch", "other")

DATA_URL = re.compile(r"^data:image/(jpeg|jpg|png|webp);base64,[A-Za-z0-9+/=\s]+$")


def _asks():
    return store.load("asks", [])


def public_row(a, me_id=None):
    """What anybody may see: no email, no user id, no rejection reasons."""
    return {
        "id": a["id"],
        "note": a.get("note") or "",
        "cat": a.get("cat") or "other",
        "when": a.get("when"),
        "handle": a.get("handle") or "someone",
        "mine": bool(me_id and a.get("user_id") == me_id),
        "answers": [{"brand": x.get("brand"), "handle": x.get("handle"),
                     "when": x.get("when")} for x in (a.get("answers") or [])],
    }


def submit(user, photo, note="", cat="other"):
    """Take a photo into the queue. Returns (row, error)."""
    if not user:
        return None, "sign_in_required"
    photo = (photo or "").strip()
    if not DATA_URL.match(photo):
        return None, "bad_photo"
    if len(photo) > MAX_PHOTO:
        return None, "photo_too_big"
    if cat not in CATS:
        cat = "other"

    waiting = sum(1 for a in _asks()
                  if a.get("user_id") == user["id"] and a.get("status") == "pending")
    if waiting >= MAX_PENDING:
        return None, "too_many_pending"

    ask = {
        "id": uuid.uuid4().hex[:12],
        "user_id": user["id"],
        "handle": user.get("handle") or "someone",
        "note": (note or "").strip()[:120],
        "cat": cat,
        "when": time.time(),
        "status": "pending",          # nothing is public until a human says so
        "answers": [],
    }
    store.save("ask_photo_" + ask["id"], photo)
    store.update("asks", [], lambda rows: rows + [ask])
    return public_row(ask, user["id"]), None


def photo_of(ask_id):
    """The image bytes and their content type, for an approved ask only."""
    ask = next((a for a in _asks() if a["id"] == ask_id), None)
    if not ask or ask.get("status") != "open":
        return None, None
    data = store.load("ask_photo_" + ask_id, None)
    if not data or "," not in data:
        return None, None
    head, b64 = data.split(",", 1)
    ctype = head[5:].split(";")[0] or "image/jpeg"
    try:
        return base64.b64decode(b64), ctype
    except Exception:
        return None, None


def open_queue(me_id=None, limit=60):
    rows = [a for a in _asks() if a.get("status") == "open"]
    rows.sort(key=lambda a: -(a.get("when") or 0))
    return [public_row(a, me_id) for a in rows[:limit]]


def mine(user_id, limit=40):
    """Your own, whatever state they are in — you may see your own pending."""
    rows = [a for a in _asks() if a.get("user_id") == user_id]
    rows.sort(key=lambda a: -(a.get("when") or 0))
    out = []
    for a in rows[:limit]:
        row = public_row(a, user_id)
        row["status"] = a.get("status")
        out.append(row)
    return out


def answer(user, ask_id, brand):
    """Name the brand on somebody else's photo."""
    if not user:
        return None, "sign_in_required"
    brand = (brand or "").strip()[:40]
    if len(brand) < 2:
        return None, "bad_brand"

    err = [None]

    def upd(rows):
        for a in rows:
            if a["id"] != ask_id:
                continue
            if a.get("status") != "open":
                err[0] = "not_open"
                return rows
            answers = a.setdefault("answers", [])
            if any(x.get("user_id") == user["id"] for x in answers):
                err[0] = "already_answered"
                return rows
            answers.append({"user_id": user["id"],
                            "handle": user.get("handle") or "someone",
                            "brand": brand, "when": time.time()})
            return rows
        err[0] = "not_found"
        return rows

    rows = store.update("asks", [], upd)
    if err[0]:
        return None, err[0]
    ask = next((a for a in rows if a["id"] == ask_id), None)
    return public_row(ask, user["id"]), None


# ---------------------------------------------------------------- the desk --
def pending(limit=60):
    """The moderation queue, photos included — this is the one place they are
    handed out before approval, and it sits behind the admin key."""
    rows = [a for a in _asks() if a.get("status") == "pending"]
    rows.sort(key=lambda a: a.get("when") or 0)
    out = []
    for a in rows[:limit]:
        row = public_row(a)
        row["photo"] = store.load("ask_photo_" + a["id"], None)
        out.append(row)
    return out


def moderate(ask_id, action):
    """approve -> the queue sees it. reject -> the photo is deleted outright."""
    if action not in ("approve", "reject"):
        return None, "bad_action"

    def upd(rows):
        for a in rows:
            if a["id"] == ask_id:
                a["status"] = "open" if action == "approve" else "rejected"
                a["moderated"] = time.time()
        return rows

    rows = store.update("asks", [], upd)
    if action == "reject":
        # a rejected picture has no reason to stay on the disk
        store.save("ask_photo_" + ask_id, "")
    return {"id": ask_id, "status": "open" if action == "approve" else "rejected",
            "pending": sum(1 for a in rows if a.get("status") == "pending")}, None


def counts():
    rows = _asks()
    out = {"pending": 0, "open": 0, "rejected": 0, "answers": 0}
    for a in rows:
        out[a.get("status", "pending")] = out.get(a.get("status", "pending"), 0) + 1
        out["answers"] += len(a.get("answers") or [])
    return out
