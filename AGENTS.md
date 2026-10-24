# Rules for every AFTERLIFE agent

These rules apply to the Coroner, Undertaker, Reviewer and Medium. CI enforces
the hard ones, so breaking them fails the pipeline anyway.

1. **Evidence or nothing.** Every claim cites the census file, Orbit, or the
   code. If you can't ground a number, say "not verified" instead of guessing.
2. **When the evidence is unclear, keep it.** Prefer HIBERNATING or
   INSUFFICIENT_EVIDENCE over DEAD when the census numbers don't add up. A wrong
   deletion costs far more than a late one. A DEAD verdict deletes nothing by
   itself, though: the flag goes off and a vigil listens for real traffic first,
   so callers the census can't see are what the vigil is for.
3. **Never touch** `afterlife/policy.yaml`, `ci/`, `flows/`, `infra/`,
   `CODEOWNERS`, `LICENSE`, or anything listed in `protected_paths`.
4. **Never drop data.** No migration may delete a table or column. Archive it.
5. **Stay in scope.** A Sunset MR changes only the files listed in its DEAD
   verdict, plus `app/features/__init__.py`, the feature's tests,
   `requirements.txt` and a tombstone in `afterlife/graveyard.yaml`.
6. **Be idempotent.** Before creating a branch or MR, check whether
   `afterlife/<feature>` already exists. If it does, update it.
7. **Machine-readable verdicts.** End every verdict with a fenced
   `afterlife-verdict` JSON block. CI parses it; prose alone does not count.
8. **You do not merge, release or deploy.** Deterministic CI jobs do that.
