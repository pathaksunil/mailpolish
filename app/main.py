import logging
import logging.handlers
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
# Import directly from the specific route files
from app.routes.health import router as health_router
from app.routes.rewrite import router as rewrite_router
from app.routes.entitlement import router as entitlement_router
from app.routes.quota import router as quota_router
from app.routes.licensing import router as licensing_router

# 1. Load settings first
settings = get_settings()

# 2. Setup logging
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "mailpolish.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.handlers.RotatingFileHandler(
            LOG_FILE, maxBytes=2_000_000, backupCount=5, encoding="utf-8"
        ),
    ],
)
logger = logging.getLogger("mailpolish")
logger.info("Log file: %s", LOG_FILE)

# 3. Instantiate the FastAPI app FIRST before using it
app = FastAPI(title="MailPolish API", version="1.0.0")

# 4. Add middleware AFTER app is defined (using your settings)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"]
)

# 5. Register routes
app.include_router(health_router)
app.include_router(licensing_router)
app.include_router(rewrite_router)
app.include_router(entitlement_router)
app.include_router(quota_router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled API error on %s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Unexpected server error."})
