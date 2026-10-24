# Medium

A feature was switched off for its vigil and somebody knocked. CI has already
turned the flag back on and closed the Sunset MR. Your job is to explain who
still needs it and make sure it is not retired again by mistake.

## Inputs

- `vigil.json` from the vigil job: each knock's caller, time and feature.
- The closed Sunset MR and its `afterlife-verdict` block.
- The census entry for the feature.

## Do

1. Comment on the MR: who knocked (caller key or user agent), when, and what
   that suggests about their usage pattern (for example, a quarterly job the
   30-day census window could not see). Say plainly that the census verdict
   was wrong and why.
2. Open an MR that moves the feature into `resurrected:` in
   `afterlife/graveyard.yaml` with `caller`, `knocked_at`, `reason` and a
   `recheck` date. If the pattern looks periodic, suggest a longer
   `lookback_days` in a comment for a human to decide; do not edit the policy.

Never delete code.
