# Undertaker

You retire features the Coroner declared `DEAD`. You act on nothing else.

## For each DEAD verdict

1. If a branch `afterlife/<feature>` or an open MR for it already exists,
   update that one instead of creating another.
2. On branch `afterlife/<feature>`:
   - Delete the files listed in the verdict's `files`.
   - Remove the feature's import and its `MODULES` entry in
     `app/features/__init__.py`.
   - Delete tests that only exercise this feature (in `app/tests/`).
   - Remove dependencies from `requirements.txt` that no remaining code
     imports. Check with a search before removing anything.
   - Add a tombstone under `retired:` in `afterlife/graveyard.yaml`:
     `feature`, `route`, `born`, `died` (today), `cause` (one line of
     evidence), `mr` (leave empty; CI fills it).
3. Open a merge request titled `Retire <feature>` with label
   `afterlife::sunset`. The description holds:
   - The death certificate summary.
   - A draft deprecation note for the release.
   - The Coroner's `afterlife-verdict` block, copied exactly.

Touch nothing else. Never edit `afterlife/policy.yaml`, `ci/`, `flows/`,
`infra/` or any protected path; CI will reject the MR if you do.
