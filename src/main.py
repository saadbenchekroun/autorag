"""FastAPI application factory with lifespan management."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.routers import api_router
from src.core.config import settings
from src.core.exceptions import AutoRAGError
from src.core.logging import configure_logging, get_logger
from src.services.embedding_registry import warm_default_embedding

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: warm models on startup, clean up on shutdown."""
    logger.info("startup_begin", version=settings.VERSION)
    # Pre-load the default embedding model so the first request has no cold-start.
    warm_default_embedding()
    logger.info("startup_complete")
    yield
    logger.info("shutdown")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
# In production set ALLOWED_ORIGINS to a comma-separated list of origins,
# e.g. "https://app.example.com,https://staging.example.com".
# When unset (local dev) all origins are allowed.
_allowed_origins_raw = settings.ALLOWED_ORIGINS
allowed_origins = (
    [o.strip() for o in _allowed_origins_raw.split(",") if o.strip()]
    if _allowed_origins_raw
    else ["*"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Global exception handler for domain errors not caught in routers
# ---------------------------------------------------------------------------


@app.exception_handler(AutoRAGError)
async def autorag_error_handler(request: Request, exc: AutoRAGError) -> JSONResponse:
    logger.error("unhandled_domain_exception", path=str(request.url), error=str(exc))
    return JSONResponse(status_code=500, content={"detail": str(exc)})


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["system"])
def root():
    return {"message": f"Welcome to {settings.PROJECT_NAME} v{settings.VERSION}"}
