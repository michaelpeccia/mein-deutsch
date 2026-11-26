#!/usr/bin/env python3
"""Mein Deutsch daily reminder server (runs on kingdom-ai).

Sends one push notification a day at the time you pick in the app, plus a
9 PM "save your streak" nudge, and skips both on days you already did a lesson.
Keys are created on first run and never leave this machine.
"""
import base64
import datetime
import json
import os
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from zoneinfo import ZoneInfo

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from pywebpush import WebPushException, webpush

HERE = os.path.dirname(os.path.abspath(__file__))
KEY_FILE = os.path.join(HERE, "vapid_private.pem")
DB_FILE = os.path.join(HERE, "subscriptions.json")
PORT = int(os.environ.get("PORT", "8097"))
CONTACT = "mailto:michaelbenyah@kingdom-life-ministry.com"
ALLOWED_ORIGINS = {"https://michaelpeccia.github.io", "https://german.kingdom-life-ministry.com"}
LATE_TIME = "21:00"          # second nudge if no lesson yet
WINDOW_MIN = 60              # a reminder may go out up to this many minutes after its time
DEFAULT_TZ = "America/Chicago"
TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")

lock = threading.Lock()


def b64url(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def load_public_key() -> str:
    if not os.path.exists(KEY_FILE):
        key = ec.generate_private_key(ec.SECP256R1())
        with open(KEY_FILE, "wb") as f:
            f.write(key.private_bytes(serialization.Encoding.PEM,
                                      serialization.PrivateFormat.PKCS8,
                                      serialization.NoEncryption()))
        os.chmod(KEY_FILE, 0o600)
        print("Created new VAPID key", flush=True)
    with open(KEY_FILE, "rb") as f:
        key = serialization.load_pem_private_key(f.read(), None)
    raw = key.public_key().public_bytes(serialization.Encoding.X962,
                                        serialization.PublicFormat.UncompressedPoint)
    return b64url(raw)


PUBLIC_KEY = load_public_key()


def load_db() -> dict:
    try:
        with open(DB_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_db(db: dict) -> None:
    tmp = DB_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(db, f, indent=1)
    os.replace(tmp, DB_FILE)


DB = load_db()


def minutes(hm: str) -> int:
    h, m = hm.split(":")
    return int(h) * 60 + int(m)


def tz_for(rec):
    try:
        return ZoneInfo(rec.get("tz") or DEFAULT_TZ)
    except Exception:
        return ZoneInfo(DEFAULT_TZ)


def send(rec: dict, title: str, body: str):
    """Returns True if sent, 'gone' if the phone unsubscribed, False on other errors."""
    try:
        webpush(subscription_info=rec["sub"],
                data=json.dumps({"title": title, "body": body, "tag": "daily"}),
                vapid_private_key=KEY_FILE,
                vapid_claims={"sub": CONTACT},
                ttl=3 * 3600)
        return True
    except WebPushException as e:
        code = e.response.status_code if e.response is not None else None
        print(f"push failed ({code}): {e}", flush=True)
        return "gone" if code in (404, 410) else False
    except Exception as e:  # network trouble: try again next time
        print(f"push error: {e}", flush=True)
        return False


def messages(rec: dict, today: str, yesterday: str):
    streak = int(rec.get("streak") or 0)
    alive = rec.get("lastDay") == yesterday and streak > 0
    if alive:
        main = (f"🔥 {streak}-day streak", "Keep it going! Zeit für Deutsch. One lesson takes about 3 minutes.")
        late = (f"⏰ Your {streak}-day streak ends at midnight", "Do one quick lesson before bed to keep it alive.")
    else:
        main = ("Zeit für Deutsch! 🇩🇪", "Start a new streak today with one quick lesson.")
        late = None
    return main, late


def scheduler():
    while True:
        try:
            with lock:
                changed = False
                for rid, rec in list(DB.items()):
                    now = datetime.datetime.now(tz_for(rec))
                    today = now.date().isoformat()
                    yesterday = (now.date() - datetime.timedelta(days=1)).isoformat()
                    if rec.get("lastDay") == today:
                        continue  # lesson already done today
                    m = now.hour * 60 + now.minute
                    main, late = messages(rec, today, yesterday)
                    result = None
                    t = minutes(rec.get("time", "19:00"))
                    if rec.get("sentDay") != today and t <= m < t + WINDOW_MIN:
                        result = send(rec, *main)
                        rec["sentDay"] = today
                        changed = True
                    elif late and rec.get("lateDay") != today and t < minutes(LATE_TIME) \
                            and minutes(LATE_TIME) <= m < minutes(LATE_TIME) + WINDOW_MIN:
                        result = send(rec, *late)
                        rec["lateDay"] = today
                        changed = True
                    if result == "gone":
                        del DB[rid]
                        print(f"removed dead subscription {rid}", flush=True)
                if changed:
                    save_db(DB)
        except Exception as e:  # keep the loop alive no matter what
            print("scheduler error:", e, flush=True)
        time.sleep(30)


class Handler(BaseHTTPRequestHandler):
    server_version = "MeinDeutschPush/1"

    def cors(self):
        origin = self.headers.get("Origin", "")
        if origin in ALLOWED_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def reply(self, code: int, obj: dict):
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self.send_response(204)
        self.cors()
        self.end_headers()

    def do_GET(self):
        if self.path == "/vapid":
            return self.reply(200, {"key": PUBLIC_KEY})
        if self.path == "/health":
            return self.reply(200, {"ok": True, "subscribers": len(DB)})
        self.reply(404, {"error": "not found"})

    def body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0 or n > 16384:
            raise ValueError("bad length")
        return json.loads(self.rfile.read(n))

    def do_POST(self):
        try:
            b = self.body()
        except Exception:
            return self.reply(400, {"error": "bad request"})
        rid = str(b.get("id") or "")[:64]
        if not rid:
            return self.reply(400, {"error": "missing id"})

        if self.path == "/subscribe":
            sub = b.get("sub") or {}
            tm = str(b.get("time") or "19:00")
            if not str(sub.get("endpoint", "")).startswith("https://") or not sub.get("keys"):
                return self.reply(400, {"error": "bad subscription"})
            if not TIME_RE.match(tm):
                return self.reply(400, {"error": "bad time"})
            with lock:
                old = DB.get(rid, {})
                DB[rid] = {"sub": sub, "time": tm, "tz": str(b.get("tz") or DEFAULT_TZ)[:64],
                           "streak": int(b.get("streak") or 0), "lastDay": b.get("lastDay"),
                           "sentDay": old.get("sentDay"), "lateDay": old.get("lateDay")}
                save_db(DB)
            return self.reply(200, {"ok": True})

        with lock:
            rec = DB.get(rid)
        if rec is None:
            return self.reply(404, {"error": "not subscribed"})

        if self.path == "/done":
            with lock:
                rec["streak"] = int(b.get("streak") or 0)
                rec["lastDay"] = b.get("lastDay")
                save_db(DB)
            return self.reply(200, {"ok": True})

        if self.path == "/unsubscribe":
            with lock:
                DB.pop(rid, None)
                save_db(DB)
            return self.reply(200, {"ok": True})

        if self.path == "/test":
            result = send(rec, "🔔 Test from kingdom-ai", "Reminders are working. Bis morgen!")
            return self.reply(200 if result is True else 502, {"ok": result is True})

        self.reply(404, {"error": "not found"})

    def log_message(self, fmt, *args):
        pass  # keep the journal quiet


if __name__ == "__main__":
    threading.Thread(target=scheduler, daemon=True).start()
    print(f"Mein Deutsch push server on port {PORT}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
