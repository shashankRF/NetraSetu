"""Sign-in, profile and troubleshooting APIs for the NetraSetu prototype."""
from __future__ import annotations

import base64
import json
import os
import re
import smtplib
import ssl
import uuid
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .authentication import (
    SESSION_COOKIE, SESSION_TTL_SECONDS, authenticate, get_session,
    invalidate_session, request_session, require_session, update_display_name,
    _configured_credentials,
)

router = APIRouter()


class Credentials(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=256)


class DisplayNameUpdate(BaseModel):
    display_name: str = Field(min_length=2, max_length=50)


class Attachment(BaseModel):
    filename: str = Field(max_length=180)
    content_type: str = Field(max_length=100)
    content_base64: str = Field(max_length=7_000_000)


class TroubleReport(BaseModel):
    category: str = Field(min_length=1, max_length=60)
    title: str = Field(min_length=4, max_length=120)
    description: str = Field(min_length=10, max_length=5000)
    module: str = Field(min_length=1, max_length=100)
    error_message: Optional[str] = Field(default=None, max_length=2000)
    attachment: Optional[Attachment] = None


def _cookie_settings(request: Request) -> dict:
    production = os.getenv("NETRASETU_ENV", "development").strip().lower() not in {"development", "dev", "local", "demo"}
    return {
        "key": SESSION_COOKIE,
        "httponly": True,
        "secure": production or request.url.scheme == "https",
        "samesite": "strict",
        "max_age": SESSION_TTL_SECONDS,
        "path": "/",
    }


@router.post("/api/auth/login")
def login(body: Credentials, request: Request):
    client_key = request.client.host if request.client else "unknown"
    token, attempts, demo = authenticate(body.username, body.password, client_key)
    if token is None:
        response = JSONResponse({
            "authenticated": False,
            "message": "Username or password is incorrect.",
            "administrator_warning": attempts > 3,
        }, status_code=401)
        return response
    session = get_session(token) or {}
    response = JSONResponse({
        "authenticated": True,
        "username": session.get("username"),
        "display_name": session.get("display_name"),
        "demo_mode": demo,
        "expires_in": SESSION_TTL_SECONDS,
        "csrf_token": session.get("csrf_token"),
    })
    response.set_cookie(**_cookie_settings(request), value=token)
    return response


@router.get("/api/auth/session")
def session_status(request: Request):
    _, session = request_session(request)
    if not session:
        _, _, demo = _configured_credentials()
        return {"authenticated": False, "demo_mode": demo}
    return {"authenticated": True, "username": session["username"], "display_name": session["display_name"], "demo_mode": session["demo_mode"], "csrf_token": session["csrf_token"]}


@router.post("/api/auth/logout")
def logout(request: Request):
    token, _ = request_session(request)
    invalidate_session(token)
    response = JSONResponse({"authenticated": False})
    production = os.getenv("NETRASETU_ENV", "development").strip().lower() not in {"development", "dev", "local", "demo"}
    response.delete_cookie(SESSION_COOKIE, path="/", httponly=True, samesite="strict", secure=production or request.url.scheme == "https")
    return response


@router.patch("/api/auth/profile")
def save_profile(body: DisplayNameUpdate, session=Depends(require_session)):
    name = " ".join(body.display_name.split())
    if len(name) < 2 or not any(ch.isalpha() for ch in name):
        raise HTTPException(status_code=422, detail="Enter a display name containing at least two characters.")
    update_display_name(session["username"], name)
    # Update every active session for this username so the sidebar reflects the save immediately.
    from . import authentication
    with authentication._lock:
        for active in authentication._sessions.values():
            if active["username"] == session["username"]:
                active["display_name"] = name
    return {"saved": True, "display_name": name, "persistence": "local server profile file"}


REPORT_DIR = Path(__file__).resolve().parent / "support" / "reports"
REPORT_FILE = REPORT_DIR / "reports.jsonl"
ALLOWED_ATTACHMENTS = {
    ".pdf": ("application/pdf", b"%PDF-"),
    ".txt": ("text/plain", None),
    ".png": ("image/png", b"\x89PNG\r\n\x1a\n"),
    ".jpg": ("image/jpeg", b"\xff\xd8\xff"),
    ".jpeg": ("image/jpeg", b"\xff\xd8\xff"),
}
MAX_ATTACHMENT_BYTES = 5 * 1024 * 1024


def _redact_secrets(text: str) -> str:
    text = re.sub(r"(?i)(authorization|password|passwd|api[_ -]?key|access[_ -]?token|secret)\s*[:=]\s*(?:Bearer\s+)?[^\s,;]+", r"\1=[REDACTED]", text)
    text = re.sub(r"(?i)bearer\s+[A-Za-z0-9._~+/-]+=*", "Bearer [REDACTED]", text)
    return text


