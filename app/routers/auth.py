"""SSO Multi-Platform Authentication Router."""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel

from app.database import transaction
from app.security import (
    create_jwt_token,
    decode_jwt_token,
    verify_password,
)

router = APIRouter(prefix="/api/sso/auth", tags=["SSO Auth"])


class AdminLoginRequest(BaseModel):
    identifier: str  # Email or username
    password: str


class ClientLoginRequest(BaseModel):
    identifier: str  # Email, username, or phone
    password: str
    app_id: Optional[str] = "eagrology"  # 'eagrology', 'agrotutor', etc.


class VerifyRequest(BaseModel):
    token: str



@router.post("/admin-login")
def sso_admin_login(req: AdminLoginRequest):
    """Admin-only authentication for the SSO Management Portal."""
    clean_id = req.identifier.strip().lower()
    with transaction() as cur:
        cur.execute(
            """
            SELECT u.*, r.name AS role, r.label AS role_label
            FROM sso_user u
            JOIN sso_global_role r ON r.role_id = u.global_role_id
            WHERE LOWER(u.email) = %s OR LOWER(u.username) = %s
            LIMIT 1;
            """,
            (clean_id, clean_id),
        )
        row = cur.fetchone()

        if not row or not verify_password(req.password, row["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid administrator email/username or password.",
            )

        if not row["is_active"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This account has been deactivated.",
            )

        # STRICT CHECK: Only administrators can log in to the SSO portal
        if row["global_role_id"] != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access Denied: Only administrators have access to the SSO management console.",
            )

        token = create_jwt_token({
            "sub": row["user_id"],
            "email": row["email"],
            "username": row["username"],
            "global_role": "admin",
            "full_name": row["full_name"],
            "portal": "sso_admin",
        })

        return {
            "success": True,
            "token": token,
            "user": {
                "user_id": row["user_id"],
                "email": row["email"],
                "username": row["username"],
                "full_name": row["full_name"],
                "global_role": "admin",
                "role_label": row["role_label"],
            },
        }


@router.post("/login")
def platform_login(req: ClientLoginRequest):
    """Platform authentication endpoint for connected applications (e-Agrology, Agrotutor)."""
    clean_id = req.identifier.strip().lower()
    app_id = (req.app_id or "eagrology").strip().lower()

    with transaction() as cur:
        # Check platform exists and is active
        cur.execute("SELECT app_id, name FROM sso_client_app WHERE app_id = %s AND is_active = TRUE;", (app_id,))
        app_row = cur.fetchone()
        if not app_row:
            raise HTTPException(status_code=400, detail=f"Client application '{app_id}' is not recognized or active.")

        cur.execute(
            """
            SELECT u.*, r.name AS role, r.label AS role_label
            FROM sso_user u
            JOIN sso_global_role r ON r.role_id = u.global_role_id
            WHERE LOWER(u.email) = %s OR LOWER(u.username) = %s OR u.phone = %s
            LIMIT 1;
            """,
            (clean_id, clean_id, req.identifier.strip()),
        )
        row = cur.fetchone()

        if not row or not verify_password(req.password, row["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username, email, or password.",
            )

        if not row["is_active"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This account has been deactivated. Contact an administrator.",
            )

        user_id = row["user_id"]
        global_role = row["role"]  # "admin" or "standard"
        global_role_label = row["role_label"]

        user_profile = {
            "user_id": user_id,
            "email": row["email"],
            "username": row["username"],
            "phone": row["phone"],
            "full_name": row["full_name"],
            "global_role": global_role,
            "role": global_role,
            "role_label": global_role_label,
            "app_id": app_id,
            "is_active": bool(row["is_active"]),
        }

        token = create_jwt_token({
            "sub": user_id,
            "email": row["email"],
            "username": row["username"],
            "global_role": global_role,
            "app_id": app_id,
        })

        return {
            "success": True,
            "token": token,
            "user": user_profile,
        }


@router.post("/verify")
def sso_verify(req: VerifyRequest):
    """Validate a token and return refreshed user profile, subroles, and permissions."""
    payload = decode_jwt_token(req.token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is invalid or has expired.",
        )

    user_id = payload.get("sub")
    app_id = payload.get("app_id")

    with transaction() as cur:
        cur.execute(
            """
            SELECT u.*, r.name AS role, r.label AS role_label
            FROM sso_user u
            JOIN sso_global_role r ON r.role_id = u.global_role_id
            WHERE u.user_id = %s;
            """,
            (user_id,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="User no longer exists.")

        if not row["is_active"]:
            raise HTTPException(status_code=403, detail="Account is deactivated.")

        primary_role = row["role"]
        primary_role_label = row["role_label"]

        return {
            "valid": True,
            "user": {
                "user_id": user_id,
                "email": row["email"],
                "username": row["username"],
                "full_name": row["full_name"],
                "global_role": row["role"],
                "role": primary_role,
                "role_label": primary_role_label,
                "app_id": app_id,
                "subroles": [],
                "permissions": [],
                "is_active": bool(row["is_active"]),
            },
        }


@router.get("/me")
def sso_me(authorization: Optional[str] = Header(default=None)):
    """Get current user from Bearer token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization header.")
    token = authorization.split(" ", 1)[1].strip()
    return sso_verify(VerifyRequest(token=token))
