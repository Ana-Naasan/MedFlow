"""CORS contract: the browser frontend must be allowed to call the API.

The local dev server runs on port 3001 (``next dev --port 3001``) and the deployed
frontend is a Cloud Run ``umraa-frontend-*.run.app`` origin. Both must pass CORS or the
browser blocks every API call.
"""

from fastapi.testclient import TestClient

from backend.app.main import app


def _preflight(origin: str):
    client = TestClient(app)
    return client.options(
        "/health",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
        },
    )


def test_local_dev_origin_3001_is_allowed() -> None:
    # The dev server runs on 3001 (package.json: `next dev --port 3001`).
    response = _preflight("http://localhost:3001")

    assert response.headers.get("access-control-allow-origin") == "http://localhost:3001"


def test_local_dev_origin_3000_is_allowed() -> None:
    # Keep the conventional 3000 working for custom setups.
    response = _preflight("http://localhost:3000")

    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_deployed_cloud_run_frontend_origin_is_allowed() -> None:
    # The deployed frontend is matched by regex so it works across revisions.
    origin = "https://umraa-frontend-abc123-uc.a.run.app"
    response = _preflight(origin)

    assert response.headers.get("access-control-allow-origin") == origin
