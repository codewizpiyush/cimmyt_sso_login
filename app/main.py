"""SSO Central Service Main Entrypoint."""
from contextlib import asynccontextmanager
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.bootstrap import seed_data
from app.config import settings
from app.database import close_pool, init_db, init_pool
from app.routers import auth, platforms, users

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger("sso")

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing SSO PostgreSQL database on port %d...", settings.sso_port)
    try:
        init_pool()
        init_db()
        seed_data()
        logger.info("SSO Central Service (PostgreSQL) is ready!")
    except Exception as exc:
        logger.error("SSO Startup Error: %s", exc)
        raise exc
    yield
    logger.info("SSO Service shutting down...")
    close_pool()


app = FastAPI(
    title=settings.app_name,
    description="Centralized Single Sign-On and Identity Provider for Multi-Platform Deployments.",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS Middleware with multi-domain support
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(platforms.router)

# Mount Static Files & Admin UI
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
def sso_admin_ui():
    """Serve the SSO Portal."""
    index_file = STATIC_DIR / "index.html"
    return FileResponse(index_file)


@app.get("/api/sso/health", tags=["Health"])
def health():
    return {
        "status": "healthy",
        "service": "SSO Central",
        "database": "PostgreSQL",
        "port": settings.sso_port,
    }
