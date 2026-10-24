# AFTERLIFE

**Every team automates code on its way into production. AFTERLIFE automates the way out.**

Production telemetry finds features nobody uses. GitLab Duo agents write the
evidence, switch the feature off behind a flag, and hold a vigil for real
traffic. Then they delete the code, tests and dependencies, and CI ships the
smaller app. If anyone knocks during the vigil, the feature is resurrected
automatically.

Built for the GitLab Transcend hackathon, *Life After Code* (Path A,
Hands-off).

## How a feature dies

1. **Census** (Monitor): a scheduled job joins per-route usage with static
   analysis into `census/latest.json`.
2. **Coroner** (Plan): a Duo agent writes a death certificate per candidate:
   DEAD, HIBERNATING, PROTECTED, ALIVE or INSUFFICIENT_EVIDENCE.
3. **Undertaker** (Create): for each DEAD verdict, deletes the feature and opens
   a Sunset MR.
4. **Gates** (Verify, Secure, Package): tests, SAST, secret detection, CVE count
   before vs after, image size, and `verdict_check` against policy read from
   the target branch.
5. **Coma and vigil** (Configure, Monitor): the feature flag goes off in
   production. Any request now returns `410 Gone` and is logged as a knock.
6. **Resurrection**: one knock and the flag comes back on, the MR closes, and
   the Medium agent explains who still needs it.
7. **Merge, release, canary** (Govern, Release): a deterministic gate merges,
   CI releases, and Cloud Run shifts traffic 10% then 100%, or rolls back.
8. **Obituary**: measured savings land in `afterlife/graveyard.yaml` and on
   `/graveyard`.

## The demo app: Shelf

| Feature | Route | Planted situation |
| --- | --- | --- |
| `books_v1` | `GET /v1/books` | Replaced by v2, silent ~200 days |
| `books_v2` | `GET /v2/books` | Live |
| `import_goodreads` | `POST /import/goodreads` | Never called; sole user of a vulnerable `requests` pin |
| `wrapped` | `GET /wrapped/{year}` | Busy only in December |
| `embed_widget` | `GET /embed/widget` | Silent 71 days, but a partner still calls it occasionally |
| `admin_reindex` | `POST /admin/reindex` | Rare, and protected by policy |

**Simulated vs live data:** `scripts/seed_history.py` writes 400 days of
history, every call marked `simulated`, and the census reports the simulated
share. Demo traffic during the vigil and canary comes from
`scripts/traffic.py` against the live service.

## Layout

```
app/          Shelf (FastAPI): features, usage gate, flags, store, /graveyard
afterlife/    policy.yaml (rules, read from the target branch), graveyard.yaml (ledger)
ci/           census, verdict_check, vigil: the deterministic gates, with tests
flows/        Duo custom flows and agent prompts
scripts/      seed_history.py, traffic.py
infra/        Terraform for Google Cloud
AGENTS.md     rules every agent follows
```

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
