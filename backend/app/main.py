from fastapi import FastAPI

from backend.app.api.router import api_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Umraa API",
        version="0.1.0",
        description="Stage B scaffold for the polypharmacy decision packet.",
    )
    app.include_router(api_router)
    return app


app = create_app()
