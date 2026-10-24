# Runbook: pipelines, gates, Google Cloud (owner: Om)

What exists, what still needs a human with accounts, and how to run Om's Day-1 spikes.
Post each spike result in team chat as yes/no plus a link.

## Live setup (Oct 25, 2026)

| Thing | Value |
| --- | --- |
| GCP project | `project-52f411a4-f688-4521-bbc` (number 246401536067), on Om's free-trial billing account |
| Region | `europe-north1` |
| Cloud Run | `https://shelf-i6y2wbu2yq-lz.a.run.app` |
| Budget alert | `afterlife-guard`, ₹2,000, gross usage (before credits), alerts at 25/50/90/100% |
| Terraform state | Om's Cloud Shell, `~/AFTERLIFE/infra/terraform.tfstate`, via a local `backend_override.tf`. Move it to GitLab-managed state before running `terraform-plan` on an MR. |
| Firestore | Seeded with `scripts/seed_history.py`; every call is marked simulated |
| GitLab | Both flows enabled. CI variables set: `AFTERLIFE_TOKEN`, `AFTERLIFE_AGENT_USERNAME`, all GCP ones |

Terraform isn't preinstalled in Cloud Shell any more; install it from `apt.releases.hashicorp.com`.
Trial accounts have a small project quota, so the trial's own "My First Project" is used.

## What's in the repo

| Path | What |
| --- | --- |
| `.gitlab-ci.yml`, `ci/pipelines/*.yml` | census, Sunset MR, main and terraform-plan pipelines |
| `ci/coma.py`, `ci/resurrect.py` | flag off / back on through the GitLab Feature Flags API |
| `ci/review_check.py` | waits for the Reviewer's `AFTERLIFE-REVIEW: PASS` |
| `ci/gate_merge.py` | merges with the project access token, pinned to the tested SHA |
| `ci/canary_watch.py`, `ci/rollback.py` | Cloud Run canary judgement and rollback notice |
| `ci/measure.py`, `ci/runner_minutes.py`, `ci/obituary.py`, `ci/release_notes.py` | measured savings, SCI, obituary, release |
| `ci/diff_checks.py` | vulture and pip-audit, target branch vs MR |
| `ci/gitlab.py` | GitLab API client shared by the gates |
| `ci/gcp_auth.sh`, `ci/gcp_token.sh` | keyless GCP auth: GitLab OIDC → Workload Identity Federation |
| `infra/*.tf` | APIs, Artifact Registry, Firestore, Cloud Run, WIF, deploy and plan service accounts |
| `afterlife/sci_coefficients.yaml` | SCI inputs, each with a source; embodied is still null |

Aditya's `ci/census.py`, `ci/verdict_check.py`, `ci/vigil.py` and `ci/policy.py` are used as they are.

## How the Sunset MR pipeline runs

```
test, vulture, vulture-recheck, dependency-audit, pip-audit-diff, SAST, secret detection, build-image
  -> verdict-check (policy from target branch, census from afterlife/census) + review-check
  -> coma (flag off: 410 + knock log)
  -> vigil (vigil_minutes, exit 1 on a knock)
  -> gate-merge (silent vigil, no protected path, CODEOWNERS if requires_approval)
     or resurrect (on failure: flag on, MR closed and labelled afterlife::resurrected)
```

The feature is the branch suffix: `afterlife/books_v1` → flag `books_v1`. The merge commit
message is `AFTERLIFE: retire <feature> via !<iid>`. The main pipeline's release, measure and
obituary jobs key off it, so set the merge method to **merge commit**.

## Spike 1: GCP project, budget, WIF, first deploy from CI

```sh
gcloud auth login && gcloud auth application-default login
gcloud projects create afterlife-hackathon --name="AFTERLIFE"
gcloud billing projects link afterlife-hackathon --billing-account=XXXXXX-XXXXXX-XXXXXX
gcloud billing budgets create --billing-account=XXXXXX-XXXXXX-XXXXXX \
  --display-name="afterlife" --budget-amount=20USD \
  --filter-projects=projects/afterlife-hackathon \
  --threshold-rule=percent=0.5 --threshold-rule=percent=0.9 --threshold-rule=percent=1.0

cd infra && cp terraform.tfvars.example terraform.tfvars   # fill it in
# GitLab-managed state; GITLAB_PAT is a personal access token with api scope
TF_ADDRESS=https://gitlab.com/api/v4/projects/<PROJECT_ID>/terraform/state/afterlife
terraform init \
  -backend-config="address=$TF_ADDRESS" \
  -backend-config="lock_address=$TF_ADDRESS/lock" -backend-config="unlock_address=$TF_ADDRESS/lock" \
  -backend-config="username=<gitlab-user>" -backend-config="password=$GITLAB_PAT" \
  -backend-config="lock_method=POST" -backend-config="unlock_method=DELETE"
terraform apply
terraform output   # copy into the CI/CD variables below
```

