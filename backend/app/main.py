"""FastAPI application entrypoint for YogyataMitra."""

import logging
from typing import Any, Dict

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.router import api_v1_router
from app.core.config import settings
from app.core.database import get_db
from app.schemas.api import ErrorDetail, ErrorResponse

logger = logging.getLogger("yogyatamitra.api")

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    description="GovTech Statutory Welfare Entitlement and Eligibility Platform API",
    version="1.0.0",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
)

# Configure CORS for local development frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Mount Version 1 API
app.include_router(api_v1_router, prefix=settings.API_V1_STR)


# ==============================================================================
# Standardized Error Handlers
# ==============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Standardize HTTP exceptions into ErrorResponse schema."""
    code_map = {
        status.HTTP_400_BAD_REQUEST: "BAD_REQUEST",
        status.HTTP_404_NOT_FOUND: "NOT_FOUND",
        status.HTTP_409_CONFLICT: "CONFLICT",
        status.HTTP_422_UNPROCESSABLE_CONTENT: "UNPROCESSABLE_ENTITY",
        status.HTTP_503_SERVICE_UNAVAILABLE: "SERVICE_UNAVAILABLE",
    }
    error_code = code_map.get(exc.status_code, "ERROR")

    # If detail is already a dict, extract details
    if isinstance(exc.detail, dict):
        message = exc.detail.get("message", "An error occurred.")
        details = exc.detail.get("details")
        code = exc.detail.get("code", error_code)
    else:
        message = str(exc.detail)
        details = None
        code = error_code

    payload = ErrorResponse(
        error=ErrorDetail(code=code, message=message, details=details)
    ).model_dump()
    return JSONResponse(status_code=exc.status_code, content=payload)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Standardize Pydantic validation errors into ErrorResponse schema."""
    errors = exc.errors()
    # Sanitize errors for client exposure
    sanitized_errors = []
    for err in errors:
        loc = [str(x) for x in err.get("loc", [])]
        sanitized_errors.append({
            "field": ".".join(loc),
            "message": err.get("msg", "Invalid value"),
            "type": err.get("type", "value_error"),
        })

    payload = ErrorResponse(
        error=ErrorDetail(
            code="VALIDATION_ERROR",
            message="Request body or query parameter validation failed.",
            details={"validation_errors": sanitized_errors},
        )
    ).model_dump()
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, content=payload)


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler ensuring internal stack traces and DB credentials never leak."""
    logger.error("Unhandled exception during request processing: %s", exc, exc_info=True)
    payload = ErrorResponse(
        error=ErrorDetail(
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected server error occurred while processing the request.",
            details=None,
        )
    ).model_dump()
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=payload)


# ==============================================================================
# Health / Readiness Endpoints
# ==============================================================================

@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    """Basic health check endpoint."""
    return {
        "status": "ok",
        "service": settings.PROJECT_NAME,
    }


@app.get("/health/db", tags=["Health"])
async def db_health_check(
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Database connectivity health check."""
    try:
        result = await db.execute(text("SELECT 1"))
        row = result.fetchone()
        if row and row[0] == 1:
            return {
                "status": "ok",
                "database": "connected",
                "service": settings.PROJECT_NAME,
            }
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unexpected database response",
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database unreachable: {str(exc)}",
        )
