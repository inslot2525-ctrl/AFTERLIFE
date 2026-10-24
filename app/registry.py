"""What the census needs to know about each feature."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Feature:
    name: str  # also the GitLab feature flag name
    route: str
    module: str  # repo-relative path; the Undertaker deletes this file
    owner: str
    born: str
    summary: str
