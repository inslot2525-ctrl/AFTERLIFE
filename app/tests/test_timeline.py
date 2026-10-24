from app.timeline import build_timeline, is_retirement, render_timeline

URL = "https://gitlab.com/afterlife-transcend/AFTERLIFE"


def mr(iid, feature, state="opened", labels=("afterlife::sunset",), merge_sha=None):
    return {"iid": iid, "source_branch": f"afterlife/{feature}", "state": state, "labels": list(labels),
            "web_url": f"{URL}/-/merge_requests/{iid}", "merge_commit_sha": merge_sha}


def jobs(**statuses):
    return [{"id": i, "name": name.replace("_", "-"), "status": status, "web_url": f"{URL}/-/jobs/{i}"}
            for i, (name, status) in enumerate(statuses.items(), start=1)]


def fake_gitlab(mrs, mr_jobs, main_jobs=None):
    """mr_jobs: iid -> jobs of that MR's latest pipeline; main_jobs: merge sha -> jobs."""
    main_jobs = main_jobs or {}

    def fetch(path):
        if path.startswith("/merge_requests?"):
            return mrs
        if path.startswith("/merge_requests/"):
            iid = int(path.split("/")[2])
            return [{"id": 1000 + iid}] if iid in mr_jobs else []
        if path.startswith("/pipelines?sha="):
            sha = path.split("sha=")[1].split("&")[0]
            return [{"id": 2000 + list(main_jobs).index(sha)}] if sha in main_jobs else []
        pipeline = int(path.split("/")[2])
        if pipeline >= 2000:
            return list(main_jobs.values())[pipeline - 2000]
        return mr_jobs[pipeline - 1000]

    return fetch


def states(retirement):
    return {s["label"]: s["state"] for s in retirement["stages"]}


def test_vigil_in_progress():
    fetch = fake_gitlab([mr(5, "books_v1")], {5: jobs(review_check="success", verdict_check="success",
                                                       coma="success", vigil="running")})
    [r] = build_timeline(fetch)
    assert r["feature"] == "books_v1" and r["outcome"] == "in progress"
    assert states(r)["Vigil"] == "active" and states(r)["Merged"] == "todo"


def test_knock_resurrects():
    fetch = fake_gitlab([mr(6, "embed_widget", state="closed", labels=["afterlife::resurrected"])],
                        {6: jobs(review_check="success", verdict_check="success", coma="success",
                                 vigil="failed", resurrect="success")})
    [r] = build_timeline(fetch)
    assert r["outcome"] == "resurrected"
    assert r["stages"][-1]["label"] == "Resurrected" and "Merged" not in states(r)
    # The vigil job fails on a knock by design; the timeline shows the knock, not an error.
    assert states(r)["Vigil"] == "knocked"


def test_full_retirement():
    gates = jobs(review_check="success", verdict_check="success", coma="success", vigil="success",
                 gate_merge="success")
    main = jobs(canary_watch="success", promote="success", rollback="success", obituary="success")
    fetch = fake_gitlab([mr(7, "import_goodreads", state="merged", merge_sha="abc")], {7: gates}, {"abc": main})
    [r] = build_timeline(fetch)
    assert r["outcome"] == "retired"
    assert [s["label"] for s in r["stages"]][-3:] == ["Canary", "Live", "Obituary"]


def test_rollback_is_its_own_outcome():
    gates = jobs(review_check="success", verdict_check="success", coma="success", vigil="success",
                 gate_merge="success")
    main = jobs(canary_watch="success", promote="success", rollback="failed")
    fetch = fake_gitlab([mr(8, "books_v1", state="merged", merge_sha="def")], {8: gates}, {"def": main})
    [r] = build_timeline(fetch)
    assert r["outcome"] == "rolled back" and r["stages"][-1]["label"] == "Rolled back"


def test_failed_gate_shows_failed():
    fetch = fake_gitlab([mr(9, "books_v1")], {9: jobs(review_check="success", verdict_check="failed")})
    [r] = build_timeline(fetch)
    assert r["outcome"] == "failed" and states(r)["Gates"] == "failed"


def test_only_sunset_mrs_count():
    assert is_retirement(mr(1, "books_v1"))
    assert not is_retirement(mr(2, "census"))
    assert not is_retirement(mr(3, "resurrect-embed_widget"))
    assert not is_retirement(mr(4, "books_v1", state="closed", labels=[]))
    assert not is_retirement({**mr(5, "x"), "source_branch": "feature/login"})


def test_render_links_every_stage_and_escapes():
    fetch = fake_gitlab([mr(5, "<b>v1</b>")], {5: jobs(review_check="success")})
    html = render_timeline(build_timeline(fetch))
    assert "&lt;b&gt;v1" in html and "<b>v1</b>" not in html
    assert f"{URL}/-/jobs/1" in html


def test_empty_state_explains_how_to_start():
    assert "AFTERLIFE census" in render_timeline([])


def test_running_vigil_gets_a_countdown_and_knock_count():
    import datetime as dt

    from app.timeline import clock_text

    started = "2026-10-25T10:00:00Z"
    vigil = [{"id": 9, "name": "vigil", "status": "running", "started_at": started, "web_url": f"{URL}/-/jobs/9"}]
    fetch = fake_gitlab([mr(5, "books_v1")], {5: jobs(review_check="success", verdict_check="success",
                                                       coma="success") + vigil})
    heard = []
    [r] = build_timeline(fetch, knocks=lambda feature, since: heard.append((feature, since)) or 0)
    stage = next(s for s in r["stages"] if s["label"] == "Vigil")
    assert stage["deadline"].startswith("2026-10-25T10:10:00")  # policy vigil_minutes = 10
    assert stage["knocks"] == 0 and heard[0][0] == "books_v1"

    now = dt.datetime(2026, 10, 25, 10, 3, 48, tzinfo=dt.timezone.utc)
    assert clock_text(stage["deadline"], now) == "6:12 left"
    assert clock_text(stage["deadline"], now + dt.timedelta(minutes=7)) == "deciding"
    html = render_timeline([r])
    assert "class='countdown' data-deadline=" in html and "0 knocks" in html


def test_finished_vigil_has_no_countdown():
    fetch = fake_gitlab([mr(5, "books_v1")], {5: jobs(vigil="success")})
    [r] = build_timeline(fetch, knocks=lambda f, s: 0)
    assert "deadline" not in next(s for s in r["stages"] if s["label"] == "Vigil")
