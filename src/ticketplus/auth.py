"""Dependency-free email/password auth for the local TicketPlus reference environment.

Not intended for real production use (no rate limiting, no email verification,
no password reset flow) -- it exists so the frontend has a real register/login
screen to talk to instead of a client-generated guest id.
"""

import base64
import hashlib
import hmac
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import RLock
from uuid import uuid4

TOKEN_TTL_SECONDS = 60 * 60 * 24 * 7  # 7 days
PBKDF2_ITERATIONS = 200_000


class EmailAlreadyRegistered(Exception):
    """Raised when registering with an email that already has an account."""


class InvalidCredentials(Exception):
    """Raised on bad login, bad/expired token, or missing auth."""


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user' CHECK(role IN ('user', 'admin')),
    created_at TEXT NOT NULL
);
"""


class NotAuthorized(Exception):
    """Raised when an authenticated user lacks the role required for an action."""


def _b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64u_decode(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


class AuthService:
    def __init__(self, database: str | Path, secret: str | None = None) -> None:
        self.database = str(database)
        self.secret = (secret or os.getenv("AUTH_SECRET") or "ticketplus-dev-secret-change-me").encode()
        self._write_lock = RLock()
        with self._connect() as connection:
            connection.executescript(SCHEMA)

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.database, timeout=30, isolation_level=None)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
        finally:
            connection.close()

    @staticmethod
    def _hash_password(password: str, salt: bytes) -> str:
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
        return _b64u(digest)

    def register(self, email: str, password: str, name: str, role: str = "user") -> dict[str, str]:
        email = (email or "").strip().lower()
        name = (name or "").strip()
        if "@" not in email or "." not in email.split("@")[-1] or len(email) < 5:
            raise ValueError("a valid email address is required")
        if not password or len(password) < 8:
            raise ValueError("password must be at least 8 characters")
        if not name:
            raise ValueError("name is required")
        if role not in ("user", "admin"):
            raise ValueError("role must be 'user' or 'admin'")

        salt = os.urandom(16)
        password_hash = self._hash_password(password, salt)
        user_id = str(uuid4())
        with self._write_lock, self._connect() as connection:
            try:
                connection.execute(
                    "INSERT INTO users (id, email, name, password_hash, salt, role, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (user_id, email, name, password_hash, _b64u(salt), role, datetime.now(UTC).isoformat()),
                )
            except sqlite3.IntegrityError as error:
                raise EmailAlreadyRegistered(email) from error
        return {"id": user_id, "email": email, "name": name, "role": role}

    def login(self, email: str, password: str) -> dict[str, str]:
        email = (email or "").strip().lower()
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if not row:
            raise InvalidCredentials("invalid email or password")
        expected = self._hash_password(password or "", _b64u_decode(row["salt"]))
        if not hmac.compare_digest(expected, row["password_hash"]):
            raise InvalidCredentials("invalid email or password")
        return {"id": row["id"], "email": row["email"], "name": row["name"], "role": row["role"]}

    def issue_token(self, user_id: str) -> str:
        payload = {
            "sub": user_id,
            "exp": (datetime.now(UTC) + timedelta(seconds=TOKEN_TTL_SECONDS)).isoformat(),
        }
        payload_b64 = _b64u(json.dumps(payload).encode())
        signature = _b64u(hmac.new(self.secret, payload_b64.encode(), hashlib.sha256).digest())
        return f"{payload_b64}.{signature}"

    def _verify_token(self, token: str) -> str:
        try:
            payload_b64, signature = token.split(".", 1)
        except ValueError as error:
            raise InvalidCredentials("malformed token") from error
        expected_signature = _b64u(hmac.new(self.secret, payload_b64.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected_signature):
            raise InvalidCredentials("invalid token signature")
        try:
            payload = json.loads(_b64u_decode(payload_b64))
            expires_at = datetime.fromisoformat(payload["exp"])
        except (ValueError, KeyError) as error:
            raise InvalidCredentials("malformed token") from error
        if expires_at <= datetime.now(UTC):
            raise InvalidCredentials("token expired")
        return str(payload["sub"])

    def get_user(self, user_id: str) -> dict[str, str]:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if not row:
            raise InvalidCredentials("user no longer exists")
        return {"id": row["id"], "email": row["email"], "name": row["name"], "role": row["role"]}

    def user_from_token(self, token: str) -> dict[str, str]:
        return self.get_user(self._verify_token(token))

    def user_from_auth_header(self, header_value: str | None) -> dict[str, str]:
        if not header_value or not header_value.startswith("Bearer "):
            raise InvalidCredentials("missing bearer token")
        return self.user_from_token(header_value[len("Bearer ") :])

    def require_admin(self, header_value: str | None) -> dict[str, str]:
        """Return the authenticated user, or raise if they are not an admin."""
        user = self.user_from_auth_header(header_value)
        if user["role"] != "admin":
            raise NotAuthorized("admin role is required for this action")
        return user
