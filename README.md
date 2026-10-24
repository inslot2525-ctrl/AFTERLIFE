# AFTERLIFE

**Every team automates code on its way into production. AFTERLIFE automates the way out.**

Codebases only grow. Features stop being used, but their code, tests and dependencies stay, and every pipeline keeps
building, scanning and shipping them. AFTERLIFE finds features nobody uses from production traffic, proves they are
dead, switches them off, listens for anyone who still needs them, and only then deletes them and ships the smaller app.
If anyone knocks while a feature is switched off, it comes back automatically.

Built for the GitLab Transcend hackathon, *Life After Code*: Path A (start fresh), **Hands-off**.

## How a feature dies

1. **Census.** Every route counts its calls. A scheduled job joins 400 days of usage with static analysis and writes
   `census/latest.json` to the `afterlife/census` branch.
2. **Coroner** (Duo agent). A human opens one issue titled `AFTERLIFE census`. The Coroner writes a death certificate
   per candidate: DEAD, HIBERNATING, PROTECTED, ALIVE or INSUFFICIENT_EVIDENCE, with the evidence and a machine-readable
   verdict. It refuses to call seasonal or protected code dead.
3. **Undertaker** (Duo agent). Runs only if something is DEAD. Deletes the feature, its tests and its now-unused
   dependencies, adds a tombstone to `afterlife/graveyard.yaml`, and opens a Sunset MR.
4. **Reviewer** (Duo agent). Checks the diff against the verdict and posts `AFTERLIFE-REVIEW: PASS` or `BLOCK`.
5. **Gates** (CI). Tests, SAST, secret detection, CVEs before and after, unused code before and after, and
   `verdict_check` against the policy **from the target branch**, so an MR can't loosen the rules that judge it.
6. **Coma and vigil** (CI). The feature flag goes off in production. The route answers `410 Gone` and every request is
   logged as a knock. One knock resurrects it.
7. **Merge, release, canary** (CI). A deterministic gate merges, pinned to the tested commit. CI releases, Cloud Run
   takes 10% of traffic, then 100%, or rolls back.
8. **Obituary** (CI). Measured savings (lines, dependencies, CVEs, image size, SCI) go on the census issue and the live
   `/graveyard` page.

If a knock arrives during the vigil, CI turns the flag back on and closes the MR, and the **Medium** (Duo agent)
explains who still depends on the feature and records it as resurrected.

## All 9 DevSecOps stages

| Stage | What AFTERLIFE does | Where |
| --- | --- | --- |
| Plan | Coroner writes death certificates from evidence | [`flows/afterlife-retire.yml`](flows/afterlife-retire.yml) |
| Create | Undertaker deletes the feature and opens the Sunset MR | [`flows/afterlife-retire.yml`](flows/afterlife-retire.yml) |
| Verify | Tests, unused-code re-check, Reviewer agent, verdict check | [`ci/pipelines/sunset.yml`](ci/pipelines/sunset.yml), [`ci/verdict_check.py`](ci/verdict_check.py) |
| Package | Container image to GitLab registry and Artifact Registry, size before and after | [`.gitlab-ci.yml`](.gitlab-ci.yml), [`ci/pipelines/main.yml`](ci/pipelines/main.yml) |
| Secure | SAST, secret detection, `pip-audit` CVEs before and after | [`.gitlab-ci.yml`](.gitlab-ci.yml), [`ci/diff_checks.py`](ci/diff_checks.py) |
| Release | Merge gate, GitLab Release with deprecation notes, Cloud Run canary | [`ci/gate_merge.py`](ci/gate_merge.py), [`ci/pipelines/main.yml`](ci/pipelines/main.yml) |
| Configure | Feature flags (coma and resurrection), Terraform for Google Cloud | [`ci/coma.py`](ci/coma.py), [`infra/`](infra/) |
| Monitor | Usage census, vigil for knocks, canary error-rate watch and rollback | [`ci/census.py`](ci/census.py), [`ci/vigil.py`](ci/vigil.py), [`ci/canary_watch.py`](ci/canary_watch.py) |
| Govern | Policy from the target branch, protected paths, CODEOWNERS, graveyard ledger, agent rules | [`afterlife/policy.yaml`](afterlife/policy.yaml), [`CODEOWNERS`](CODEOWNERS), [`AGENTS.md`](AGENTS.md) |

