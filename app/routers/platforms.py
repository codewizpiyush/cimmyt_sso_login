"""SSO Connected Platforms & Domains Management Router."""
import re
import secrets
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.database import transaction
from app.security import require_sso_admin

router = APIRouter(prefix="/api/sso/platforms", tags=["SSO Platforms"])


class CreatePlatformRequest(BaseModel):
    app_id: str
    name: str
    description: Optional[str] = None
    allowed_domains: str  # Comma-separated domains e.g. "https://revamp.agrotutor.co,http://localhost:3000"


class UpdatePlatformRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    allowed_domains: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("")
def list_platforms(admin: Dict[str, Any] = Depends(require_sso_admin)):
    """List all registered client platforms and their allowed domains."""
    with transaction() as cur:
        cur.execute(
            """
            SELECT p.*
            FROM sso_client_app p
            ORDER BY p.name ASC;
            """
        )
        return {"platforms": [dict(r) for r in cur.fetchall()]}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_platform(req: CreatePlatformRequest, admin: Dict[str, Any] = Depends(require_sso_admin)):
    """Register a new platform and configure its allowed domains."""
    clean_app_id = re.sub(r"[^a-z0-9_-]", "", req.app_id.strip().lower())
    if not clean_app_id:
        raise HTTPException(status_code=400, detail="Platform app_id must be alphanumeric.")

    api_key = f"{clean_app_id}-{secrets.token_hex(16)}"

    with transaction() as cur:
        cur.execute("SELECT app_id FROM sso_client_app WHERE app_id = %s;", (clean_app_id,))
        if cur.fetchone():
            raise HTTPException(status_code=409, detail=f"Platform '{clean_app_id}' already registered.")

        cur.execute(
            """
            INSERT INTO sso_client_app (app_id, name, description, allowed_domains, api_key, is_active)
            VALUES (%s, %s, %s, %s, %s, TRUE);
            """,
            (clean_app_id, req.name.strip(), req.description or "", req.allowed_domains.strip(), api_key),
        )

        cur.execute("SELECT * FROM sso_client_app WHERE app_id = %s;", (clean_app_id,))
        return dict(cur.fetchone())


@router.put("/{app_id}")
def update_platform(app_id: str, req: UpdatePlatformRequest, admin: Dict[str, Any] = Depends(require_sso_admin)):
    """Update platform metadata, allowed domains, or active status."""
    with transaction() as cur:
        cur.execute("SELECT * FROM sso_client_app WHERE app_id = %s;", (app_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Platform not found.")

        updates = []
        params = []
        if req.name is not None:
            updates.append("name = %s")
            params.append(req.name.strip())
        if req.description is not None:
            updates.append("description = %s")
            params.append(req.description.strip())
        if req.allowed_domains is not None:
            updates.append("allowed_domains = %s")
            params.append(req.allowed_domains.strip())
        if req.is_active is not None:
            updates.append("is_active = %s")
            params.append(req.is_active)

        if updates:
            updates.append("updated_on = CURRENT_TIMESTAMP")
            sql = f"UPDATE sso_client_app SET {', '.join(updates)} WHERE app_id = %s;"
            params.append(app_id)
            cur.execute(sql, params)

        cur.execute("SELECT * FROM sso_client_app WHERE app_id = %s;", (app_id,))
        return dict(cur.fetchone())


@router.delete("/{app_id}")
def delete_platform(app_id: str, admin: Dict[str, Any] = Depends(require_sso_admin)):
    """Delete a connected platform and its subroles."""
    with transaction() as cur:
        cur.execute("SELECT app_id FROM sso_client_app WHERE app_id = %s;", (app_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Platform not found.")

        cur.execute("DELETE FROM sso_client_app WHERE app_id = %s;", (app_id,))
        return {"deleted": True, "app_id": app_id}
