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
BACKEND_SERVICE="corporate-backend"
A2A_SERVICE="corporate-a2a-sales"

cd "$(dirname "$0")/../../backend"

echo "== deploying ${BACKEND_SERVICE} (first pass, to learn its URL) =="
gcloud run deploy "${BACKEND_SERVICE}" \
  --source . \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --no-allow-unauthenticated \
  --service-account="${SA_EMAIL}" \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_GENAI_USE_VERTEXAI=1,VERTEX_LOCATION=${REGION}"

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
gcloud run deploy "${A2A_SERVICE}" \
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

echo "== granting Pub/Sub's service agent permission to invoke the backend =="
PROJECT_NUMBER="$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')"
gcloud run services add-iam-policy-binding "${BACKEND_SERVICE}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --member="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-pubsub.iam.gserviceaccount.com" \
  --role="roles/run.invoker"

echo "== seeding Firestore agents + Pub/Sub push subscriptions =="
GOOGLE_CLOUD_PROJECT="${PROJECT_ID}" CORPORATE_BACKEND_URL="${BACKEND_URL}" python scripts/seed.py

echo "== deploying frontend to Firebase Hosting =="
(cd ../frontend && npm run build)
(cd .. && firebase deploy --only hosting --project "${PROJECT_ID}")

echo "== done =="
echo "Backend:   ${BACKEND_URL}"
echo "A2A (Sales & CRM): ${A2A_URL}/.well-known/agent-card.json"
