# Sustainability: how AFTERLIFE measures carbon

AFTERLIFE removes code nobody uses, which means less to build, test, scan, ship and serve. This page says how we
measure that, what each number is made of, and where the numbers are estimates.

**Standard:** Software Carbon Intensity (SCI) from the Green Software Foundation, published as
[ISO/IEC 21031:2024](https://scc-ccn.ca/standardsdb/standards/2053951).

```
SCI = ((E × I) + M) per R
```

| Term | Meaning | Our value |
| --- | --- | --- |
| E | Energy used, kWh | From measured CI job minutes, using the coefficients below |
| I | Carbon intensity of the grid, gCO2e/kWh | Grid where the runner draws power |
| M | Embodied emissions of the hardware, gCO2e | Share of manufacturing emissions for the time used |
| R | Functional unit | **One CI pipeline run** |

## Why a pipeline run is the unit

Every retirement shrinks what each pipeline does: fewer tests, fewer files to scan, fewer dependencies to install and
audit, a smaller image to build and push. The pipeline runs on every push and every merge request for the life of the
project, so a saving per run keeps paying. We measure it directly: `ci/measure.py` compares the runner minutes of the
pipelines before and after a retirement, with the same jobs on the same runner (`ci/runner_minutes.py`).

## Coefficients and sources

All values live in [`afterlife/sci_coefficients.yaml`](../afterlife/sci_coefficients.yaml). Every one has a source,
and `measure.py` refuses to compute SCI if any is missing. Checked on 2026-10-24.

| Input | Value | Source |
| --- | --- | --- |
| CPU power, min / max per vCPU | 0.71 W / 4.26 W (medians) | [Cloud Carbon Footprint methodology](https://www.cloudcarbonfootprint.org/docs/methodology), GCP |
| CPU utilisation | 50% | Stated assumption, not measured |
| Memory energy | 0.000392 kWh per GB-hour | Cloud Carbon Footprint methodology |
| PUE | 1.1 | Cloud Carbon Footprint methodology, GCP |
| Grid intensity, CI runner | 598 gCO2e/kWh | [Google region carbon data](https://cloud.google.com/sustainability/region-carbon), 2025, `asia-south1` |
| Embodied emissions | 1.12 gCO2e per vCPU-hour | [CCF embodied method](https://www.cloudcarbonfootprint.org/docs/embodied-emissions) with the E2 platform from [ccf-coefficients](https://github.com/cloud-carbon-footprint/ccf-coefficients) |
| Runner size | 14 vCPU, 8 GB | `docker info` on the runner |

**How the embodied rate is derived:** CCF gives M = TE × (TR / EL) × (RR / total resources). For the E2 platform,
TE = 1,255.46 kgCO2e, EL = 4 years (35,040 hours), and the largest E2 machine has 32 vCPUs. So
1,255,460 g ÷ 35,040 h ÷ 32 = 1.12 gCO2e per vCPU-hour.

## Today's baseline

[Pipeline #2984790237](https://gitlab.com/afterlife-transcend/AFTERLIFE/-/pipelines/2984790237) (tests, vulture,
SAST, secret detection, dependency audit, image build) used 3.66 job-minutes. With the coefficients above:

| E | I | M | SCI per run |
| --- | --- | --- | --- |
| 0.00254 kWh | 598 gCO2e/kWh | 0.96 gCO2e | **2.48 gCO2e** |

Each retirement's before and after SCI comes from the `measure` job and appears on the obituary, in `savings.json`, and
on the live [`/graveyard`](../app/graveyard.py) page, linked to the job that measured it. We don't project savings we
haven't measured.

## Measured retirements

The `measure` job compares the same set of jobs before and after a retirement, so its per-run figures are lower than
the full-pipeline baseline above.

| Retirement | Lines removed | Dependencies / CVEs removed | Image | SCI per pipeline run | Measured by |
| --- | --- | --- | --- | --- | --- |
| `books_v1` (!1) | 26 | none | not measured | 1.3949 → 1.3813 gCO2e (−0.0136) | [job 17441216925](https://gitlab.com/afterlife-transcend/AFTERLIFE/-/jobs/17441216925) |
| `import_goodreads` (!2) | 72 | `requests==2.31.0` pin; 3 CVEs (PYSEC-2026-1872, -1873, -2275) | 70.5 → 70.6 MB | 1.3746 → 1.3678 gCO2e (−0.0068) | [job 17441604134](https://gitlab.com/afterlife-transcend/AFTERLIFE/-/jobs/17441604134) |
| **Total** | **98** | **1 pin, 3 CVEs** | | **−0.0204 gCO2e per run** | |

**Why the image didn't shrink:** removing the importer removed the vulnerable `requests` pin, but `google-api-core`
(used by the Firestore client) requires `requests>=2.33.0`, so a patched `requests` is still installed. The CVEs are
gone because the patched version fixes them; the bytes are not.

## Design choices that cut carbon

| Choice | Effect |
| --- | --- |
| Serve Shelf from `europe-north1` (Finland) | 30 gCO2e/kWh against 598 for `asia-south1`, about 20× lower grid intensity for the same energy ([Google, 2025](https://cloud.google.com/sustainability/region-carbon)) |
| Cloud Run with minimum instances 0 | No idle compute between requests |
| Deterministic gates do the checking | Verdict check, vigil, merge gate and canary judgement are plain scripts, not LLM calls |
| Agents run only when there is work | The Undertaker runs only if the Coroner returns `RETIRE`; the Reviewer only after an MR exists |
| Deleting dead code | Fewer files to test and scan, fewer dependencies to install and audit, a smaller image to build, push and pull, on every future pipeline |

## Limits, stated plainly

- **The runner is a laptop, not a data centre.** CCF's cloud coefficients and a PUE of 1.1 are proxies for it.
  Per-run figures are estimates; the before and after comparison is more reliable than either number alone, because
  both use the same runner and coefficients.
- **Utilisation is assumed at 50%**, not measured.
- **The grid figure is a proxy.** Google's `asia-south1` value stands in for the runner's location in India.
- **The demo's usage history is simulated** and labelled as such. It affects which features the census flags, not the
  carbon numbers, which come from real pipeline runs.
- **Serving energy is not yet in R.** Cloud Run usage for Shelf is tiny at demo scale. The per-request saving from
  removed routes is not measured, so we don't claim it.
