"""
NetraSetu Authentication & Session API Router
============================================

Provides session verification, local administrative sign-in, CSRF token
generation, and user profile management for the NetraSetu platform.
"""

from __future__ import annotations

import os
import secrets
import time
from typing import Any, Dict, Optional, Tuple
from fastapi import APIRouter, Cookie, Header, HTTPException, Request, Response
from pydantic import BaseModel

router = APIRouter(tags=["Authentication"])

# In-memory session store for local demo
_ACTIVE_SESSIONS: Dict[str, Dict[str, Any]] = {}
_DEMO_CSRF_TOKEN = secrets.token_hex(16)


class LoginRequest(BaseModel):
    username: str
    password: str


class ProfileUpdateRequest(BaseModel):
    display_name: str


def _get_or_create_session(session_id: Optional[str]) -> Tuple[str, Dict[str, Any]]:
    if session_id and session_id in _ACTIVE_SESSIONS:
        sess = _ACTIVE_SESSIONS[session_id]
        if time.time() - sess.get("timestamp", 0) < 3600:
            return session_id, sess

    # Generate new session ID
    new_id = secrets.token_urlsafe(32)
    sess = {
        "authenticated": False,
        "username": "",
        "display_name": "",
        "csrf_token": secrets.token_hex(16),
        "timestamp": time.time(),
        "demo_mode": True,
    }
    _ACTIVE_SESSIONS[new_id] = sess
    return new_id, sess


@router.get("/api/auth/session")
def get_session(
    request: Request,
    response: Response,
    netra_session: Optional[str] = Cookie(None),
) -> Dict[str, Any]:
    """Returns the current user session state, demo mode status, and CSRF token."""
    sid, sess = _get_or_create_session(netra_session)
    response.set_cookie(
        key="netra_session",
        value=sid,
        httponly=True,
        samesite="lax",
        max_age=3600,
    )
    return {
        "authenticated": sess.get("authenticated", False),
        "username": sess.get("username", ""),
        "display_name": sess.get("display_name", ""),
        "demo_mode": True,
        "csrf_token": sess.get("csrf_token", _DEMO_CSRF_TOKEN),
    }


@router.post("/api/auth/login")
def login(
    req: LoginRequest,
    response: Response,
    netra_session: Optional[str] = Cookie(None),
) -> Dict[str, Any]:
    """
    Signs the user into the NetraSetu administrative dashboard.
    In local demonstration mode, any valid non-empty username/password is accepted.
    Default recommended credentials: admin / admin (or admin / netrasetu).
    """
    uname = (req.username or "").strip()
    pword = (req.password or "").strip()

    if not uname or not pword:
        raise HTTPException(
            status_code=400,
            detail="Username and password are required.",
        )

    # In local demo environment, authorize user cleanly
    sid, sess = _get_or_create_session(netra_session)
    sess["authenticated"] = True
    sess["username"] = uname
    sess["display_name"] = uname.title() if uname.lower() != "admin" else "NetraSetu Lead Officer"
    sess["timestamp"] = time.time()
    sess["csrf_token"] = secrets.token_hex(16)
    _ACTIVE_SESSIONS[sid] = sess

    response.set_cookie(
        key="netra_session",
        value=sid,
        httponly=True,
        samesite="lax",
        max_age=3600,
    )

    return {
        "status": "SUCCESS",
        "authenticated": True,
        "username": sess["username"],
        "display_name": sess["display_name"],
        "demo_mode": True,
        "csrf_token": sess["csrf_token"],
        "message": "Signed in successfully.",
    }


@router.post("/api/auth/logout")
def logout(
    response: Response,
    netra_session: Optional[str] = Cookie(None),
) -> Dict[str, Any]:
    """Signs out of the current session."""
    if netra_session and netra_session in _ACTIVE_SESSIONS:
        _ACTIVE_SESSIONS.pop(netra_session, None)

    response.delete_cookie("netra_session")
    return {
        "status": "SUCCESS",
        "authenticated": False,
        "message": "Signed out successfully.",
    }


@router.patch("/api/auth/profile")
def update_profile(
    req: ProfileUpdateRequest,
    netra_session: Optional[str] = Cookie(None),
) -> Dict[str, Any]:
    """Updates user display name."""
    sid, sess = _get_or_create_session(netra_session)
    disp = (req.display_name or "").strip()
    if disp:
        sess["display_name"] = disp
        sess["timestamp"] = time.time()
    return {
        "status": "SUCCESS",
        "display_name": sess.get("display_name", "Authorized Officer"),
    }


# ============================================================
# Simulator Support Endpoints (Prevents Console 404s)
# ============================================================

@router.get("/api/5g/failure-combinations/catalog")
def get_failure_catalog() -> Dict[str, Any]:
    return {
        "status": "SUCCESS",
        "failures": {
            "DU_FAILOVER": {"label": "Distributed Unit (DU) Failure", "modeled_range": "10-50ms"},
            "BACKHAUL_CONGESTION": {"label": "Backhaul Transport Congestion", "modeled_range": "15-120ms"},
            "SLICE_ISOLATION_BREACH": {"label": "Emergency Slice Degradation", "modeled_range": "Packet loss 0.1-5%"},
        }
    }


@router.get("/api/5g/failure-combinations")
def get_failure_combinations(limit: int = 20) -> Dict[str, Any]:
    return {
        "status": "SUCCESS",
        "runs": []
    }
