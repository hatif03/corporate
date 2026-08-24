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
# --proxy-headers --forwarded-allow-ips='*': Cloud Run terminates TLS at its
# own edge and forwards internally over plain HTTP, so without this,
# request.url.scheme inside the app reads "http" even for a real HTTPS
# request — breaks anything that checks the request's own URL/scheme (e.g.
# require_internal_oidc's audience check in app/services/auth.py, which
# must match the "https://..." audience Pub/Sub's OIDC token actually
# carries). Safe to trust every forwarder here: Cloud Run's edge is the only
# thing that can reach this container directly.
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --proxy-headers --forwarded-allow-ips='*'
