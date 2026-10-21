"""Local demonstration authentication and short-lived server-side sessions.

Production deployments must configure NETRASETU_ADMIN_USERNAME and
NETRASETU_ADMIN_PASSWORD. The development-only fallback credentials are kept
on the server and are never emitted to the browser.
"""
from __future__ import annotations

import hmac
import os
import secrets
import threading
import time
from pathlib import Path
from typing import Any

from fastapi import HTTPException, Request

_lock = threading.RLock()
_sessions: dict[str, dict[str, Any]] = {}
_failures: dict[str, dict[str, float | int]] = {}
SESSION_COOKIE = "netrasetu_session"
SESSION_TTL_SECONDS = 60 * 30
LOGIN_FAILURE_LIMIT = 8
LOGIN_LOCK_SECONDS = 15 * 60
PROFILE_PATH = Path(__file__).resolve().parent / "auth" / "profiles.json"


def _configured_credentials() -> tuple[str | None, str | None, bool]:
    mode = os.getenv("NETRASETU_ENV", "development").strip().lower()
    demo = mode in {"development", "dev", "local", "demo"}
    username = os.getenv("NETRASETU_ADMIN_USERNAME") or ("admin" if demo else None)
    # Production accepts only a one-way Argon2id PHC hash. Plaintext password
    # configuration remains available solely for the explicitly marked demo.
    password = os.getenv("NETRASETU_ADMIN_PASSWORD") or ("admin123" if demo else None)
    return username, password, demo


def authenticate(username: str, password: str, client_key: str) -> tuple[str | None, int, bool]:
    expected_user, expected_password, demo = _configured_credentials()
    password_hash = os.getenv("NETRASETU_ADMIN_PASSWORD_HASH", "").strip()
    if not demo and (expected_user is None or not password_hash):
        raise HTTPException(status_code=503, detail="Authentication is not configured by the administrator.")
    if expected_user is None or (demo and expected_password is None):
        raise HTTPException(status_code=503, detail="Authentication is not configured by the administrator.")
    key = client_key + ":" + username.casefold()[:100]
    with _lock:
        failure = _failures.get(key, {"count": 0, "locked_until": 0.0})
        if float(failure["locked_until"]) > time.time():
            return None, int(failure["count"]), demo
    user_ok = hmac.compare_digest(username.encode(), expected_user.encode())
    if demo:
        password_ok = hmac.compare_digest(password.encode(), expected_password.encode())
    else:
        try:
            from argon2 import PasswordHasher
            from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
            try:
                password_ok = PasswordHasher().verify(password_hash, password)
            except (InvalidHashError, VerificationError, VerifyMismatchError):
                password_ok = False
        except ImportError as exc:
            raise HTTPException(status_code=503, detail="Argon2id support is unavailable; install the configured security dependencies.") from exc
    valid = user_ok and password_ok
    with _lock:
        if not valid:
            attempts = int(_failures.get(key, {}).get("count", 0)) + 1
            locked_until = time.time() + LOGIN_LOCK_SECONDS if attempts >= LOGIN_FAILURE_LIMIT else 0.0
            _failures[key] = {"count": attempts, "locked_until": locked_until}
            return None, attempts, demo
        _failures.pop(key, None)
        token = secrets.token_urlsafe(32)
        _sessions[token] = {"username": expected_user, "display_name": _display_name(expected_user), "demo_mode": demo, "csrf_token": secrets.token_urlsafe(32), "expires": time.time() + SESSION_TTL_SECONDS}
    return token, 0, demo


def _display_name(username: str) -> str:
    # Display-name persistence is intentionally separate from authentication.
    try:
        import json
        profile_path = PROFILE_PATH
        data = json.loads(profile_path.read_text(encoding="utf-8")) if profile_path.exists() else {}
        return str(data.get(username, username))
    except (OSError, ValueError, TypeError):
        return username


def update_display_name(username: str, display_name: str) -> None:
    import json
    profile_path = PROFILE_PATH
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        data = json.loads(profile_path.read_text(encoding="utf-8")) if profile_path.exists() else {}
        data[username] = display_name
        tmp_path = profile_path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp_path.replace(profile_path)


def get_session(token: str | None) -> dict[str, Any] | None:
    if not token:
        return None
    with _lock:
        session = _sessions.get(token)
        if not session:
            return None
        if session["expires"] <= time.time():
            _sessions.pop(token, None)
            return None
        return session


def valid_csrf(session: dict[str, Any], supplied: str | None) -> bool:
    expected = str(session.get("csrf_token", ""))
    return bool(expected and supplied and hmac.compare_digest(expected, supplied))


def invalidate_session(token: str | None) -> None:
    if token:
        with _lock:
            _sessions.pop(token, None)


def request_session(request: Request) -> tuple[str | None, dict[str, Any] | None]:
    token = request.cookies.get(SESSION_COOKIE)
    return token, get_session(token)


def requires_session(path: str, method: str = "GET") -> bool:
    """Protect dashboard/data operations without changing public query pages."""
    method = method.upper()
    # Catalogue, evidence and source files feed the authenticated dashboard;
    # guarding only the dashboard HTML would leave these API responses public.
    if path.startswith("/api/scenarios") or path.startswith("/api/documents/") or path == "/api/document_metadata":
        return True
    if path.startswith("/api/5g/"):
        return True
    if path.startswith("/api/audits"):
        return True
    if path.startswith("/api/risk/"):
        return True
    if path.startswith("/api/change_impact/") or path == "/api/verify_claim" or path.startswith("/api/verify_claim"):
        return True
    return path.startswith("/api/troubleshooting/reports")


def require_session(request: Request) -> dict[str, Any]:
    _, session = request_session(request)
    if not session:
        raise HTTPException(status_code=401, detail="Sign in to access this dashboard service.")
    return session

