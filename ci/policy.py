"""Loading afterlife/policy.yaml and matching paths against it."""

from pathlib import Path

import yaml

DEFAULT_POLICY = Path("afterlife/policy.yaml")


def load_policy(path: str | Path = DEFAULT_POLICY) -> dict:
    return yaml.safe_load(Path(path).read_text())


def matches(path: str, patterns: list[str]) -> bool:
    """Exact file match, or directory match when the pattern ends with '/'."""
    path = path.replace("\\", "/")
    return any(path == p or (p.endswith("/") and path.startswith(p)) for p in patterns)


def is_protected(path: str, policy: dict) -> bool:
    return matches(path, policy.get("protected_paths", []))


def is_allowed_collateral(path: str, policy: dict) -> bool:
    return matches(path, policy.get("allowed_collateral", []))
