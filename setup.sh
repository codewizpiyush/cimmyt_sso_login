#!/usr/bin/env bash
# ==============================================================================
# Central SSO & Identity Service - Automated Server Setup & Environment Generator
# ==============================================================================
# This script sets up the Python virtual environment, installs dependencies,
# generates the production .env file, verifies the PostgreSQL database, and
# bootstraps the SSO database tables and initial administrator.
#
# Usage examples:
#   1. Interactive / Default:
#      ./setup.sh
#
#   2. With Environment Variables:
#      DB_HOST=localhost DB_NAME=sso_db DB_USER=postgres DB_PASSWORD=mysecret ./setup.sh
#
#   3. With Command-Line Flags:
#      ./setup.sh --db-host 127.0.0.1 --db-user postgres --db-pass mysecret --sso-port 8005
#
#   4. Install and enable as Linux systemd service:
#      sudo ./setup.sh --systemd --start
# ==============================================================================
set -euo pipefail

# Locate SSO directory
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

# Text Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1" >&2; }

# ------------------------------------------------------------------------------
# 1. Parse Arguments & Set Defaults
# ------------------------------------------------------------------------------
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-sso_db}"
DB_USER="${DB_USER:-$(whoami 2>/dev/null || echo 'postgres')}"
DB_PASSWORD="${DB_PASSWORD:-}"
SSO_HOST="${SSO_HOST:-0.0.0.0}"
SSO_PORT="${SSO_PORT:-8005}"
JWT_SECRET="${JWT_SECRET:-}"
CORS_ORIGINS="${CORS_ORIGINS:-https://eagrology-revamp.indevconsultancy.in,https://revamp.agrotutor.co,http://localhost:5173,http://localhost:5174,http://localhost:8000,http://localhost:8001}"
INITIAL_ADMIN_EMAIL="${INITIAL_ADMIN_EMAIL:-admin@example.org}"
INITIAL_ADMIN_USERNAME="${INITIAL_ADMIN_USERNAME:-admin}"
INITIAL_ADMIN_PASSWORD="${INITIAL_ADMIN_PASSWORD:-Admin@12345}"
INITIAL_ADMIN_NAME="${INITIAL_ADMIN_NAME:-Global Administrator}"
INSTALL_SYSTEMD=false
START_SERVICE=false

print_help() {
  echo "Usage: ./setup.sh [OPTIONS]"
  echo ""
  echo "Database Options:"
  echo "  --db-host <host>          PostgreSQL host (default: localhost)"
  echo "  --db-port <port>          PostgreSQL port (default: 5432)"
  echo "  --db-name <name>          Database name (default: sso_db)"
  echo "  --db-user <user>          Database username (default: current user / postgres)"
  echo "  --db-pass, --db-password  Database password"
  echo ""
  echo "SSO Server Options:"
  echo "  --sso-host <host>         Bind host (default: 0.0.0.0)"
  echo "  --sso-port <port>         Server port (default: 8005)"
  echo "  --jwt-secret <secret>     JWT signing secret (auto-generated if omitted)"
  echo "  --cors-origins <origins>  Comma-separated allowed origins"
  echo ""
  echo "Initial Admin Options:"
  echo "  --admin-email <email>     Admin email (default: admin@example.org)"
  echo "  --admin-user <username>   Admin username (default: admin)"
  echo "  --admin-pass <password>   Admin password (default: Admin@12345)"
  echo ""
  echo "System Options:"
  echo "  --systemd                 Install and enable systemd unit file (requires sudo)"
  echo "  --start                   Start the service immediately after setup"
  echo "  -h, --help                Show this help message"
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --db-host) DB_HOST="$2"; shift 2 ;;
    --db-port) DB_PORT="$2"; shift 2 ;;
    --db-name) DB_NAME="$2"; shift 2 ;;
    --db-user) DB_USER="$2"; shift 2 ;;
    --db-pass|--db-password) DB_PASSWORD="$2"; shift 2 ;;
    --sso-host) SSO_HOST="$2"; shift 2 ;;
    --sso-port) SSO_PORT="$2"; shift 2 ;;
    --jwt-secret) JWT_SECRET="$2"; shift 2 ;;
    --cors-origins) CORS_ORIGINS="$2"; shift 2 ;;
    --admin-email) INITIAL_ADMIN_EMAIL="$2"; shift 2 ;;
    --admin-user) INITIAL_ADMIN_USERNAME="$2"; shift 2 ;;
    --admin-pass) INITIAL_ADMIN_PASSWORD="$2"; shift 2 ;;
    --systemd) INSTALL_SYSTEMD=true; shift ;;
    --start) START_SERVICE=true; shift ;;
    -h|--help) print_help ;;
    *) log_error "Unknown parameter: $1"; print_help ;;
  esac
