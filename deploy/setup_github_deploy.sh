#!/usr/bin/env bash
# One-time setup so GitHub Actions can deploy to Cloud Run without any password or key file.
# Run it in Google Cloud Shell (the ">_" button at the top right of console.cloud.google.com).
#
#   bash deploy/setup_github_deploy.sh YOUR_PROJECT_ID
#
# It is safe to run twice: things that already exist are skipped.
# At the end it prints the values to paste into GitHub (Settings > Secrets and variables > Actions > Variables).

set -euo pipefail

PROJECT_ID="${1:?Usage: bash deploy/setup_github_deploy.sh YOUR_PROJECT_ID [github-user/repo]}"
REPO="${2:-yuv294/Life-saver}"   # must match the repo name exactly, including capital letters
POOL="github-pool"
PROVIDER="github-provider"
SA_NAME="github-deployer"

gcloud config set project "$PROJECT_ID" >/dev/null
PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "1/5 Turning on the Google services the deploy needs..."
gcloud services enable \
  run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com \
  iamcredentials.googleapis.com iam.googleapis.com

echo "2/5 Creating a robot account that GitHub will act as..."
gcloud iam service-accounts describe "$SA_EMAIL" >/dev/null 2>&1 || \
  gcloud iam service-accounts create "$SA_NAME" --display-name="GitHub deployer"

echo "3/5 Giving the robot account permission to build and deploy..."
for ROLE in roles/run.admin roles/cloudbuild.builds.editor roles/artifactregistry.writer \
            roles/storage.admin roles/iam.serviceAccountUser roles/serviceusage.serviceUsageConsumer; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${SA_EMAIL}" --role="$ROLE" --condition=None >/dev/null
done

echo "4/5 Letting ONLY your GitHub repo use that robot account..."
gcloud iam workload-identity-pools describe "$POOL" --location=global >/dev/null 2>&1 || \
  gcloud iam workload-identity-pools create "$POOL" --location=global --display-name="GitHub"

gcloud iam workload-identity-pools providers describe "$PROVIDER" \
  --location=global --workload-identity-pool="$POOL" >/dev/null 2>&1 || \
  gcloud iam workload-identity-pools providers create-oidc "$PROVIDER" \
    --location=global --workload-identity-pool="$POOL" \
    --issuer-uri="https://token.actions.githubusercontent.com" \
    --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
    --attribute-condition="assertion.repository=='${REPO}'"

gcloud iam service-accounts add-iam-policy-binding "$SA_EMAIL" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL}/attribute.repository/${REPO}" >/dev/null

echo "5/5 Looking up your existing Cloud Run service..."
gcloud run services list --format="table(metadata.name,metadata.labels.'cloud.googleapis.com/location':label=REGION)" || true

PROVIDER_PATH="$(gcloud iam workload-identity-pools providers describe "$PROVIDER" \
  --location=global --workload-identity-pool="$POOL" --format='value(name)')"

cat <<EOF

=====================================================================
Done. In GitHub open your repo > Settings > Secrets and variables >
Actions > the "Variables" tab > New repository variable, and add:

  GCP_PROJECT_ID                  = ${PROJECT_ID}
  GCP_REGION                      = (the REGION shown in the table above, e.g. asia-south1)
  CLOUD_RUN_SERVICE               = (the NAME shown in the table above)
  GCP_SERVICE_ACCOUNT             = ${SA_EMAIL}
  GCP_WORKLOAD_IDENTITY_PROVIDER  = ${PROVIDER_PATH}
=====================================================================
EOF
