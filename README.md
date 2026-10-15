# Central Single Sign-On (SSO) & Identity Service

A lightweight, high-performance Centralized Identity Provider and Single Sign-On (SSO) service built for multi-platform environments including **e-Agrology (Form Builder)**, **Agrotutor**, and future interconnected web applications.

---

## 📌 Architecture & Design Philosophy

1. **Centralized Identity & Global Roles**:
   * All user accounts are created and managed in the central SSO service.
   * SSO manages two universal **Global Roles**:
     * **Administrator (`admin`)**: Access to administrative capabilities across platforms and full access to the SSO Management Portal.
     * **Standard User (`standard`)**: Standard end-user access to connected applications.
2. **Platform-Isolated Subroles & Permissions**:
   * Client applications (e-Agrology, Agrotutor) manage their own internal subroles and granular permissions locally (e.g. *Project Manager*, *Surveyor*, *Reviewer* in Form Builder; *Logic Manager*, *Advisory Manager* in Agrotutor).
   * SSO validates credentials and provides the unified user identity (`user_id`, `email`, `username`, `global_role`). The client application resolves project assignments and role permissions within its own database.
3. **No Cross-Platform User Duplication**:
   * Users sign in using their central credentials. Client applications automatically synchronize/upsert local user records on successful authentication via cascading updates.

---

## 🛠️ Tech Stack

