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
  --project="${PROJECT_ID}"

echo "== Firestore (native mode) =="
gcloud firestore databases create --location="${REGION}" --project="${PROJECT_ID}" || \
  echo "Firestore database already exists, skipping"

echo "== Pub/Sub topic =="
gcloud pubsub topics create agent-bus --project="${PROJECT_ID}" || \
  echo "topic agent-bus already exists, skipping"

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

echo "== done. Next: ./deploy.sh =="
