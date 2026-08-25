#!/usr/bin/env bash
# One-time GCP project setup: enable APIs, create Firestore + the agent-bus
# Pub/Sub topic, create the backend's service account and grant it the
# roles every part of this project needs. Run once per project, before
# deploy.sh. Requires billing to already be enabled on the project (see
# docs/adr/0001-cloud-native-hosted-architecture.md).
#
# Usage: PROJECT_ID=project-f0b6b4ce-541f-43ff-9f7 REGION=us-central1 ./setup.sh

set -euo pipefail

PROJECT_ID="${PROJECT_ID:?set PROJECT_ID}"
REGION="${REGION:-us-central1}"
SA_NAME="corporate-backend-sa"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "== enabling APIs =="
gcloud services enable \
  firestore.googleapis.com \
  pubsub.googleapis.com \
  run.googleapis.com \
  aiplatform.googleapis.com \
  cloudscheduler.googleapis.com \
  secretmanager.googleapis.com \
  storage.googleapis.com \
  --project="${PROJECT_ID}"

echo "== Firestore (native mode) =="
gcloud firestore databases create --location="${REGION}" --project="${PROJECT_ID}" || \
  echo "Firestore database already exists, skipping"

echo "== Pub/Sub topic =="
gcloud pubsub topics create agent-bus --project="${PROJECT_ID}" || \
  echo "topic agent-bus already exists, skipping"

echo "== vision attachments bucket (ADR-0013) =="
ATTACHMENTS_BUCKET="${PROJECT_ID}-attachments"
gcloud storage buckets create "gs://${ATTACHMENTS_BUCKET}" --location="${REGION}" --project="${PROJECT_ID}" || \
  echo "bucket gs://${ATTACHMENTS_BUCKET} already exists, skipping"

echo "== service account =="
gcloud iam service-accounts create "${SA_NAME}" \
  --display-name="Corporate backend" \
  --project="${PROJECT_ID}" || echo "service account already exists, skipping"

for role in roles/datastore.user roles/pubsub.publisher roles/pubsub.subscriber roles/aiplatform.user roles/secretmanager.admin; do
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="${role}" \
    --condition=None
done

echo "== granting the backend write access to the attachments bucket =="
gcloud storage buckets add-iam-policy-binding "gs://${ATTACHMENTS_BUCKET}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/storage.objectAdmin"

echo "== granting Vertex AI's service agent read access to the attachments bucket =="
# types.Part.from_uri() (app/adk_agents/runtime.py) hands Gemini a gs:// URI
# directly — Vertex AI reads that object as its own service identity, not as
# corporate-backend-sa, so it needs its own grant here (ADR-0013).
PROJECT_NUMBER="$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')"
gcloud storage buckets add-iam-policy-binding "gs://${ATTACHMENTS_BUCKET}" \
  --member="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-aiplatform.iam.gserviceaccount.com" \
  --role="roles/storage.objectViewer"

echo "== granting Cloud Build's default identity storage read access =="
# `gcloud run deploy --source .` uploads your source to a per-project GCS
# bucket for Cloud Build to read. On projects created after Google tightened
# default service-account IAM (removed the old broad Editor role), the
# default Compute service account Cloud Build runs as lacks
# storage.objects.get on that bucket and the deploy fails with a 403 on the
# uploaded source zip. Grant it once here so deploy.sh doesn't hit it.
# PROJECT_NUMBER is already set above, for the Vertex AI attachments-bucket grant.
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/storage.objectViewer" \
  --condition=None

echo "== granting Cloud Build's default identity Artifact Registry push access =="
# Same tightened-IAM story as above: after the build succeeds, Cloud Build
# pushes the image to the cloud-run-source-deploy Artifact Registry repo as
# this same default Compute service account. Without this role the deploy
# fails later, at push time, with "Build failed; check build logs" and no
# further detail from `gcloud run deploy`.
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/artifactregistry.writer" \
  --condition=None

echo "== done. Next: ./deploy.sh =="
