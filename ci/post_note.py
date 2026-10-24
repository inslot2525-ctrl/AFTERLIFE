"""Post a file to the current MR as a collapsed note.

    python -m ci.post_note plan.txt "terraform plan for infra/"
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from ci.gitlab import GitLab

MAX_CHARS = 60_000


def render(title: str, body: str) -> str:
    if len(body) > MAX_CHARS:
        body = body[:MAX_CHARS] + "\n... (truncated; the full output is in the job artifacts)"
    return f"<details><summary>{title}</summary>\n\n```\n{body}\n```\n</details>"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("file", type=Path)
    parser.add_argument("title")
    args = parser.parse_args()
    GitLab().comment_mr(os.environ["CI_MERGE_REQUEST_IID"], render(args.title, args.file.read_text()))


if __name__ == "__main__":
    main()
