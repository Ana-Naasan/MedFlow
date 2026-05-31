# Backend (FastAPI) image — built from the REPO ROOT context so the
# `backend.app.*` package imports resolve (PYTHONPATH=/app).
#   docker build -f backend/Dockerfile -t umraa-backend .
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PORT=8080

WORKDIR /app

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend /app/backend

EXPOSE 8080
# Cloud Run injects $PORT (defaults to 8080). Imports are `backend.app.*`.
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