done

echo -e "${BOLD}=================================================================${NC}"
echo -e "${BOLD}     Central SSO & Identity Service - Server Setup Assistant     ${NC}"
echo -e "${BOLD}=================================================================${NC}"

# ------------------------------------------------------------------------------
# 2. Check Python Environment
# ------------------------------------------------------------------------------
log_info "Verifying Python runtime..."
PYTHON_CMD=""
for py in python3 python3.13 python3.12 python3.11 python3.10 python; do
  if command -v "$py" >/dev/null 2>&1; then
    VER="$($py -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
    MAJOR="$(echo "$VER" | cut -d'.' -f1)"
    MINOR="$(echo "$VER" | cut -d'.' -f2)"
    if [ "$MAJOR" -ge 3 ] && [ "$MINOR" -ge 10 ]; then
      PYTHON_CMD="$py"
      break
    fi
  fi
done

if [ -z "$PYTHON_CMD" ]; then
  log_error "Python 3.10 or higher is required. Please install python3 (e.g. apt install python3 python3-venv python3-pip)."
  exit 1
fi
log_success "Found compatible Python: $($PYTHON_CMD --version)"

# ------------------------------------------------------------------------------
# 3. Create Virtual Environment & Install Dependencies
# ------------------------------------------------------------------------------
VENV_DIR="$HERE/venv"
if [ ! -d "$VENV_DIR" ] || [ ! -f "$VENV_DIR/bin/python" ]; then
  log_info "Creating Python virtual environment in '$VENV_DIR'..."
  $PYTHON_CMD -m venv "$VENV_DIR" || {
    log_error "Failed to create virtualenv. On Ubuntu/Debian, run: sudo apt install python3-venv"
    exit 1
  }
fi

VENV_PYTHON="$VENV_DIR/bin/python"
VENV_PIP="$VENV_DIR/bin/pip"

log_info "Upgrading pip and installing dependencies from requirements.txt..."
"$VENV_PIP" install --upgrade pip --quiet
"$VENV_PIP" install -r "$HERE/requirements.txt" --quiet
log_success "All dependencies installed successfully."

# ------------------------------------------------------------------------------
# 4. Generate JWT Secret if missing
# ------------------------------------------------------------------------------
if [ -z "$JWT_SECRET" ]; then
  if [ -f "$HERE/.env" ]; then
    EXISTING_SECRET="$(grep -E '^JWT_SECRET=' "$HERE/.env" | cut -d'=' -f2- || true)"
    if [ -n "$EXISTING_SECRET" ] && [ "$EXISTING_SECRET" != "change-this-to-a-secure-random-secret-key-in-production" ]; then
      JWT_SECRET="$EXISTING_SECRET"
    fi
  fi
fi

if [ -z "$JWT_SECRET" ]; then
  log_info "Generating secure random 64-character JWT secret key..."
  JWT_SECRET="$("$VENV_PYTHON" -c "import secrets; print(secrets.token_hex(32))")"
fi

# ------------------------------------------------------------------------------
# 5. Generate / Overwrite .env File
# ------------------------------------------------------------------------------
ENV_FILE="$HERE/.env"
log_info "Writing production environment file to '$ENV_FILE'..."

cat > "$ENV_FILE" <<EOF
# ==============================================================================
# Central SSO & Identity Service - Environment Configuration
# Generated on: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
# ==============================================================================

# Database Configuration (PostgreSQL)
DB_HOST=${DB_HOST}
DB_PORT=${DB_PORT}
DB_NAME=${DB_NAME}
DB_USER=${DB_USER}
DB_PASSWORD=${DB_PASSWORD}
DB_POOL_MIN=2
DB_POOL_MAX=10

# Security
JWT_SECRET=${JWT_SECRET}
JWT_ALGORITHM=HS256
JWT_EXPIRES_HOURS=24

# Service Binding
SSO_HOST=${SSO_HOST}
SSO_PORT=${SSO_PORT}

# Initial Global Administrator Account
INITIAL_ADMIN_EMAIL=${INITIAL_ADMIN_EMAIL}
INITIAL_ADMIN_USERNAME=${INITIAL_ADMIN_USERNAME}
INITIAL_ADMIN_PASSWORD=${INITIAL_ADMIN_PASSWORD}
INITIAL_ADMIN_NAME=${INITIAL_ADMIN_NAME}

