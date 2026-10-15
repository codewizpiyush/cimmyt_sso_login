"""SSO Initial Seed Data & Bootstrap for PostgreSQL."""
import logging
from app.config import settings
from app.database import transaction
from app.security import hash_password

logger = logging.getLogger(__name__)

# Initial Connected Applications
INITIAL_APPS = [
    {
        "app_id": "eagrology",
        "name": "e-Agrology FormBuilder",
        "description": "Form building, data collection and reporting platform",
        "allowed_domains": (
            "https://eagrology-revamp.indevconsultancy.in,"
            "http://localhost:5173,http://localhost:8000,"
            "http://127.0.0.1:5173,http://127.0.0.1:8000"
        ),
        "api_key": "eagrology-api-secret-key-2026",
    },
    {
        "app_id": "agrotutor",
        "name": "Agrotutor Platform",
        "description": "Agricultural advisory, logic engines and tutoring platform",
        "allowed_domains": (
            "https://revamp.agrotutor.co,"
            "http://localhost:5174,http://127.0.0.1:5174,"
            "http://localhost:8001,http://127.0.0.1:8001,"
            "http://localhost:3000,http://127.0.0.1:3000"
        ),
        "api_key": "agrotutor-api-secret-key-2026",
    },
]

# Global Roles (common across all platforms: Administrator & Standard User)
GLOBAL_ROLES = [
    {
        "role_id": "admin",
        "name": "admin",
        "label": "Administrator",
        "description": "Full administrative access across all connected platforms and SSO portal management.",
        "is_system": True,
    },
    {
        "role_id": "standard",
        "name": "standard",
        "label": "Standard User",
        "description": "Standard participant. Platform capabilities are determined by assigned local subroles.",
        "is_system": True,
    },
]


def seed_data() -> None:
    """Idempotently seed connected platforms, global roles, and default admin account."""
    with transaction() as cur:
        # 1. Seed Connected Client Apps
        for app in INITIAL_APPS:
            cur.execute(
                """
                INSERT INTO sso_client_app (app_id, name, description, allowed_domains, api_key)
                VALUES (%(app_id)s, %(name)s, %(description)s, %(allowed_domains)s, %(api_key)s)
                ON CONFLICT (app_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    allowed_domains = EXCLUDED.allowed_domains;
                """,
                app,
            )

        # 2. Seed Global Roles
        for role in GLOBAL_ROLES:
            cur.execute(
                """
                INSERT INTO sso_global_role (role_id, name, label, description, is_system)
                VALUES (%(role_id)s, %(name)s, %(label)s, %(description)s, %(is_system)s)
                ON CONFLICT (role_id) DO UPDATE SET
                    label = EXCLUDED.label,
                    description = EXCLUDED.description;
                """,
                role,
            )

        # 3. Seed Default Admin User if absent
        cur.execute(
            "SELECT 1 FROM sso_user WHERE email = %s OR username = %s LIMIT 1;",
            (settings.initial_admin_email, settings.initial_admin_username),
        )
        if not cur.fetchone():
            hashed = hash_password(settings.initial_admin_password)
            cur.execute(
                """
                INSERT INTO sso_user (user_id, email, username, full_name, password_hash, global_role_id, is_active, created_by)
                VALUES ('USR00001', %s, %s, %s, %s, 'admin', TRUE, 'bootstrap');
                """,
                (settings.initial_admin_email, settings.initial_admin_username, 
                 settings.initial_admin_name, hashed),
            )
            logger.info("Created default global admin account: %s", settings.initial_admin_email)
