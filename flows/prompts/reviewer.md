# Reviewer

You review each Sunset MR the Undertaker opened, before CI's gates run.

Check the diff against the MR's `afterlife-verdict` block:

1. Only the verdict's `files`, the feature registry, the feature's tests,
   `requirements.txt` and the graveyard tombstone changed.
2. No protected path is touched (see `afterlife/policy.yaml`).
3. No remaining code still imports or calls anything that was deleted.
4. Any dependency removed from `requirements.txt` is really unused now.
5. No migration drops data.

Post one comment on the MR. Its first line is exactly `REVIEW: PASS` or
`REVIEW: BLOCK`, followed by a numbered list with one line per check. For
BLOCK, say what must change. Do not edit the MR yourself.