def _save_attachment(report_id: str, attachment: Attachment | None) -> dict | None:
    if attachment is None:
        return None
    name = Path(attachment.filename.replace("\\", "/")).name
    ext = Path(name).suffix.lower()
    allowed = ALLOWED_ATTACHMENTS.get(ext)
    if not allowed or attachment.content_type.lower() != allowed[0]:
        raise HTTPException(status_code=415, detail="Attachment must be a PDF, TXT, PNG or JPEG with a matching file type.")
    try:
        payload = base64.b64decode(attachment.content_base64, validate=True)
    except (ValueError, base64.binascii.Error):
        raise HTTPException(status_code=422, detail="Attachment data is invalid.")
    if not payload or len(payload) > MAX_ATTACHMENT_BYTES:
        raise HTTPException(status_code=413, detail="Attachment must be between 1 byte and 5 MB.")
    signature = allowed[1]
    if signature and not payload.startswith(signature):
        raise HTTPException(status_code=415, detail="Attachment content does not match its file type.")
    if ext == ".txt":
        try:
            payload.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(status_code=415, detail="TXT attachments must be valid UTF-8 text.")
    folder = REPORT_DIR / "attachments"
    folder.mkdir(parents=True, exist_ok=True)
    stored_name = f"{report_id}{ext}"
    (folder / stored_name).write_bytes(payload)
    return {"filename": name, "content_type": allowed[0], "size_bytes": len(payload), "stored_as": f"attachments/{stored_name}"}


def _send_email(record: dict) -> tuple[str, str]:
    recipient = os.getenv("NETRASETU_SUPPORT_EMAIL", "").strip()
    host = os.getenv("NETRASETU_SMTP_HOST", "").strip()
    sender = os.getenv("NETRASETU_SMTP_FROM", "").strip()
    if not recipient or not host or not sender:
        return "SAVED_EMAIL_NOT_CONFIGURED", "Report saved locally; support email or SMTP delivery is not configured."
    try:
        message = EmailMessage()
        message["Subject"] = f"NetraSetu troubleshooting: {record['title']} [{record['report_id']}]"
        message["From"] = sender
        message["To"] = recipient
        message.set_content(
            f"Report ID: {record['report_id']}\nCategory: {record['category']}\nModule: {record['module']}\n"
            f"Title: {record['title']}\n\nDescription:\n{record['description']}\n\n"
            f"Error message:\n{record.get('error_message') or 'Not provided'}\n"
        )
        attachment_info = record.get("attachment")
        if attachment_info:
            relative = Path(attachment_info["stored_as"])
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError("Invalid stored attachment reference")
            path = (REPORT_DIR / relative).resolve()
            if not path.is_relative_to(REPORT_DIR.resolve()):
                raise ValueError("Invalid stored attachment path")
            data = path.read_bytes()
            maintype, subtype = attachment_info["content_type"].split("/", 1)
            message.add_attachment(data, maintype=maintype, subtype=subtype, filename=attachment_info["filename"])
        port = int(os.getenv("NETRASETU_SMTP_PORT", "587"))
        user = os.getenv("NETRASETU_SMTP_USERNAME", "")
        password = os.getenv("NETRASETU_SMTP_PASSWORD", "")
        timeout = float(os.getenv("NETRASETU_SMTP_TIMEOUT", "10"))
        if os.getenv("NETRASETU_SMTP_USE_SSL", "false").lower() == "true":
            with smtplib.SMTP_SSL(host, port, timeout=timeout, context=ssl.create_default_context()) as smtp:
                if user:
                    smtp.login(user, password)
                smtp.send_message(message)
        else:
            with smtplib.SMTP(host, port, timeout=timeout) as smtp:
                smtp.starttls(context=ssl.create_default_context())
                if user:
                    smtp.login(user, password)
                smtp.send_message(message)
        return "EMAIL_SENT", "Report was accepted by the configured email service."
    except Exception:
        return "SAVED_EMAIL_DELIVERY_FAILED", "Report is saved locally, but email delivery failed. An administrator can retry it."


def _append_record(record: dict) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    with REPORT_FILE.open("a", encoding="utf-8") as output:
        output.write(json.dumps(record, ensure_ascii=False) + "\n")


def _records() -> list[dict]:
    if not REPORT_FILE.exists():
        return []
    rows = []
    for line in REPORT_FILE.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


@router.post("/api/troubleshooting/reports")
def submit_report(body: TroubleReport, session=Depends(require_session)):
    report_id = "TRB-" + uuid.uuid4().hex[:16]
    attachment_record = _save_attachment(report_id, body.attachment)
    record = {
        "report_id": report_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "username": session["username"],
        "category": body.category,
        "title": body.title.strip(),
        "description": body.description.strip(),
        "module": body.module,
        "error_message": _redact_secrets(body.error_message or ""),
        "attachment": attachment_record,
        "delivery_status": "PENDING",
    }
    _append_record(record)
    status, message = _send_email(record)
    record["delivery_status"] = status
    # Append a status event to preserve the original report and later retries.
    _append_record({"report_id": report_id, "updated_at": datetime.now(timezone.utc).isoformat(), "delivery_status": status})
    return {"report_id": report_id, "delivery_status": status, "message": message}


@router.post("/api/troubleshooting/reports/{report_id}/retry")
def retry_report(report_id: str, session=Depends(require_session)):
    record = next((r for r in reversed(_records()) if r.get("report_id") == report_id and "title" in r), None)
    if not record or record.get("username") != session["username"]:
        raise HTTPException(status_code=404, detail="Troubleshooting report not found.")
    status, message = _send_email(record)
    _append_record({"report_id": report_id, "updated_at": datetime.now(timezone.utc).isoformat(), "delivery_status": status})
    return {"report_id": report_id, "delivery_status": status, "message": message}

