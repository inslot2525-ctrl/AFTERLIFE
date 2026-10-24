"""Every feature router runs behind this gate: it counts calls and logs knocks."""

import datetime as dt

from fastapi import HTTPException, Request


def feature_gate(feature: str):
    def dependency(request: Request) -> None:
        state = request.app.state
        now = dt.datetime.now(dt.timezone.utc)
        if not state.flags.is_enabled(feature):
            caller = request.headers.get("x-partner-key") or request.headers.get("user-agent", "unknown")
            state.store.record_knock(feature, caller, now)
            raise HTTPException(
                status_code=410,
                detail=f"'{feature}' is being retired. This request was logged; if you still need it, it will come back.",
            )
        state.store.record_hit(feature, now.date())

    return dependency
