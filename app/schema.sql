-- PostgreSQL Schema for Central SSO & Identity Provider
-- Clean Architecture: Connected Platforms, Global Roles, and Central Users Directory.
-- Platform-specific subroles & permissions are kept strictly isolated on each client platform.

-- 1. Connected Client Platforms / Applications (e.g. e-Agrology, Agrotutor)
CREATE TABLE IF NOT EXISTS sso_client_app (
    app_id          VARCHAR(50) PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    description     TEXT,
    allowed_domains TEXT NOT NULL,
    api_key         VARCHAR(100) UNIQUE NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_on      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_on      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Global Roles (Consistent across all connected platforms: Administrator & Standard User)
CREATE TABLE IF NOT EXISTS sso_global_role (
    role_id     VARCHAR(50) PRIMARY KEY,
    name        VARCHAR(50) UNIQUE NOT NULL,
    label       VARCHAR(100) NOT NULL,
    description TEXT,
    is_system   BOOLEAN NOT NULL DEFAULT TRUE,
    created_on  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. SSO Central Users Directory
CREATE TABLE IF NOT EXISTS sso_user (
    user_id       VARCHAR(50) PRIMARY KEY,
    email         VARCHAR(255) UNIQUE NOT NULL,
    username      VARCHAR(100) UNIQUE,
    phone         VARCHAR(30) UNIQUE,
    full_name     VARCHAR(150),
    password_hash VARCHAR(255) NOT NULL,
    global_role_id VARCHAR(50) NOT NULL REFERENCES sso_global_role(role_id),
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    created_on    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_on    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by    VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS idx_sso_user_email ON sso_user(email);
CREATE INDEX IF NOT EXISTS idx_sso_user_username ON sso_user(username);