# Allowed Cross-Origin Origins (CORS)
CORS_ORIGINS=${CORS_ORIGINS}
EOF

chmod 600 "$ENV_FILE"
log_success "Environment configuration saved and secured (chmod 600)."

# ------------------------------------------------------------------------------
# 6. Database Verification & Schema Bootstrap
# ------------------------------------------------------------------------------
log_info "Connecting to PostgreSQL database ($DB_HOST:$DB_PORT/$DB_NAME) and applying schema..."
set +e
BOOTSTRAP_OUTPUT="$("$VENV_PYTHON" -c "
import sys
from app.config import settings
from app.database import init_pool, init_db, close_pool
from app.bootstrap import seed_data

try:
    init_pool()
    init_db()
    seed_data()
    close_pool()
    print('DATABASE_BOOTSTRAP_SUCCESS')
except Exception as exc:
    print(f'ERROR: {exc}', file=sys.stderr)
    sys.exit(1)
" 2>&1)"
BOOTSTRAP_EXIT=$?
set -e

if [ $BOOTSTRAP_EXIT -ne 0 ]; then
  log_warn "Database connection/bootstrap test encountered an issue:"
  echo "$BOOTSTRAP_OUTPUT"
  log_warn "If the database '$DB_NAME' does not exist yet on PostgreSQL, run:"
  echo -e "    ${BOLD}sudo -u postgres createdb -O $DB_USER $DB_NAME${NC}"
  echo "Then re-run this script."
else
  log_success "Database schema verified and initial administrator seeded successfully."
fi

# ------------------------------------------------------------------------------
# 7. Optional Systemd Service Setup
# ------------------------------------------------------------------------------
if [ "$INSTALL_SYSTEMD" = true ]; then
  log_info "Configuring systemd service..."
  SERVICE_FILE="/etc/systemd/system/sso.service"

  RUN_USER="$(whoami)"
  RUN_GROUP="$(id -gn)"
  if [ "$RUN_USER" = "root" ]; then
    RUN_USER="www-data"
    RUN_GROUP="www-data"
  fi

  cat > /tmp/sso.service <<EOF
[Unit]
Description=Central Single Sign-On (SSO) & Identity Service
After=network.target postgresql.service

[Service]
Type=simple
User=${RUN_USER}
Group=${RUN_GROUP}
WorkingDirectory=${HERE}
EnvironmentFile=${HERE}/.env
ExecStart=${VENV_DIR}/bin/python run.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

  if [ "$(id -u)" -eq 0 ]; then
    mv /tmp/sso.service "$SERVICE_FILE"
    systemctl daemon-reload
    systemctl enable sso.service
    log_success "Systemd service installed and enabled at $SERVICE_FILE"
    if [ "$START_SERVICE" = true ]; then
      systemctl restart sso.service
      log_success "SSO service started via systemctl."
    fi
  else
    log_warn "Cannot write to /etc/systemd/system/sso.service without root/sudo."
    echo "To install the service manually, run:"
    echo "    sudo cp /tmp/sso.service /etc/systemd/system/sso.service"
    echo "    sudo systemctl daemon-reload && sudo systemctl enable --now sso"
  fi
elif [ "$START_SERVICE" = true ]; then
  log_info "Starting SSO server on port $SSO_PORT..."
  exec "$VENV_PYTHON" run.py
fi

# ------------------------------------------------------------------------------
# 8. Setup Summary & Quick Commands
# ------------------------------------------------------------------------------
echo ""
echo -e "${GREEN}${BOLD}=================================================================${NC}"
echo -e "${GREEN}${BOLD}                 SSO SETUP COMPLETED SUCCESSFULLY!               ${NC}"
echo -e "${GREEN}${BOLD}=================================================================${NC}"
echo -e "  ${BOLD}Service Port:${NC}     $SSO_PORT"
echo -e "  ${BOLD}Database:${NC}         $DB_USER@$DB_HOST:$DB_PORT/$DB_NAME"
echo -e "  ${BOLD}Admin Account:${NC}    $INITIAL_ADMIN_EMAIL (Password: $INITIAL_ADMIN_PASSWORD)"
echo -e "  ${BOLD}Config File:${NC}      $ENV_FILE"
echo ""
echo -e "To start the SSO service manually:"
echo -e "  ${BOLD}cd '$HERE' && ./venv/bin/python run.py${NC}"
echo ""
echo -e "To test service health:"
echo -e "  ${BOLD}curl http://localhost:$SSO_PORT/api/sso/health${NC}"
echo -e "${GREEN}${BOLD}=================================================================${NC}"
