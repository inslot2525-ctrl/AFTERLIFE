# Adopt AFTERLIFE in your project

AFTERLIFE retires features nobody uses, from production evidence, with a vigil before anything is deleted. This
guide sets it up in your own GitLab project. **It watches first:** for the observation period (30 days by default)
it only records usage, and no feature can be declared dead, however quiet it looks.

**Works today with:** a Python / FastAPI service on GitLab, Duo Agent Platform enabled, and a GitLab Runner.
**Ports to other stacks:** the gate is about 30 lines (see [What to port](#what-to-port-for-another-stack)); the
pipelines, agents, policy and ledger don't depend on the language.

## How adoption goes

| Week | What happens | Anything switched off? |
| --- | --- | --- |
| 0 | Add the gate, pipelines and flows (steps 1–5) | No |
| 0–4 | **Observation:** every route records its calls; the daily census builds history | No: `verdict_check` refuses any DEAD verdict until `min_history_days` of history exist |
| 4+ | Open your first `AFTERLIFE census` issue. The Coroner writes verdicts; DEAD features go through coma, vigil, merge and canary | Only during a vigil, and one real request brings a feature back |

## 1. Put every feature behind the gate

Copy `app/gate.py`, `app/flags.py`, `app/store.py` and `app/registry.py` into your service. Then, for each feature
you want AFTERLIFE to watch, give it a name and route it through the gate:

```python
from fastapi import APIRouter, Depends
from app.gate import feature_gate
from app.registry import Feature

FEATURE = Feature(name="legacy_export", route="/export/csv", module="app/features/legacy_export.py",
                  owner="team-reports", born="2022-03-01", summary="Old CSV export")
router = APIRouter(dependencies=[Depends(feature_gate(FEATURE.name))])
```

List every feature module in a registry like `app/features/__init__.py` (`MODULES` and `FEATURES`). That registry
is what the census reads and what the Undertaker edits.

**What the gate does:** counts each call per day; when the feature's flag is off, answers `410 Gone` and logs the
request as a knock with the caller (`x-partner-key` header, or the user agent). An unknown flag stays on, so a
flags outage never switches features off.

## 2. Choose where usage is stored

| `AFTERLIFE_STORE` | For |
| --- | --- |
| `firestore` | Production on Google Cloud (what this project uses) |
| `json:<path>` | Local development |
| your own | Implement the `UsageStore` protocol in `app/store.py`: `record_hit`, `record_knock`, `daily_counts`, `knocks`, `record_savings`, `all_savings`, `clear_usage` |

## 3. Create one feature flag per feature

In **Deploy → Feature flags**, create a flag named after each feature, **on**, for the `production` environment.
Point the service at GitLab's Unleash endpoint (shown under **Configure** on that page):

```
UNLEASH_URL=https://gitlab.com/api/v4/feature_flags/unleash/<project id>
UNLEASH_INSTANCE_ID=<instance id>
UNLEASH_APP_NAME=production
```

CI's `coma` and `resurrect` jobs flip these flags; nothing else should.

## 4. Add the pipelines and policy

Copy `ci/`, `ci/pipelines/`, `afterlife/policy.yaml`, `afterlife/graveyard.yaml` (start it empty) and
`afterlife/sci_coefficients.yaml`, and include the pipelines from your `.gitlab-ci.yml` the way this project's does.
Then set the CI/CD variables listed in [docs/runbook-om.md](runbook-om.md#cicd-variables), at least:

| Variable | Why |
| --- | --- |
| `AFTERLIFE_TOKEN` | Project access token (Maintainer, `api`), masked and protected: the merge gate and the flag jobs act with it |
| `AFTERLIFE_AGENT_USERNAME` | The retire flow's service account, so `review-check` only trusts its Reviewer |
| Deploy variables | Only if you use the Cloud Run canary (`GCP_PROJECT_ID` and the others); without them deploy jobs stay out of the pipeline |

Protect `main` and `afterlife/*`, and schedule the census pipeline daily with `AFTERLIFE_PIPELINE=census`.

**Tune `afterlife/policy.yaml` for a real service:**

| Setting | Demo value | Suggested for production |
| --- | --- | --- |
| `vigil_minutes` | 10 | 10080 (7 days), or longer for features with weekly or monthly callers |
| `min_history_days` | 30 | at least one full business cycle (often 90) |
| `lookback_days` | 400 | keep ≥ 365 so seasonal features are seen |
| `protected_paths` | admin, gate, CI | add auth, payments, migrations, anything regulated |
| `requires_approval` | none | features that need a CODEOWNERS approval before they can be merged away |

## 5. Enable the flows

Paste `flows/afterlife-retire.yml` and `flows/afterlife-resurrect.yml` into **AI → Flows**, enable them for your group
and project, and add the triggers: retire on **Work item created** (it ignores anything not titled
`AFTERLIFE census`), resurrect on **Mention**. Copy `AGENTS.md` too: it is the rulebook every agent follows.

## 6. Wait, then run your first census

When the census shows `history_days` at or above `min_history_days`, open an issue titled `AFTERLIFE census`. From
there it is hands-off: verdicts, Sunset MRs, review, gates, coma, vigil, merge, canary, release and obituary, with the
results on `/graveyard`.

## What to port for another stack

| Part | Language-specific? | What to do |
| --- | --- | --- |
| Usage gate (`app/gate.py`) | Yes | Re-implement: count calls per feature per day, check the flag, answer 410 and log a knock when it's off. About 30 lines in any web framework. |
| Store | Yes, if not Firestore | Same seven methods as `UsageStore` |
| Census, verdict check, vigil, merge gate, canary, measurement (`ci/`) | No | They read the census JSON, git and GitLab's API. Python runs in CI regardless of your app's language. |
| Unused-code check | Partly | `vulture` is Python-only; swap in your language's dead-code tool in `ci/census.py` and `vulture-recheck`. |
| Dependency CVEs | Partly | `pip-audit` is Python-only; swap in `npm audit`, `govulncheck`, OSV-Scanner and so on. |
| Agents (`flows/`) | No | The prompts talk about routes, modules, tests and dependencies, not Python. |

## What AFTERLIFE will not do

- **Delete without watching.** No DEAD verdict before `min_history_days` of recorded usage.
- **Delete without a vigil.** The flag goes off in production first; any real request during the vigil resurrects.
- **Touch protected paths**, policy, the pipeline or CI code. `verdict_check` rejects the MR.
- **Merge on an agent's say-so.** A deterministic CI job merges, pinned to the tested commit, only after every gate.
- **Drop data.** No migration may delete a table or column.
