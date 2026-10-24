"""Feature flags. In production these are GitLab feature flags (Unleash protocol)."""

from __future__ import annotations

import os
from typing import Protocol


class Flags(Protocol):
    def is_enabled(self, feature: str) -> bool: ...


class EnvFlags:
    """Local and test flags: AFTERLIFE_FLAGS_OFF=books_v1,embed_widget."""

    def __init__(self, off: set[str] | None = None) -> None:
        if off is None:
            off = {name for name in os.environ.get("AFTERLIFE_FLAGS_OFF", "").split(",") if name}
        self._off = set(off)

    def is_enabled(self, feature: str) -> bool:
        return feature not in self._off

    def set(self, feature: str, enabled: bool) -> None:
        if enabled:
            self._off.discard(feature)
        else:
            self._off.add(feature)


class GitLabFlags:
    def __init__(self, url: str, instance_id: str, environment: str) -> None:
        from UnleashClient import UnleashClient

        self._client = UnleashClient(
            url=url,
            app_name=environment,
            instance_id=instance_id,
            disable_metrics=True,
            disable_registration=True,
        )
        self._client.initialize_client()

    def is_enabled(self, feature: str) -> bool:
        # A flag GitLab doesn't know about stays on: an outage must not retire features.
        return self._client.is_enabled(feature, fallback_function=lambda *_: True)


def flags_from_env() -> Flags:
    url = os.environ.get("UNLEASH_URL")
    if url:
        return GitLabFlags(
            url=url,
            instance_id=os.environ["UNLEASH_INSTANCE_ID"],
            environment=os.environ.get("UNLEASH_APP_NAME", "production"),
        )
    return EnvFlags()
