from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.router import api_router
from backend.app.cache.models import Base
from backend.app.database import get_db_url, make_engine, make_session_factory


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = make_engine(get_db_url())
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    app.state.session_factory = make_session_factory(engine)
    yield
    await engine.dispose()


def create_app() -> FastAPI:
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
    app.include_router(api_router)
    return app


app = create_app()
