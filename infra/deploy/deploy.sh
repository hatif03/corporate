#!/usr/bin/env bash
# Builds and deploys both Cloud Run services (main backend + the standalone
# Sales & CRM A2A server, see ADR-0004), wires the Pub/Sub push subscription
# IAM binding, seeds Firestore, and deploys the frontend to Firebase
# Hosting. Run setup.sh once first. Idempotent — safe to re-run.
#
# Usage: PROJECT_ID=project-f0b6b4ce-541f-43ff-9f7 REGION=us-central1 ./deploy.sh

set -euo pipefail

PROJECT_ID="${PROJECT_ID:?set PROJECT_ID}"
REGION="${REGION:-us-central1}"
SA_EMAIL="corporate-backend-sa@${PROJECT_ID}.iam.gserviceaccount.com"

# OAuth "Connect with X" (ADR-0018) — optional, all default empty so a
# deploy with none of these set just leaves those Connect buttons
# non-functional rather than failing. Sourced here (not left to a one-off
# `gcloud run services update`) because the deploy below uses
# --set-env-vars, which REPLACES the whole env-var set on every re-run —
# anything set out-of-band would get silently wiped on the next deploy.
SLACK_OAUTH_CLIENT_ID="${SLACK_OAUTH_CLIENT_ID:-}"
GITHUB_OAUTH_CLIENT_ID="${GITHUB_OAUTH_CLIENT_ID:-}"
NOTION_OAUTH_CLIENT_ID="${NOTION_OAUTH_CLIENT_ID:-}"
OAUTH_STATE_SECRET="${OAUTH_STATE_SECRET:-}"
BACKEND_SERVICE="corporate-backend"
A2A_SERVICE="corporate-a2a-sales"

cd "$(dirname "$0")/../../backend"

# scripts/seed.py needs this project's deps (google-cloud-pubsub etc.) —
# plain `python` on PATH is whatever's globally installed on the dev
# machine, not necessarily this venv, and fails with a bare ImportError deep
# into the script (after both Cloud Run services already deployed) instead
# of a clear "wrong interpreter" error. Prefer the venv explicitly.
if [ -f ".venv/Scripts/python.exe" ]; then
  PYTHON=".venv/Scripts/python.exe"
elif [ -f ".venv/bin/python" ]; then
  PYTHON=".venv/bin/python"
else
  PYTHON="python3"
fi

echo "== deploying ${BACKEND_SERVICE} (first pass, to learn its URL) =="
# --allow-unauthenticated: /api/org/* must be publicly reachable so the
# browser frontend's Firebase-token auth (require_org_member) ever runs at
# all — Cloud Run's own IAM gate is all-or-nothing per service, so it can't
# also selectively protect /internal/*. /internal/* protects itself instead,
# via require_internal_oidc (see app/services/auth.py and
# app/api/internal.py's module docstring).
gcloud run deploy "${BACKEND_SERVICE}" \
  --source . \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --allow-unauthenticated \
  --service-account="${SA_EMAIL}" \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_GENAI_USE_VERTEXAI=1,VERTEX_LOCATION=${REGION},CORPORATE_ATTACHMENTS_BUCKET=${PROJECT_ID}-attachments,SLACK_OAUTH_CLIENT_ID=${SLACK_OAUTH_CLIENT_ID},GITHUB_OAUTH_CLIENT_ID=${GITHUB_OAUTH_CLIENT_ID},NOTION_OAUTH_CLIENT_ID=${NOTION_OAUTH_CLIENT_ID},OAUTH_STATE_SECRET=${OAUTH_STATE_SECRET}"

BACKEND_URL="$(gcloud run services describe "${BACKEND_SERVICE}" --region="${REGION}" --project="${PROJECT_ID}" --format='value(status.url)')"
echo "backend URL: ${BACKEND_URL}"

