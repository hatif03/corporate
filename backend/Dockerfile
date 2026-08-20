# Cloud Run image for the main backend (app.main:app) AND the standalone
# A2A server (app.a2a_server:app) — same image, different CMD override at
# deploy time (see /infra/deploy/deploy.sh), since both are the same
# Python package with no divergent dependencies.

FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1
EXPOSE 8080

# Cloud Run sets $PORT; default to 8080 for local `docker run`.
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
