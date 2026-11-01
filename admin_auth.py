"""Authentication helpers for the Nova Hotel admin area.

This module is intentionally separate from Nova's voice/booking implementation.
It uses a small local SQLite database for admin credentials and reset tokens.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import time
from contextlib import contextmanager
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

from fastapi import HTTPException, Request, status

ROOT = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("ADMIN_AUTH_DB", str(ROOT / "data" / "admin_auth.db"))).expanduser()
if not DB_PATH.is_absolute():
    DB_PATH = ROOT / DB_PATH
PBKDF2_ITERATIONS = 310_000

_RATE_BUCKETS: dict[tuple[str, str], deque[float]] = defaultdict(deque)


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def _db():
    conn = _connect()
    try:
        yield conn
    finally:
        conn.close()


def _password_hash(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def _verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, rounds, salt_hex, digest_hex = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        expected = bytes.fromhex(digest_hex)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(rounds))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def _normal_email(value: str) -> str:
    value = (value or "").strip().lower()
    if len(value) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
        raise HTTPException(status_code=422, detail="Enter a valid email address.")
    return value


def initialize_admin_auth() -> None:
    """Create auth tables and bootstrap the first admin using .env values."""
    with _db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                mobile TEXT,
                password_hash TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                auth_version INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER NOT NULL REFERENCES admins(id) ON DELETE CASCADE,
                token_hash TEXT NOT NULL UNIQUE,
                expires_at INTEGER NOT NULL,
                used_at INTEGER,
                created_at INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_admin_reset_admin ON password_reset_tokens(admin_id);
            CREATE INDEX IF NOT EXISTS idx_admin_reset_expiry ON password_reset_tokens(expires_at);
            """
        )
        existing = conn.execute("SELECT id FROM admins LIMIT 1").fetchone()
        if existing is None:
            email = os.getenv("ADMIN_EMAIL", "").strip().lower()
            password = os.getenv("ADMIN_PASSWORD", "")
            name = os.getenv("ADMIN_NAME", "Nova Administrator").strip() or "Nova Administrator"
            mobile = re.sub(r"[^0-9+]", "", os.getenv("ADMIN_MOBILE", ""))
            if not email or not password:
                raise RuntimeError(
                    "First admin is not configured. Set ADMIN_EMAIL and ADMIN_PASSWORD in the root .env file."
                )
            _normal_email(email)
            if email.endswith("@example.com") or password.startswith("CHANGE_THIS_"):
                raise RuntimeError("Replace the example ADMIN_EMAIL/ADMIN_PASSWORD values in .env before starting Nova.")
            if len(password) < 12:
                raise RuntimeError("ADMIN_PASSWORD must contain at least 12 characters.")
            conn.execute(
                "INSERT INTO admins(name,email,mobile,password_hash) VALUES(?,?,?,?)",
                (name, email, mobile, _password_hash(password)),
            )
            conn.commit()


def get_admin_by_id(admin_id: int) -> sqlite3.Row | None:
    with _db() as conn:
        return conn.execute(
            "SELECT id,name,email,is_active,auth_version FROM admins WHERE id=?", (admin_id,)
        ).fetchone()


def get_admin_for_login(email: str) -> sqlite3.Row | None:
    with _db() as conn:
        return conn.execute("SELECT * FROM admins WHERE email=? COLLATE NOCASE", (email,)).fetchone()


def verify_admin_password(password: str, password_hash: str) -> bool:
    return _verify_password(password, password_hash)


def create_reset_token(admin_id: int, ttl_minutes: int) -> str:
    raw_token = secrets.token_urlsafe(40)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    now = int(time.time())
    with _db() as conn:
        # Only the newest outstanding link is valid.
        conn.execute(
            "UPDATE password_reset_tokens SET used_at=? WHERE admin_id=? AND used_at IS NULL",
            (now, admin_id),
        )
        conn.execute(
            "INSERT INTO password_reset_tokens(admin_id,token_hash,expires_at,created_at) VALUES(?,?,?,?)",
            (admin_id, token_hash, now + ttl_minutes * 60, now),
        )
        conn.commit()
    return raw_token


def reset_admin_password(raw_token: str, new_password: str) -> bool:
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    now = int(time.time())
    with _db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        token = conn.execute(
            "SELECT id,admin_id,expires_at,used_at FROM password_reset_tokens WHERE token_hash=?",
            (token_hash,),
        ).fetchone()
        if token is None or token["used_at"] is not None or int(token["expires_at"]) <= now:
            conn.rollback()
            return False
        admin = conn.execute("SELECT id,is_active FROM admins WHERE id=?", (token["admin_id"],)).fetchone()
        if admin is None or not admin["is_active"]:
            conn.rollback()
            return False
        conn.execute(
            "UPDATE admins SET password_hash=?,auth_version=auth_version+1 WHERE id=?",
            (_password_hash(new_password), token["admin_id"]),
        )
        conn.execute("UPDATE password_reset_tokens SET used_at=? WHERE admin_id=? AND used_at IS NULL", (now, token["admin_id"]))
        conn.commit()
        return True


def revoke_admin_sessions(admin_id: int) -> None:
    with _db() as conn:
        conn.execute("UPDATE admins SET auth_version=auth_version+1 WHERE id=?", (admin_id,))
        conn.commit()


def consume_rate_limit(request: Request, bucket: str, limit: int, window_seconds: int) -> None:
    client = request.client.host if request.client else "unknown"
    key = (bucket, client)
    now = time.monotonic()
    events = _RATE_BUCKETS[key]
    while events and now - events[0] > window_seconds:
        events.popleft()
    if len(events) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Please wait a while and try again.",
            headers={"Retry-After": str(window_seconds)},
        )
    events.append(now)


async def require_admin(request: Request) -> dict[str, Any]:
    session = request.session
    admin_id = session.get("admin_id")
    session_version = session.get("auth_version")
    if not admin_id or session_version is None:
        raise HTTPException(status_code=401, detail="Admin login required.")
    admin = get_admin_by_id(int(admin_id))
    if (
        admin is None
        or not admin["is_active"]
        or int(admin["auth_version"]) != int(session_version)
    ):
        session.clear()
        raise HTTPException(status_code=401, detail="Your admin session has expired. Please sign in again.")
    return dict(admin)


async def require_csrf(request: Request) -> None:
    expected = str(request.session.get("csrf_token", ""))
    provided = request.headers.get("x-csrf-token", "")
    if not expected or not provided or not hmac.compare_digest(expected, provided):
        raise HTTPException(status_code=403, detail="Security check failed. Refresh the admin page and try again.")
