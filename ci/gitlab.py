"""A small GitLab REST client for the CI gates, plus helpers they share.

The token is a project access token in AFTERLIFE_TOKEN (api scope, Maintainer):
the Duo flow token can't merge, so the deterministic jobs act with this one.

    python -m ci.gitlab mr-description --out mr.md
    python -m ci.gitlab image-size --tag 1a2b3c4d
"""

from __future__ import annotations

import argparse
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BRANCH_PREFIX = "afterlife/"
FEATURE_NAME = re.compile(r"[a-z0-9][a-z0-9_-]*")


class GitLabError(RuntimeError):
    pass


def feature_from_branch(branch: str) -> str:
    """afterlife/books_v1 -> books_v1. The census branch is not a feature."""
    feature = branch.removeprefix(BRANCH_PREFIX)
    if not branch.startswith(BRANCH_PREFIX) or feature == "census" or not FEATURE_NAME.fullmatch(feature):
        raise GitLabError(f"{branch!r} is not an afterlife/<feature> branch")
    return feature


class GitLab:
    def __init__(self, token: str | None = None, api_url: str | None = None, project: str | None = None) -> None:
        self.token = token or os.environ["AFTERLIFE_TOKEN"]
        self.api = (api_url or os.environ.get("CI_API_V4_URL", "https://gitlab.com/api/v4")).rstrip("/")
        self.project = urllib.parse.quote(str(project or os.environ["CI_PROJECT_ID"]), safe="")

    def request(self, method: str, path: str, body: dict | None = None, query: dict | None = None,
                project_scoped: bool = True):
        url = f"{self.api}/projects/{self.project}{path}" if project_scoped else f"{self.api}{path}"
        if query:
            url += "?" + urllib.parse.urlencode(query)
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method, headers={
            "PRIVATE-TOKEN": self.token,
            "Content-Type": "application/json",
        })
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as e:
            raise GitLabError(f"GitLab {method} {path} -> {e.code}: {e.read().decode(errors='replace')[:500]}") from e

    def get(self, path: str, **query):
        return self.request("GET", path, query=query or None)

    def post(self, path: str, body: dict | None = None):
        return self.request("POST", path, body or {})

    def put(self, path: str, body: dict | None = None):
        return self.request("PUT", path, body or {})

    def mr(self, iid) -> dict:
        return self.get(f"/merge_requests/{iid}")

    def mr_notes(self, iid) -> list[dict]:
        return self.get(f"/merge_requests/{iid}/notes", per_page=100, sort="asc")

    def comment_mr(self, iid, text: str):
        return self.post(f"/merge_requests/{iid}/notes", {"body": text})

    def comment_issue(self, iid, text: str):
        return self.post(f"/issues/{iid}/notes", {"body": text})

    def set_flag(self, flag: str, active: bool) -> dict:
        """Idempotent: a retried job must not fail because the flag already moved."""
        current = self.get(f"/feature_flags/{flag}")
        if current.get("active") == active:
            return current
        return self.put(f"/feature_flags/{flag}", {"active": active})

    def image_size(self, tag: str) -> int | None:
        """Compressed size of the project's own registry image with this tag."""
        for repo in self.get("/registry/repositories") or []:
            if repo["path"] == os.environ.get("CI_PROJECT_PATH", repo["path"]):
                try:
                    return self.get(f"/registry/repositories/{repo['id']}/tags/{tag}").get("total_size")
                except GitLabError:
                    return None
        return None

    def merge_request_for_commit(self, sha: str) -> dict | None:
        """The Sunset MR a merge commit came from, if any."""
        mrs = self.get(f"/repository/commits/{sha}/merge_requests") or []
        return next((m for m in mrs if m["source_branch"].startswith(BRANCH_PREFIX)), None)


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    desc = sub.add_parser("mr-description", help="save the current MR's description to a file")
    desc.add_argument("--out", default="mr.md")
    size = sub.add_parser("image-size", help="print a registry image's size in bytes")
    size.add_argument("--tag", required=True)
    args = parser.parse_args()

    if args.command == "mr-description":
        mr = GitLab().mr(os.environ["CI_MERGE_REQUEST_IID"])
        Path(args.out).write_text(mr.get("description") or "")
        print(f"MR !{mr['iid']} description saved to {args.out}")
    elif args.command == "image-size":
        n = GitLab().image_size(args.tag)
        if n is None:
            raise SystemExit(f"no registry image tagged {args.tag}")
        print(n)


if __name__ == "__main__":
    main()
