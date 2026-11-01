"""Admin login, session, password recovery and protected page routes."""
from __future__ import annotations

import html
import logging
import os
import secrets
import time
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from admin_auth import (
    consume_rate_limit,
    create_reset_token,
    get_admin_for_login,
    initialize_admin_auth,
    require_admin,
    require_csrf,
    reset_admin_password,
    revoke_admin_sessions,
    verify_admin_password,
)

ROOT = Path(__file__).resolve().parent
ADMIN_STATIC = ROOT / "static" / "admin"
log = logging.getLogger("nova.admin.auth")
router = APIRouter()

# SQLite is local to this project; this does not connect to or modify Nova's booking DB.
initialize_admin_auth()


class LoginPayload(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class ForgotPasswordPayload(BaseModel):
    email: str = Field(min_length=3, max_length=254)


class ResetPasswordPayload(BaseModel):
    token: str = Field(min_length=40, max_length=200)
    password: str = Field(min_length=12, max_length=128)


@router.get("/admin/assets/{asset_name}", include_in_schema=False)
async def admin_asset(asset_name: str):
    allowed = {"style.css", "login.js", "reset.js"}
    if asset_name not in allowed:
        raise HTTPException(status_code=404, detail="Asset not found.")
    return FileResponse(ADMIN_STATIC / asset_name, headers={"Cache-Control": "public, max-age=3600", "X-Content-Type-Options": "nosniff"})


def _page(filename: str) -> FileResponse:
    path = ADMIN_STATIC / filename
    return FileResponse(
        path,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, private",
            "Pragma": "no-cache",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Referrer-Policy": "same-origin",
        },
    )


def _send_reset_email(to_email: str, reset_url: str) -> None:
    api_key = os.getenv("RESEND_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("RESEND_API_KEY is not configured in the root .env file.")
    sender = os.getenv("EMAIL_FROM", "Nova Hotel Admin <onboarding@resend.dev>").strip()
    safe_url = html.escape(reset_url, quote=True)
    payload = {
        "from": sender,
        "to": [to_email],
        "subject": "Reset your Nova Hotel admin password",
        "html": (
            "<div style='font-family:Arial,sans-serif;max-width:560px;margin:auto;color:#17232d'>"
            "<h2>Nova Hotel Admin</h2><p>We received a request to reset your admin password.</p>"
            f"<p><a href='{safe_url}' style='display:inline-block;padding:12px 18px;background:#14232d;color:#fff;text-decoration:none;border-radius:8px'>Reset password</a></p>"
            "<p>This link expires in the configured reset window and can be used only once. If you did not request this, ignore this email.</p>"
            "</div>"
        ),
        "text": f"Reset your Nova Hotel admin password using this one-time link: {reset_url}\nThis link expires in the configured reset window.",
    }
    response = httpx.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=httpx.Timeout(15.0, connect=5.0),
    )
    if response.status_code >= 300:
        # Do not log reset links or API keys.
        log.error("Resend email delivery failed: status=%s response=%s", response.status_code, response.text[:500])
        raise RuntimeError("The email provider rejected the reset email.")


@router.get("/admin", include_in_schema=False)
@router.get("/admin/", include_in_schema=False)
async def admin_login_page(request: Request):
    try:
        admin_id = request.session.get("admin_id")
        if admin_id:
            return RedirectResponse("/admin/dashboard", status_code=303)
    except AssertionError:
        # This indicates middleware was not registered; fail clearly rather than leaking a page.
        log.exception("Session middleware is not configured for the admin portal")
    return _page("login.html")


@router.get("/admin/reset-password", include_in_schema=False)
async def admin_reset_page():
    return _page("reset.html")


@router.get("/admin/dashboard", include_in_schema=False)
async def admin_dashboard(request: Request):
    admin_id = request.session.get("admin_id")
    if not admin_id:
        return RedirectResponse("/admin", status_code=303)
    current = await require_admin(request)
    if current:
        return _page("dashboard.html")
    return RedirectResponse("/admin", status_code=303)


@router.post("/admin/api/login")
async def admin_login(payload: LoginPayload, request: Request):
    consume_rate_limit(request, "admin-login", limit=6, window_seconds=15 * 60)
    email = payload.email.strip().lower()
    admin = get_admin_for_login(email)
    valid = bool(admin and admin["is_active"] and verify_admin_password(payload.password, admin["password_hash"]))
    if not valid:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    # Clear any prior session data to avoid session fixation, then issue a fresh CSRF token.
    request.session.clear()
    request.session.update(
        {
            "admin_id": int(admin["id"]),
            "auth_version": int(admin["auth_version"]),
            "admin_name": str(admin["name"]),
            "csrf_token": secrets.token_urlsafe(32),
            "issued_at": int(time.time()),
        }
    )
    return {"ok": True, "name": admin["name"], "redirect": "/admin/dashboard"}


@router.post("/admin/api/logout")
async def admin_logout(request: Request, admin: dict = Depends(require_admin), _csrf: None = Depends(require_csrf)):
    # Incrementing auth_version invalidates any other active sessions for this account too.
    revoke_admin_sessions(int(admin["id"]))
    request.session.clear()
    return {"ok": True, "redirect": "/admin"}


@router.get("/admin/api/session")
async def admin_session(request: Request, admin: dict = Depends(require_admin)):
    return {
        "authenticated": True,
        "name": admin["name"],
        "email": admin["email"],
        "csrf_token": request.session.get("csrf_token", ""),
    }


@router.post("/admin/api/forgot-password")
async def forgot_password(payload: ForgotPasswordPayload, request: Request):
    consume_rate_limit(request, "admin-forgot", limit=4, window_seconds=60 * 60)
    email = payload.email.strip().lower()
    # Same response for known and unknown emails to prevent account enumeration.
    from admin_auth import _normal_email, _db

    try:
        email = _normal_email(email)
    except HTTPException:
        return {"message": "If this address belongs to an active admin account, a reset email will be sent."}

    with _db() as conn:
        admin = conn.execute(
            "SELECT id,email,is_active FROM admins WHERE email=? COLLATE NOCASE", (email,)
        ).fetchone()
    if admin and admin["is_active"]:
        ttl_minutes = int(os.getenv("ADMIN_RESET_TOKEN_MINUTES", "20"))
        if not 5 <= ttl_minutes <= 60:
            ttl_minutes = 20
        token = create_reset_token(int(admin["id"]), ttl_minutes=ttl_minutes)
        configured_base = os.getenv("APP_BASE_URL", "").strip().rstrip("/")
        if not configured_base:
            configured_base = str(request.base_url).rstrip("/")
        reset_url = f"{configured_base}/admin/reset-password?token={token}"
        try:
            await run_in_threadpool(_send_reset_email, str(admin["email"]), reset_url)
        except Exception:
            log.exception("Could not send admin password reset email")
            # Do not reveal whether this email belongs to an admin account.
    return {"message": "If this address belongs to an active admin account, a reset email will be sent."}


@router.post("/admin/api/reset-password")
async def reset_password(payload: ResetPasswordPayload, request: Request):
    consume_rate_limit(request, "admin-reset", limit=6, window_seconds=15 * 60)
    if not reset_admin_password(payload.token, payload.password):
        raise HTTPException(status_code=400, detail="This reset link is invalid, expired, or already used.")
    return {"message": "Password updated. Please sign in with your new password."}


@router.get("/admin/api/health")
async def admin_auth_health():
    return {"status": "ok", "service": "nova-admin-auth"}
