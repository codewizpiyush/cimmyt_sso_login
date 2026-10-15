"""SSO User Management Router.

Users are created here with their identity and Global Role (Administrator or Standard User).
Platform-specific subroles (e.g. project manager, surveyor on e-Agrology; logic manager on Agrotutor)
remain strictly isolated on the respective client platforms.
"""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.database import transaction
from app.security import generate_user_id, hash_password, require_sso_admin

router = APIRouter(prefix="/api/sso/users", tags=["SSO Users"])


class CreateUserRequest(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = None
    username: Optional[str] = None
    phone: Optional[str] = None
    global_role_id: str = "standard"  # 'admin' or 'standard'


class UpdateUserRequest(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    username: Optional[str] = None
    phone: Optional[str] = None
    global_role_id: Optional[str] = None
    is_active: Optional[bool] = None


class ResetPasswordRequest(BaseModel):
    new_password: str


def _fetch_user_dict(cur, user_id: str) -> Optional[Dict[str, Any]]:
    """Fetch complete user dict using the active cursor."""
    cur.execute(
        """
        SELECT u.user_id, u.email, u.username, u.phone, u.full_name,
               u.global_role_id, u.is_active, u.created_on, u.updated_on, u.created_by,
               r.name AS global_role, r.label AS global_role_label, r.description AS role_description
        FROM sso_user u
        JOIN sso_global_role r ON r.role_id = u.global_role_id
        WHERE u.user_id = %s;
        """,
        (user_id,),
    )
    row = cur.fetchone()
    if not row:
        return None

    user = dict(row)
    user.pop("password_hash", None)
    return user


@router.get("")
def list_users(
    search: Optional[str] = None,
    global_role: Optional[str] = None,
    include_inactive: bool = True,
    admin: Dict[str, Any] = Depends(require_sso_admin),
):
    """List all users in the SSO directory with their global role."""
    with transaction() as cur:
        query = """
            SELECT u.user_id, u.email, u.username, u.phone, u.full_name,
                   u.global_role_id, u.is_active, u.created_on, u.updated_on,
                   r.name AS global_role, r.label AS global_role_label
            FROM sso_user u
            JOIN sso_global_role r ON r.role_id = u.global_role_id
            WHERE 1=1
        """
        params: List[Any] = []

        if not include_inactive:
            query += " AND u.is_active = TRUE"

        if global_role:
            query += " AND u.global_role_id = %s"
            params.append(global_role)

        if search:
            query += """ AND (
                LOWER(u.email) LIKE %s OR
                LOWER(u.username) LIKE %s OR
                LOWER(u.full_name) LIKE %s OR
                u.phone LIKE %s
            )"""
            s = f"%{search.lower().strip()}%"
            params.extend([s, s, s, s])

        query += " ORDER BY u.created_on DESC;"
        cur.execute(query, params)
        rows = cur.fetchall()

        users = [dict(r) for r in rows]
        return {"users": users, "count": len(users)}


@router.get("/{user_id}")
def get_user(user_id: str, admin: Dict[str, Any] = Depends(require_sso_admin)):
    """Retrieve full user details."""
    with transaction() as cur:
        user = _fetch_user_dict(cur, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")
        return user


@router.post("", status_code=status.HTTP_201_CREATED)
def create_user(req: CreateUserRequest, admin: Dict[str, Any] = Depends(require_sso_admin)):
    """Create a new user with a global role (Administrator or Standard User)."""
    clean_email = req.email.strip().lower()
    clean_username = req.username.strip().lower() if req.username else None
    clean_phone = req.phone.strip() if req.phone else None

    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")

    with transaction() as cur:
        cur.execute("SELECT user_id FROM sso_user WHERE LOWER(email) = %s LIMIT 1;", (clean_email,))
        if cur.fetchone():
            raise HTTPException(status_code=409, detail=f"Email '{clean_email}' already exists.")

        if clean_username:
            cur.execute("SELECT user_id FROM sso_user WHERE LOWER(username) = %s LIMIT 1;", (clean_username,))
            if cur.fetchone():
                raise HTTPException(status_code=409, detail=f"Username '{clean_username}' already exists.")

        # Validate global role
        global_role_id = req.global_role_id.strip().lower()
        if global_role_id not in ("admin", "standard"):
            global_role_id = "standard"

        user_id = generate_user_id()
        hashed = hash_password(req.password)

        cur.execute(
            """
            INSERT INTO sso_user (user_id, email, username, phone, full_name, password_hash, global_role_id, is_active, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE, %s);
            """,
            (user_id, clean_email, clean_username, clean_phone, req.full_name or clean_username or clean_email,
             hashed, global_role_id, admin["email"]),
        )

        return _fetch_user_dict(cur, user_id)


@router.put("/{user_id}")
def update_user(user_id: str, req: UpdateUserRequest, admin: Dict[str, Any] = Depends(require_sso_admin)):
    """Update user profile fields, global role, or active status."""
    with transaction() as cur:
        cur.execute("SELECT * FROM sso_user WHERE user_id = %s;", (user_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="User not found.")

        updates = []
        params = []

        if req.full_name is not None:
            updates.append("full_name = %s")
            params.append(req.full_name.strip())

        if req.email is not None:
            clean_email = req.email.strip().lower()
            cur.execute("SELECT user_id FROM sso_user WHERE LOWER(email) = %s AND user_id != %s;", (clean_email, user_id))
            if cur.fetchone():
                raise HTTPException(status_code=409, detail=f"Email '{clean_email}' already in use.")
            updates.append("email = %s")
            params.append(clean_email)

        if req.username is not None:
            clean_username = req.username.strip().lower() if req.username else None
            if clean_username:
                cur.execute("SELECT user_id FROM sso_user WHERE LOWER(username) = %s AND user_id != %s;", (clean_username, user_id))
                if cur.fetchone():
                    raise HTTPException(status_code=409, detail=f"Username '{clean_username}' already in use.")
            updates.append("username = %s")
            params.append(clean_username)

        if req.phone is not None:
            updates.append("phone = %s")
            params.append(req.phone.strip() if req.phone else None)

        if req.global_role_id is not None:
            g_role = req.global_role_id.strip().lower()
            if g_role in ("admin", "standard"):
                updates.append("global_role_id = %s")
                params.append(g_role)

        if req.is_active is not None:
            updates.append("is_active = %s")
            params.append(req.is_active)

        if updates:
            updates.append("updated_on = CURRENT_TIMESTAMP")
            sql = f"UPDATE sso_user SET {', '.join(updates)} WHERE user_id = %s;"
            params.append(user_id)
            cur.execute(sql, params)

        return _fetch_user_dict(cur, user_id)


@router.post("/{user_id}/reset-password")
def reset_password(user_id: str, req: ResetPasswordRequest, admin: Dict[str, Any] = Depends(require_sso_admin)):
    """Set new password for a user."""
    if len(req.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")

    with transaction() as cur:
        cur.execute("SELECT user_id FROM sso_user WHERE user_id = %s;", (user_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="User not found.")

        hashed = hash_password(req.new_password)
        cur.execute("UPDATE sso_user SET password_hash = %s, updated_on = CURRENT_TIMESTAMP WHERE user_id = %s;", (hashed, user_id))
        return {"success": True, "message": "Password updated successfully."}


@router.delete("/{user_id}")
def delete_user(user_id: str, hard_delete: bool = False, admin: Dict[str, Any] = Depends(require_sso_admin)):
    """Deactivate or delete user."""
    with transaction() as cur:
        cur.execute("SELECT user_id FROM sso_user WHERE user_id = %s;", (user_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="User not found.")

        if hard_delete:
            cur.execute("DELETE FROM sso_user WHERE user_id = %s;", (user_id,))
            return {"deleted": True, "user_id": user_id}
        else:
            cur.execute("UPDATE sso_user SET is_active = FALSE, updated_on = CURRENT_TIMESTAMP WHERE user_id = %s;", (user_id,))
            return {"deactivated": True, "user_id": user_id}
