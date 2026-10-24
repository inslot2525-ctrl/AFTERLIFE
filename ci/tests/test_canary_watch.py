"""canary_watch against a fake Cloud Monitoring client and a fake Cloud Run URL.

The first live canary crashed because list_time_series got aggregation as a
keyword argument, and /healthz can never answer 200 on Cloud Run (reserved).
"""

import json
from types import SimpleNamespace

import pytest

pytest.importorskip("google.cloud.monitoring_v3")

from ci import canary_watch  # noqa: E402


def point(int64=0, double=0.0):
    return SimpleNamespace(value=SimpleNamespace(int64_value=int64, double_value=double))


class FakeMonitoring:
    def __init__(self):
        self.requests = []

    def list_time_series(self, request=None, **kwargs):
        # The real client rejects keyword options such as aggregation=.
        assert not kwargs, f"options must go in request=, got {sorted(kwargs)}"
        self.requests.append(request)
        if "request_count" in request["filter"]:
            return [SimpleNamespace(metric=SimpleNamespace(labels={"response_code_class": "2xx"}), points=[point(40)]),
                    SimpleNamespace(metric=SimpleNamespace(labels={"response_code_class": "5xx"}), points=[point(2)])]
        return [SimpleNamespace(metric=SimpleNamespace(labels={}), points=[point(double=180.0)])]


def test_metrics_pass_options_as_one_request():
    client = FakeMonitoring()
    requests, errors, p95 = canary_watch.revision_metrics("proj", "shelf", "shelf-00002", 5, client=client)
    assert (requests, errors, p95) == (42, 2, 180.0)
    assert all(r["name"] == "projects/proj" and "shelf-00002" in r["filter"] for r in client.requests)
    assert "aggregation" in client.requests[1]


def test_synthetic_check_uses_health_not_healthz(monkeypatch):
    asked = []
    monkeypatch.setattr(canary_watch, "http_status", lambda url: asked.append(url) or 200)
    assert canary_watch.synthetic_ok("https://canary.run.app", None)
    assert asked == ["https://canary.run.app/health"]


def test_metrics_failure_rolls_back_instead_of_crashing(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CANARY_URL", "https://canary.run.app")
    monkeypatch.setenv("CANARY_REVISION", "shelf-00002")
    monkeypatch.setenv("GCP_PROJECT_ID", "proj")
    monkeypatch.setattr(canary_watch, "http_status", lambda url: 200)
    monkeypatch.setattr(canary_watch.time, "sleep", lambda s: None)

    def broken(*args, **kwargs):
        raise PermissionError("monitoring.timeSeries.list denied")

    monkeypatch.setattr(canary_watch, "revision_metrics", broken)
    policy = tmp_path / "policy.yaml"
    policy.write_text("canary: {watch_minutes: 0, traffic_percent: 10, max_5xx_rate: 0.01}\n")
    monkeypatch.setattr("sys.argv", ["canary_watch", "--policy", str(policy), "--minutes", "0"])

    canary_watch.main()
    assert (tmp_path / "canary.env").read_text() == "CANARY_RESULT=rollback\n"
    assert "metrics unavailable" in json.loads((tmp_path / "canary.json").read_text())["problems"][0]
