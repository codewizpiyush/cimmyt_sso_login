"""SSO Cryptographic, JWT & Admin Guard Utilities."""
from datetime import datetime, timedelta, timezone
import secrets
from typing import Any, Dict, Optional

import bcrypt
from fastapi import Header, HTTPException, status
import jwt

from app.config import settings


def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    pw_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(pw_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )
    except Exception:
        return False


def create_jwt_token(payload: Dict[str, Any], expires_hours: Optional[int] = None) -> str:
    """Issue a signed JWT token containing user identity, roles, and permissions."""
    hours = expires_hours or settings.jwt_expires_hours
    exp = datetime.now(timezone.utc) + timedelta(hours=hours)

    to_encode = payload.copy()
    to_encode.update({
        "exp": exp,
        "iat": datetime.now(timezone.utc),
        "iss": "sso.indevconsultancy.in",
    })
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a JWT token."""
    try:
        decoded = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            issuer="sso.indevconsultancy.in",
        )
        return decoded
    except Exception:
        return None


def generate_user_id() -> str:
    """Generate a clean user ID matching the platform format USR#####."""
    return f"USR{secrets.randbelow(90000) + 10000}"


def require_sso_admin(
    authorization: Optional[str] = Header(default=None),
    x_sso_api_key: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    """Dependency: Strict authorization check — only Administrators can access SSO management APIs."""
    if x_sso_api_key:
        from app.database import transaction
        with transaction() as cur:
            cur.execute("SELECT app_id, name FROM sso_client_app WHERE api_key = %s AND is_active = TRUE;", (x_sso_api_key,))
            client = cur.fetchone()
            if client:
                return {
                    "user_id": f"service:{client['app_id']}",
                    "email": f"{client['app_id']}@service.sso",
                    "username": client["app_id"],
                    "global_role": "admin",
                }

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sign in to the SSO Administration Portal to continue.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.split(" ", 1)[1].strip()
    payload = decode_jwt_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired. Please sign in again.",
        )

    user_id = payload.get("sub")
    global_role = payload.get("global_role") or payload.get("role")

    if global_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied: Only administrators have access to the SSO management console.",
        )

    return {
        "user_id": user_id,
        "email": payload.get("email"),
        "username": payload.get("username"),
        "global_role": global_role,
    }