echo "== redeploying ${BACKEND_SERVICE} with its own URL set (needed for Pub/Sub push subscription creation in seed.py) =="
gcloud run services update "${BACKEND_SERVICE}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --update-env-vars="CORPORATE_BACKEND_URL=${BACKEND_URL}"

echo "== deploying ${A2A_SERVICE} (same image, different entrypoint) =="
# --command/--args override the container's CMD in exec form (no shell), so
# $PORT would otherwise reach uvicorn as the literal string "$PORT" instead
# of being expanded — route through /bin/sh -c explicitly so it actually
# expands, same as the Dockerfile's own shell-form CMD does for the main service.
# MSYS2_ARG_CONV_EXCL="--command=": on Git Bash for Windows, "--command=/bin/sh"
# is one argv token whose /bin/sh half looks like a POSIX absolute path, so it
# gets silently rewritten to a Windows path (e.g.
# "--command=C:/Program Files/Git/usr/bin/sh") before gcloud ever sees it,
# which Cloud Run then fails to exec inside the Linux container. Match on the
# "--command=" prefix (matching must cover the whole argv token, not just the
# embedded path) — the blanket MSYS_NO_PATHCONV=1 / "*" also breaks gcloud's
# own internal path resolution (its Windows wrapper is itself a bash script).
# No-op on real bash/Linux.
MSYS2_ARG_CONV_EXCL="--command=" gcloud run deploy "${A2A_SERVICE}" \
  --source . \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --allow-unauthenticated \
  --service-account="${SA_EMAIL}" \
  --command="/bin/sh" \
  --args="-c,exec uvicorn app.a2a_server:app --host 0.0.0.0 --port \$PORT" \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_GENAI_USE_VERTEXAI=1,VERTEX_LOCATION=${REGION}"

A2A_URL="$(gcloud run services describe "${A2A_SERVICE}" --region="${REGION}" --project="${PROJECT_ID}" --format='value(status.url)')"
echo "A2A server URL: ${A2A_URL}"
gcloud run services update "${BACKEND_SERVICE}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --update-env-vars="CORPORATE_A2A_SALES_URL=${A2A_URL}"

echo "== redeploying ${A2A_SERVICE} with its own URL set (a2a_server.py uses it to build the agent-card host/protocol, otherwise it advertises localhost) =="
gcloud run services update "${A2A_SERVICE}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --update-env-vars="CORPORATE_A2A_SALES_URL=${A2A_URL}"

echo "== granting Pub/Sub's service agent permission to mint OIDC tokens as the backend's own service account =="
# The backend is --allow-unauthenticated (Cloud Run's own IAM gate is not
# in play), so Pub/Sub doesn't need roles/run.invoker here — it needs to be
# able to mint an OIDC token AS corporate-backend-sa to attach to each push
# request, which require_internal_oidc then verifies on arrival.
PROJECT_NUMBER="$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')"
gcloud iam service-accounts add-iam-policy-binding "${SA_EMAIL}" \
  --project="${PROJECT_ID}" \
  --member="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-pubsub.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountTokenCreator"

echo "== seeding Firestore agents + Pub/Sub push subscriptions =="
GOOGLE_CLOUD_PROJECT="${PROJECT_ID}" CORPORATE_BACKEND_URL="${BACKEND_URL}" "${PYTHON}" scripts/seed.py

echo "== deploying Firestore security rules =="
# Client reads go straight to Firestore (see frontend/src/lib/platformClient.ts's
# onSnapshot calls) — without these, the default deny-all rules on a fresh
# project block every client read silently (onSnapshot has no error
# callback here), which looks exactly like "agents never got seeded" even
# when they did.
(cd .. && firebase deploy --only firestore:rules --project "${PROJECT_ID}")

echo "== deploying frontend to Firebase Hosting =="
(cd ../frontend && npm run build)
(cd .. && firebase deploy --only hosting --project "${PROJECT_ID}")

echo "== done =="
echo "Backend:   ${BACKEND_URL}"
echo "A2A (Sales & CRM): ${A2A_URL}/.well-known/agent-card.json"
