import time
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.logging import configure_logging, get_logger, request_id_var, user_id_var

settings = get_settings()
configure_logging(settings.LOG_LEVEL)
logger = get_logger("app")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        description="Customer support platform with a human-in-the-loop AI assistant (Ollama + LangGraph + pgvector).",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        request_id_token = request_id_var.set(request_id[:64])
        user_token = user_id_var.set(None)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("Unhandled error", extra={"path": request.url.path, "method": request.method})
            response = JSONResponse(status_code=500, content={"detail": "Internal server error", "code": "internal_error"})
        latency_ms = round((time.perf_counter() - started) * 1000, 1)
        # Auth dependencies may run in a worker thread, so the user id travels via request.state.
        user_id_var.set(getattr(request.state, "user_id", None))
        response.headers["X-Request-ID"] = request_id_var.get() or request_id
        logger.info(
            "request",
            extra={
                "operation": "http.request",
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "latency_ms": latency_ms,
                "success": response.status_code < 400,
            },
        )
        request_id_var.reset(request_id_token)
        user_id_var.reset(user_token)
        return response

    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
        return JSONResponse(
            status_code=exc.status_code, content={"detail": exc.message, "code": exc.code}, headers=headers
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            {"field": ".".join(str(part) for part in err["loc"] if part != "body"), "message": err["msg"]}
            for err in exc.errors()
        ]
        summary = "; ".join(f"{e['field']}: {e['message']}" if e["field"] else e["message"] for e in errors)
        return JSONResponse(
            status_code=422, content={"detail": summary or "Invalid request", "code": "validation_error", "errors": errors}
        )

    @app.exception_handler(SQLAlchemyError)
    async def database_error_handler(_: Request, exc: SQLAlchemyError) -> JSONResponse:
        logger.error("Database error", extra={"operation": "db", "success": False, "error": type(exc).__name__})
        return JSONResponse(
            status_code=503,
            content={"detail": "The database is unavailable or returned an error. Please try again.", "code": "database_error"},
        )

    app.include_router(api_router)

    @app.get("/", include_in_schema=False)
    def root() -> dict[str, str]:
        return {"name": settings.APP_NAME, "docs": "/docs", "health": "/api/health"}

    return app


app = create_app()