| Component | Technology | Description |
| :--- | :--- | :--- |
| **Backend Framework** | [FastAPI](https://fastapi.tiangolo.com/) (`v0.115.6`) | Asynchronous, high-throughput REST API framework |
| **ASGI Web Server** | [Uvicorn](https://www.uvicorn.org/) (`v0.34.0`) | Lightning-fast ASGI server with auto-reload |
| **Database** | [PostgreSQL](https://www.postgresql.org/) (`sso_db`) | Relational database for central identity and platform registry |
| **Database Driver** | [psycopg2](https://www.psycopg.org/) | Connection-pooled PostgreSQL driver (`ThreadedConnectionPool`) |
| **Security & Hashing** | [bcrypt](https://pypi.org/project/bcrypt/) (`v4.2.1`) | Salted password hashing for credentials |
| **Tokens & Sessions** | [PyJWT](https://pyjwt.readthedocs.io/) (`v2.10.1`) | Stateless JSON Web Tokens signed with HMAC-SHA256 (`HS256`) |
| **Data Validation** | [Pydantic v2](https://docs.pydantic.dev/) | Strongly typed request schemas and settings validation |
| **Admin UI & API Hub** | Vanilla HTML5 / Modern CSS / JS | Built-in zero-dependency management dashboard and interactive API Hub |

---

## 📁 Project Directory Structure

```text
SSO/
├── app/
│   ├── routers/
│   │   ├── auth.py          # Login, token verification, session claims
│   │   ├── users.py         # User directory CRUD, passwords, global roles
│   │   └── platforms.py     # Connected applications & allowed domains registry
│   ├── static/              # Embedded Management Console & API Hub SPA
│   │   ├── index.html       # Single-Page Application interface
│   │   ├── styles.css       # Modern CSS design system
│   │   └── app.js           # Frontend interactivity, API Hub filtering
│   ├── bootstrap.py         # Initial database seeding (admin, default apps)
│   ├── config.py            # Pydantic environment configuration
│   ├── database.py          # PostgreSQL thread-pooled connection manager
│   ├── schema.sql           # Core database schema DDL
│   └── security.py          # Password hashing, JWT creation & verification
├── .env.example             # Template for environment variables
├── requirements.txt         # Python package dependencies
├── run.py                   # Server entrypoint script (runs on port 8005)
└── setup.sh                 # Automated server installer and .env generator
```

---

## 🚀 Quickstart & Server Setup

### Method 1: Automated Setup (`setup.sh`) — Recommended

The included [`setup.sh`](setup.sh) script automates virtual environment creation, dependency installation, `.env` generation, database initialization, and optional `systemd` service setup.

#### 1. Run with Command-Line Arguments:
```bash
cd SSO

./setup.sh \
  --db-host "localhost" \
  --db-port "5432" \
  --db-name "sso_db" \
  --db-user "postgres" \
  --db-pass "your_db_password" \
  --sso-port "8005" \
  --admin-email "admin@example.org" \
  --admin-pass "Admin@12345"
```

#### 2. Run with Environment Variables:
```bash
DB_HOST=localhost DB_NAME=sso_db DB_USER=postgres DB_PASSWORD=your_password SSO_PORT=8005 ./setup.sh
```

#### 3. Linux Production Deploy (One-Shot with Systemd):
```bash
sudo ./setup.sh \
  --db-host "127.0.0.1" \
  --db-name "sso_db" \
  --db-user "postgres" \
  --db-pass "your_password" \
  --sso-port "8005" \
  --systemd \
  --start
```

#### `setup.sh` Available Options:
| Option | Default | Description |
| :--- | :--- | :--- |
| `--db-host <host>` | `localhost` | PostgreSQL host |
| `--db-port <port>` | `5432` | PostgreSQL port |
| `--db-name <name>` | `sso_db` | Database name |
| `--db-user <user>` | Current user / `postgres` | Database user |
| `--db-pass <password>` | `""` | Database password |
| `--sso-port <port>` | `8005` | SSO HTTP listen port |
| `--sso-host <host>` | `0.0.0.0` | Bind host address |
| `--jwt-secret <key>` | Auto-generated 64-char hex | Secret key for JWT signing |
| `--cors-origins <urls>`| Standard app domains | Comma-separated allowed CORS origins |
| `--admin-email <email>`| `admin@example.org` | Initial administrator email |
| `--admin-pass <pass>` | `Admin@12345` | Initial administrator password |
| `--systemd` | Disabled | Installs `/etc/systemd/system/sso.service` |
| `--start` | Disabled | Starts the service immediately |

---

### Method 2: Manual Setup

#### 1. Create the PostgreSQL Database
```bash
createdb -U postgres sso_db
```

#### 2. Create Virtual Environment & Install Dependencies
```bash
cd SSO
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt
```

#### 3. Create Configuration File (`.env`)
Copy `.env.example` to `.env` and fill in your values:
```bash
cp .env.example .env
```
Example `.env`:
```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=sso_db
DB_USER=postgres
DB_PASSWORD=your_password
SSO_PORT=8005
JWT_SECRET=your-secure-random-secret-key-32-chars-minimum
```

#### 4. Run the Server
```bash
./venv/bin/python run.py
```
* **SSO Portal & API:** [http://localhost:8005](http://localhost:8005)
* **API Documentation (Swagger):** [http://localhost:8005/docs](http://localhost:8005/docs)
* **Health Check:** [http://localhost:8005/api/sso/health](http://localhost:8005/api/sso/health)

---

## 🌐 Port Mapping Across Connected Applications

To avoid port conflicts during concurrent local development and server hosting:

| Application | Service | Port | Default URL |
| :--- | :--- | :--- | :--- |
| **Central SSO** | Portal & API | **`8005`** | `http://localhost:8005` |
| **Form Builder (e-Agrology)** | Backend API | **`8000`** | `http://localhost:8000` |
| **Form Builder (e-Agrology)** | Frontend UI | **`5173`** | `http://localhost:5173` |
| **Agrotutor** | Backend API | **`8001`** | `http://localhost:8001` |
| **Agrotutor** | Frontend UI | **`5174`** | `http://localhost:5174` |
| **Agrotutor** | GenAI / Flow Studio | **`8003`** | `http://localhost:8003` |

---

## 🔗 Connecting Client Applications to SSO

To connect an application (like e-Agrology or Agrotutor) to Central SSO, add the following environment variables to the client application's `.env`:

### For e-Agrology / Form Builder:
```env
SSO_ENABLED=true
SSO_API_URL=http://localhost:8005
SSO_APP_ID=eagrology
SSO_API_KEY=eagrology-api-secret-key-2026
```

### For Agrotutor:
```env
SSO_ENABLED=true
SSO_API_URL=http://localhost:8005
SSO_APP_ID=agrotutor
SSO_API_KEY=agrotutor-api-secret-key-2026
```

*(In production, replace `http://localhost:8005` with your live SSO URL, e.g. `https://sso.indevconsultancy.in`).*

---

## 📡 API Reference Summary

### Authentication (`/api/sso/auth`)
* `POST /api/sso/auth/login`: Authenticate platform users (accepts `identifier` [email/username], `password`, and `app_id`). Returns JWT access token and user profile.
* `POST /api/sso/auth/admin-login`: Admin-only authentication for the central SSO management dashboard.
* `POST /api/sso/auth/verify`: Validate a JWT token and retrieve active user profile and global role.
* `GET /api/sso/auth/me`: Validate Bearer token passed in `Authorization` header.

### User Directory (`/api/sso/users`)
* `GET /api/sso/users`: List all users with filtering by search query or global role. Requires `X-SSO-Api-Key` or Admin Token.
* `POST /api/sso/users`: Provision a new central user (`email`, `username`, `password`, `full_name`, `global_role_id`).
* `GET /api/sso/users/{user_id}`: Fetch user profile details.
* `PUT /api/sso/users/{user_id}`: Update user metadata, global role, or active status.
* `POST /api/sso/users/{user_id}/reset-password`: Set a new password for a user.
* `DELETE /api/sso/users/{user_id}`: Deactivate or delete user account.

### Platforms & Domains (`/api/sso/platforms`)
* `GET /api/sso/platforms`: List all registered client platforms and their allowed domains.
* `POST /api/sso/platforms`: Register a new client platform with allowed redirect/CORS domains.
* `PUT /api/sso/platforms/{app_id}`: Update platform domains or status.
* `DELETE /api/sso/platforms/{app_id}`: Unlink and remove a connected platform.

### Health
* `GET /api/sso/health`: Return service health status and active port.

---

## 🔒 Production Nginx Reverse Proxy Example

When hosting on a company server with SSL, configure Nginx as a reverse proxy:

```nginx
server {
    listen 80;
    server_name sso.indevconsultancy.in;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name sso.indevconsultancy.in;

    ssl_certificate /etc/letsencrypt/live/sso.indevconsultancy.in/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/sso.indevconsultancy.in/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8005;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## 👥 Default Initial Admin Credentials
* **Email:** `admin@example.org`
* **Username:** `admin`
* **Password:** `Admin@12345`
* **Global Role:** `Administrator`