**Pass:** a push to `main` runs `build-push → deploy-canary → canary-watch → promote`, and
`SHELF_URL/health` answers 200 (not `/healthz`: Cloud Run reserves paths ending in `z`).

## Spike 2: CI merges an MR with a project access token, pinned to SHA

1. Settings → Access tokens: role **Maintainer**, scope `api`. Save it as `AFTERLIFE_TOKEN` (masked).
2. Settings → Merge requests: merge method **Merge commit**.
3. Open a throwaway MR from `afterlife/spike` with label `afterlife::sunset` and run `gate-merge`
   alone, with a hand-written `vigil.json` (`{"feature": "spike", "decision": "pass", "knocks": []}`).
4. **Pass:** the MR is merged at the pipeline's SHA. Try both `GATE_MERGE_MODE=auto` (the default)
   and `immediate`. With "Pipelines must succeed" on, only `auto` can work, because the pipeline is still running.

## Spike 3: CI toggles a GitLab feature flag

```sh
curl -sH "PRIVATE-TOKEN: $AFTERLIFE_TOKEN" -H 'Content-Type: application/json' -X POST \
  "https://gitlab.com/api/v4/projects/<PROJECT_ID>/feature_flags" \
  -d '{"name":"books_v1","version":"new_version_flag","active":true,
       "strategies":[{"name":"default","scopes":[{"environment_scope":"production"}]}]}'
AFTERLIFE_TOKEN=... CI_PROJECT_ID=<PROJECT_ID> python -m ci.coma --feature books_v1
AFTERLIFE_TOKEN=... CI_PROJECT_ID=<PROJECT_ID> python -m ci.coma --feature books_v1 --on
```

**Pass:** the flag flips in Deploy → Feature flags, and Shelf (with `UNLEASH_URL` set) returns
410 within the Unleash poll interval. Create one flag per feature in `app/features/`.

## CI/CD variables

| Variable | Value | Flags |
| --- | --- | --- |
| `AFTERLIFE_TOKEN` | project access token (api, Maintainer) | masked, protected |
| `AFTERLIFE_AGENT_USERNAME` | the Duo flow service account's username | |
| `GCP_PROJECT_ID` | e.g. `afterlife-hackathon` | |
| `GCP_REGION` | `europe-north1` | |
| `WIF_PROVIDER` | `terraform output WIF_PROVIDER` | |
| `DEPLOY_SA` | `terraform output DEPLOY_SA` | |
| `TF_PLAN_SA` | `terraform output TF_PLAN_SA` | |
| `AR_REPO` | `terraform output AR_REPO` | |
| `SHELF_URL` | `terraform output SHELF_URL` | |
| `VIGIL_MINUTES` | optional override of policy `vigil_minutes` | |
| `MEDIUM_VIA_API` | `1` only once the Flows API spike passes | |

Protect `main` and the wildcard `afterlife/*`, so protected variables reach Sunset MR pipelines.
Census: CI/CD → Schedules, daily, with variable `AFTERLIFE_PIPELINE=census`.

## Region: europe-north1

Google's 2025 table gives Finland (europe-north1) **98% carbon-free energy and 30 gCO2eq/kWh**,
against 20% / 598 g for Mumbai (asia-south1) and 39% / 473 g for Delhi (asia-south2).
Source: https://cloud.google.com/sustainability/region-carbon, checked 2026-10-24.
Cloud Run and Firestore are both available there. Latency from India doesn't matter for this demo.

## Known gaps

- **"No new SAST findings" is shown, not enforced.** Findings appear in the MR security widget.
  To block on them, add an approval policy or a job that parses the report.
- **The Flows API call in `resurrect.py` is unverified** (endpoint guessed). It stays off until `MEDIUM_VIA_API=1`.
- **WIF `ref_protected` hardening is left out** until we see what MR pipelines send (see `infra/wif.tf`).
- **Embodied carbon coefficient is null.** SCI says "not computed" until it has a cited value.
- **Image size before/after** uses the registry's compressed sizes for both commits.
- **Nothing here has run on GitLab or GCP yet.** Only unit tests and YAML reference checks ran locally.