## Why Hands-off holds up

The only human action is opening the census issue. GitLab flows must be started by a person, and that issue is the
intent. Everything after it, including merge and production deploy, is agents plus deterministic gates. Agents can't
merge (GitLab's flow token doesn't allow it), so a CI job with its own token merges, and only after every gate passes.
Policy decides when a retirement needs a human approval (`requires_approval`), which keeps risky areas supervised.

## The demo app: Shelf

| Feature | Route | Planted situation | Expected outcome |
| --- | --- | --- | --- |
| `books_v1` | `GET /v1/books` | Replaced by v2, silent about 200 days | Retired, hands-off |
| `import_goodreads` | `POST /import/goodreads` | Never called; sole user of a vulnerable `requests` pin | Retired, CVEs removed with it |
| `wrapped` | `GET /wrapped/{year}` | Busy only in December | Kept as HIBERNATING |
| `embed_widget` | `GET /embed/widget` | Silent 71 days, but a partner still calls it occasionally | Switched off, knocked, resurrected |
| `admin_reindex` | `POST /admin/reindex` | Rare, and protected by policy | Never auto-retired |
| `books_v2` | `GET /v2/books` | Live | Untouched |

**Simulated vs live data:** `scripts/seed_history.py` writes 400 days of history, every call marked `simulated`, and
the census reports the simulated share. Traffic during the vigil and canary comes from `scripts/traffic.py` against the
live service. Carbon and savings numbers come from real pipeline runs.

## Sustainability

SCI per pipeline run, with every coefficient sourced: see [docs/sci.md](docs/sci.md).

## Layout

```
app/          Shelf (FastAPI): features, usage gate, flags, store, /graveyard
afterlife/    policy.yaml (rules), graveyard.yaml (ledger), sci_coefficients.yaml
flows/        Duo custom flows: retire (Coroner, Undertaker, Reviewer) and resurrect (Medium)
ci/           census, gates, coma, vigil, merge, canary, measure, obituary, with tests
ci/pipelines/ census, Sunset MR, main and Terraform pipelines
infra/        Terraform for Google Cloud
scripts/      seed_history.py, traffic.py
docs/         sci.md, runbook-om.md
AGENTS.md     rules every agent follows
```

## Set up

1. **Flows:** in GitLab, go to **AI > Flows > New flow**, paste each file from `flows/`, enable it for the group and
   project, and add the trigger (retire: work item created; resurrect: mention).
2. **Google Cloud and CI variables:** follow [docs/runbook-om.md](docs/runbook-om.md). Deploy jobs stay out of the
   pipeline until `GCP_PROJECT_ID` is set.
3. **Runner:** pipelines run on a self-hosted GitLab Runner (Docker executor, privileged, for Docker-in-Docker).

## Run locally

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest

# Seed history into a local file store and run the census
export AFTERLIFE_STORE=json:demo.local.json
python -m scripts.seed_history
python -m ci.census --out census/latest.json

# Serve the app; turn a feature off with AFTERLIFE_FLAGS_OFF=books_v1
uvicorn app.main:app --reload
```

| Variable | Purpose |
| --- | --- |
| `AFTERLIFE_STORE` | `memory` (default), `json:<path>`, or `firestore` |
| `AFTERLIFE_FLAGS_OFF` | Comma-separated flags to turn off locally |
| `UNLEASH_URL`, `UNLEASH_INSTANCE_ID`, `UNLEASH_APP_NAME` | GitLab feature flags in production |
| `ADMIN_TOKEN` | Token for `/admin/reindex` |

## License

MIT. See [LICENSE](LICENSE).
