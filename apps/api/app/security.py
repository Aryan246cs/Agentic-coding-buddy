"""Passwords and tokens.

Two separate token audiences, and they must never be interchangeable:

  * `platform` — our customer, signed in to build things.
  * `app:<project_id>` — one of their staff, signed in to one published app.

The audience is baked into the token and checked on decode, so a token minted
for one published app cannot be replayed against another app or against the
platform dashboard.
"""

from __future__ import annotations

import hmac
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import bcrypt
import jwt

from app.config import get_settings

ALGORITHM = "HS256"
PLATFORM_AUDIENCE = "platform"

#: bcrypt silently truncates at 72 bytes, so refuse longer input rather than
#: accept a password whose tail is ignored.
MAX_PASSWORD_BYTES = 72
MIN_PASSWORD_LENGTH = 8


class AuthError(Exception):
    """A token or credential was not acceptable."""


def app_audience(project_id: str) -> str:
    return f"app:{project_id}"


# --------------------------------------------------------------------------
# Passwords
# --------------------------------------------------------------------------


def password_problem(password: str) -> str | None:
    """Why this password is unacceptable, or None if it is fine."""
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        return "Password is too long. Please use something shorter."
    return None


def hash_password(password: str) -> str:
    problem = password_problem(password)
    if problem:
        raise ValueError(problem)
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    encoded = password.encode("utf-8")
    if len(encoded) > MAX_PASSWORD_BYTES:
        return False
    try:
        return bcrypt.checkpw(encoded, password_hash.encode("utf-8"))
    except ValueError:
        # A malformed stored hash must read as "wrong password", not crash.
        return False


def tokens_equal(left: str, right: str) -> bool:
    """Constant-time compare, for invite tokens and similar secrets."""
    return hmac.compare_digest(left.encode("utf-8"), right.encode("utf-8"))


# --------------------------------------------------------------------------
# Tokens
# --------------------------------------------------------------------------


def create_token(
    subject: str,
    audience: str,
    *,
    extra: dict[str, Any] | None = None,
    hours: int | None = None,
) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "aud": audience,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=hours or settings.access_token_hours)).timestamp()),
        **(extra or {}),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_token(token: str, audience: str) -> dict[str, Any]:
    """Decode and verify, insisting on the expected audience."""
    try:
        return jwt.decode(
            token,
            get_settings().secret_key,
            algorithms=[ALGORITHM],
            audience=audience,
            options={"require": ["sub", "aud", "exp"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise AuthError("Your session has expired. Please sign in again.") from exc
    except jwt.InvalidAudienceError as exc:
        raise AuthError("This session is not valid here.") from exc
    except jwt.InvalidTokenError as exc:
        raise AuthError("Your session is not valid. Please sign in again.") from exc


def create_platform_token(user_id: str, email: str) -> str:
    return create_token(user_id, PLATFORM_AUDIENCE, extra={"email": email})


def create_app_token(app_user_id: str, project_id: str, role: str) -> str:
    return create_token(
        app_user_id,
        app_audience(project_id),
        extra={"project_id": project_id, "role": role},
    )


TokenKind = Literal["platform", "app"]
