# Keyless GCP auth: GitLab OIDC id_token -> Workload Identity Federation ->
# impersonate the deploy service account. No service-account keys anywhere.
# SOURCE this file (". ci/gcp_auth.sh"), so no `set -eu` here: it would leak
# into the job's shell. Needs: GITLAB_OIDC_TOKEN (id_tokens), WIF_PROVIDER, DEPLOY_SA.
for v in GITLAB_OIDC_TOKEN WIF_PROVIDER DEPLOY_SA GCP_PROJECT_ID; do
  eval "[ -n \"\${$v:-}\" ]" || { echo "gcp_auth: $v is not set" >&2; exit 1; }
done
printf '%s' "$GITLAB_OIDC_TOKEN" > "$CI_PROJECT_DIR/.gitlab_oidc_jwt"
cat > "$CI_PROJECT_DIR/.gcp_cred.json" <<EOF
{
  "type": "external_account",
  "audience": "//iam.googleapis.com/${WIF_PROVIDER}",
  "subject_token_type": "urn:ietf:params:oauth:token-type:jwt",
  "token_url": "https://sts.googleapis.com/v1/token",
  "service_account_impersonation_url": "https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/${DEPLOY_SA}:generateAccessToken",
  "credential_source": { "file": "${CI_PROJECT_DIR}/.gitlab_oidc_jwt" }
}
EOF
export GOOGLE_APPLICATION_CREDENTIALS="$CI_PROJECT_DIR/.gcp_cred.json"
if command -v gcloud >/dev/null 2>&1; then
  gcloud auth login --quiet --cred-file="$GOOGLE_APPLICATION_CREDENTIALS" || exit 1
  gcloud config set project "$GCP_PROJECT_ID" --quiet
fi
