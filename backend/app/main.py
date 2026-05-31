from __future__ import annotations

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
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def log_requests(request: Request, call_next) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
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
