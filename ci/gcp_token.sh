#!/bin/sh
# Print a short-lived GCP access token for DEPLOY_SA using only curl + jq.
# For jobs without gcloud (docker build). Same WIF exchange as gcp_auth.sh:
#   GitLab OIDC JWT --STS--> federated token --IAM Credentials--> SA access token
set -eu
FED=$(curl -sSf https://sts.googleapis.com/v1/token \
  -H 'Content-Type: application/json' \
  -d "$(jq -n --arg aud "//iam.googleapis.com/${WIF_PROVIDER}" --arg tok "$GITLAB_OIDC_TOKEN" '{
        audience: $aud,
        grantType: "urn:ietf:params:oauth:grant-type:token-exchange",
        requestedTokenType: "urn:ietf:params:oauth:token-type:access_token",
        scope: "https://www.googleapis.com/auth/cloud-platform",
        subjectTokenType: "urn:ietf:params:oauth:token-type:jwt",
        subjectToken: $tok }')" | jq -r .access_token)
curl -sSf "https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/${DEPLOY_SA}:generateAccessToken" \
  -H "Authorization: Bearer ${FED}" -H 'Content-Type: application/json' \
  -d '{"scope":["https://www.googleapis.com/auth/cloud-platform"]}' | jq -r .accessToken
