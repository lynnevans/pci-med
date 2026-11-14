# -*- coding: utf-8 -*-
"""医生账号与会话（SQLite，无外部依赖）。

- 注册：用户名 3–32 位（中英文/数字/下划线），密码至少 6 位
- 密码：PBKDF2-HMAC-SHA256，16 字节随机盐，120000 次
- 会话：随机 token 存 HttpOnly Cookie，数据库只存 token 的 SHA-256
- 有效期：7 天，退出即删除
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
from pathlib import Path

DB_PATH = Path(os.getenv("PCI_USERS_DB", str(Path(__file__).with_name("users.db"))))
SESSION_DAYS = 7
PBKDF2_ROUNDS = 120_000
USERNAME_RE = re.compile(r"^[A-Za-z0-9_\u4e00-\u9fff]{3,32}$")


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=8)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def _db():
    conn = _connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with _db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                salt TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                expires_at INTEGER NOT NULL,
                created_at INTEGER NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)")
        conn.execute("DELETE FROM sessions WHERE expires_at <= ?", (int(time.time()),))


def _hash_password(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ROUNDS).hex()


def _public_user(row: sqlite3.Row) -> dict:
    return {"id": row["id"], "username": row["username"], "display_name": row["display_name"]}


def register(username: str, password: str, display_name: str = "") -> dict:
    username = (username or "").strip()
    display_name = (display_name or "").strip() or username
    if not USERNAME_RE.match(username):
        raise ValueError("用户名需为 3–32 位中英文、数字或下划线")
    if len(password or "") < 6:
        raise ValueError("密码至少 6 位")
    salt = secrets.token_bytes(16)
    password_hash = _hash_password(password, salt)
    now = int(time.time())
    try:
        with _db() as conn:
            cur = conn.execute(
                "INSERT INTO users(username, display_name, salt, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
                (username, display_name, salt.hex(), password_hash, now),
            )
            return {"id": cur.lastrowid, "username": username, "display_name": display_name}
    except sqlite3.IntegrityError as exc:
        raise ValueError("该用户名已被注册，请换一个或直接登录") from exc


def login(username: str, password: str) -> dict | None:
    username = (username or "").strip()
    with _db() as conn:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    if row is None:
        return None
    expected = _hash_password(password or "", bytes.fromhex(row["salt"]))
    if not hmac.compare_digest(expected, row["password_hash"]):
        return None
    return _public_user(row)


def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    now = int(time.time())
    with _db() as conn:
        conn.execute(
            "INSERT INTO sessions(token_hash, user_id, expires_at, created_at) VALUES (?, ?, ?, ?)",
            (hashlib.sha256(token.encode("utf-8")).hexdigest(), user_id, now + SESSION_DAYS * 86400, now),
        )
    return token


def get_session_user(token: str | None) -> dict | None:
    if not token:
        return None
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    with _db() as conn:
        row = conn.execute(
            """
            SELECT users.id, users.username, users.display_name
            FROM sessions JOIN users ON users.id = sessions.user_id
            WHERE sessions.token_hash = ? AND sessions.expires_at > ?
            """,
            (token_hash, int(time.time())),
        ).fetchone()
    return dict(row) if row else None


def delete_session(token: str | None) -> None:
    if not token:
        return
    with _db() as conn:
        conn.execute(
            "DELETE FROM sessions WHERE token_hash = ?",
            (hashlib.sha256(token.encode("utf-8")).hexdigest(),),
        )
