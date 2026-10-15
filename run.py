"""SSO Service Runner."""
import os
from pathlib import Path
import sys

# Ensure the SSO directory is in python search path and set as app_dir
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import uvicorn
from app.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.sso_host,
        port=settings.sso_port,
        reload=True,
        app_dir=str(BASE_DIR),
    )
