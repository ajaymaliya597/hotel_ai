"""Merge missing admin settings and create a persistent strong session secret."""
from __future__ import annotations

import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"
EXAMPLE_FILE = ROOT / ".env.example"

if not ENV_FILE.exists():
    raise SystemExit(".env is missing. Copy .env.example to .env first.")

lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
existing_keys = {
    line.split("=", 1)[0].strip()
    for line in lines
    if line.strip() and not line.lstrip().startswith("#") and "=" in line
}
# Migrate existing Nova .env files by adding only missing admin-specific settings.
if EXAMPLE_FILE.exists():
    for line in EXAMPLE_FILE.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
            continue
        key = line.split("=", 1)[0].strip()
        if key.startswith(("ADMIN_", "RESEND_API_KEY", "EMAIL_FROM", "APP_BASE_URL")) and key not in existing_keys:
            lines.append(line)
            existing_keys.add(key)

found_secret = False
updated: list[str] = []
for line in lines:
    if line.startswith("ADMIN_SESSION_SECRET="):
        found_secret = True
        current = line.split("=", 1)[1].strip()
        if len(current) < 48 or current.startswith("PASTE_"):
            line = "ADMIN_SESSION_SECRET=" + secrets.token_urlsafe(48)
    updated.append(line)
if not found_secret:
    updated.append("ADMIN_SESSION_SECRET=" + secrets.token_urlsafe(48))
ENV_FILE.write_text("\n".join(updated).rstrip() + "\n", encoding="utf-8")
print("Admin settings checked; session secret is present in .env.")
