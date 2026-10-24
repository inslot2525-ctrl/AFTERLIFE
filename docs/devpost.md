# Devpost submission text (draft)

Paste each section into the matching Devpost field. Replace every `[FILL: ...]` with a number or link from a real
run before submitting; leave nothing invented.

**Category:** Path A: Start Fresh · Hands-off · opted in to Most Environmentally Impactful

**Links:**
- GitLab project: https://gitlab.com/afterlife-transcend/AFTERLIFE
- Live app on Google Cloud: [FILL: SHELF_URL]/graveyard
- Demo video: [FILL: YouTube link]

---

## Tagline

Every team automates code on its way into production. AFTERLIFE automates the way out.

## Inspiration

Code generation made writing code cheap, so codebases grow faster than ever. Nothing removes code. Features stop being
used, but their routes, tests and dependencies stay. Every pipeline keeps testing, scanning and shipping them, and
their old dependencies keep collecting CVEs. Deleting code is scary because nobody can prove it's unused, so nobody
does it. The hackathon asks what happens after code. We think the honest answer is that code dies, and nobody
automates that part.

## What it does

AFTERLIFE retires dead features end to end, from production evidence to a smaller app in production:

1. **Census:** every route counts its calls; a scheduled job joins a year of usage with static analysis.
2. **Coroner** (Duo agent): writes a death certificate for each candidate, with evidence and a machine-readable verdict.
   It refuses to kill seasonal or protected code ("hibernating, not dead").
3. **Undertaker** (Duo agent): deletes the feature, its tests and now-unused dependencies, and opens a Sunset MR.
4. **Reviewer** (Duo agent): checks the diff against the verdict.
5. **Gates:** tests, SAST, secret detection, CVEs before and after, and a verdict check against policy read from the
   target branch.
6. **Coma and vigil:** the feature flag goes off in production; any request gets `410 Gone` and is logged as a knock.
7. **Resurrection:** one knock and the flag comes back, the MR closes, and the **Medium** (Duo agent) explains who
   still needs the feature.
8. **Merge, release, canary, obituary:** a deterministic gate merges, Cloud Run canaries then promotes or rolls back,
   and the measured savings go on the issue and the live Graveyard page.

A human opens one issue. Nothing else is manual.

## How we built it

- **GitLab Duo Agent Platform:** two custom flows (Flow Registry v1). The retire flow chains Coroner, Undertaker and
  Reviewer, with a conditional router so the Undertaker runs only when something is DEAD. The resurrect flow runs the
  Medium. Agents use GitLab tools (issue and MR notes, diffs) plus `git` and `glab`.
- **GitLab CI/CD:** census, Sunset MR and main pipelines. Every decision that matters is a plain script with tests:
  verdict check, vigil, merge gate pinned to the tested commit, canary judgement, rollback, measurement.
- **GitLab features:** feature flags (Unleash protocol) for coma and resurrection, protected branches, CODEOWNERS,
  container registry, Releases, SAST and secret detection templates.
- **Google Cloud:** Cloud Run (scale to zero), Firestore, Artifact Registry, keyless auth from GitLab OIDC through
  Workload Identity Federation, all in Terraform, in `europe-north1`.
- **The app:** Shelf, a small FastAPI reading-list app with five planted situations: a legacy API, a dead importer
  holding a vulnerable dependency, a December-only feature, a forgotten partner widget, and a protected admin path.

## Lifecycle stages covered

Plan, Create, Verify, Package, Secure, Release, Configure, Monitor, Govern: all nine. The README maps each stage to the
file that implements it.

## Challenges we ran into

- **Flows can only be started by a person.** We made the single human action, opening the census issue, the
  statement of intent, and put everything after it in one flow plus CI.
- **Agents can't merge.** GitLab's flow token doesn't allow it, which is right. A deterministic CI gate merges instead,
  only after every check passes, pinned to the commit the pipeline tested.
- **Agents could loosen their own rules.** The gates read policy from the target branch, never from the MR under review.
- **Proving something is unused is hard.** Seasonal features look dead in a 30-day window, so the census looks back
  400 days, and the vigil gives real traffic the final say.
- **Identity verification without a credit card.** We run CI on a self-hosted runner.

## Accomplishments that we're proud of

- The agents decide, and plain code with tests checks every decision before anything changes. [FILL: test count] tests
  cover the gates.
- The system says when it's wrong. A resurrection is a first-class outcome, not a failure.
- Nothing is invented: every number on the Graveyard page links to the CI job that measured it, and simulated demo
  traffic is labelled as simulated.
- From the demo run: [FILL: lines removed] lines, [FILL: n] dependencies and [FILL: n] CVEs removed;
  image [FILL: before → after] MB.

## What we learned

The interesting part of agentic DevOps is not what the agent can do but what it's allowed to do and how you prove it
was right. Splitting judgement (agents) from enforcement (deterministic gates) made the system both more autonomous
and safer.

## What's next

- Longer vigils for real services (policy already supports days instead of minutes).
- Cross-repo callers through GitLab Orbit before calling anything dead.
- Dead branches inside live functions, using runtime coverage.
- Per-request SCI for serving, not just per pipeline run.

## Sustainability statement (Most Environmentally Impactful)

We measure Software Carbon Intensity (Green Software Foundation, ISO/IEC 21031:2024) with one CI pipeline run as the
functional unit, because every retirement shrinks every future pipeline. Coefficients come from the Cloud Carbon
Footprint methodology and Google's 2025 region carbon data, each with a source, in `afterlife/sci_coefficients.yaml`.
Our measured baseline is 2.48 gCO2e per pipeline run. The demo retirements took it to [FILL: after] gCO2e
([FILL: delta] per run). Design choices: serving from `europe-north1` (30 gCO2e/kWh against 598 for Mumbai), Cloud
Run scaling to zero, deterministic scripts instead of LLM calls for every check, and agents that run only when there is
work. Method, sources and limits: `docs/sci.md`.

## Built with

GitLab Duo Agent Platform, GitLab CI/CD, GitLab feature flags, Google Cloud Run, Firestore, Artifact Registry,
Workload Identity Federation, Terraform, Python, FastAPI
