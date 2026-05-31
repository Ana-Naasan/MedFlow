from __future__ import annotations

import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import Response

from backend.app.api.router import api_router
from backend.app.cache.models import Base
from backend.app.database import get_db_url, make_engine, make_session_factory
from backend.app.observability import configure_logging, get_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = make_engine(get_db_url())
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    app.state.session_factory = make_session_factory(engine)
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    configure_logging()
    logger = get_logger("api")
    app = FastAPI(
        title="Umraa API",
        version="0.1.0",
        description="Stage B scaffold for the polypharmacy decision packet.",
        separate_input_output_schemas=False,
        lifespan=lifespan,
    )
    # Local dev origin plus any extra origins from CORS_ALLOW_ORIGINS (comma-separated).
    # The deployed Cloud Run frontend is matched by regex so it works across revisions
    # and project numbers without hardcoding a single URL.
    allowed_origins = ["http://localhost:3000"]
    extra = os.getenv("CORS_ALLOW_ORIGINS", "")
    allowed_origins += [o.strip() for o in extra.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_origin_regex=r"https://umraa-frontend-.*\.run\.app",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def log_requests(request: Request, call_next) -> Response:
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            # Log the 5xx/unhandled case too — the requests most worth logging —
            # then re-raise so the error is NOT swallowed.
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.exception(
                "%s %s -> error",
                request.method,
                request.url.path,
                extra={
                    "context": {
                        "method": request.method,
                        "path": request.url.path,
                        "status": 500,
                        "duration_ms": duration_ms,
                    }
                },
            )
            raise
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "%s %s -> %s",
            request.method,
            request.url.path,
            response.status_code,
            extra={
                "context": {
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": duration_ms,
                }
            },
        )
        return response

    app.include_router(api_router)
    return app


app = create_app()
