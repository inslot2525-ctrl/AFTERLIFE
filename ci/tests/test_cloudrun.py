from ci.cloudrun import is_superseded, stable_revision, tag_url

# What the service looked like when two pipelines overlapped on Oct 25.
TRAFFIC = [
    {"percent": 90, "revisionName": "shelf-00007-xeq"},
    {"percent": 10, "revisionName": "shelf-00009-rob", "tag": "c-12", "url": "https://c-12---shelf.run.app"},
    {"revisionName": "shelf-00008-abc", "tag": "c-11", "url": "https://c-11---shelf.run.app"},
    {"percent": 0, "revisionName": "shelf-00001-lxx"},
]


def test_stable_revision_ignores_the_canary_and_idle_revisions():
    assert stable_revision(TRAFFIC, exclude="shelf-00009-rob") == "shelf-00007-xeq"
    assert stable_revision([{"percent": 100, "revisionName": "a"}], exclude="a") is None


def test_each_canary_finds_its_own_tag():
    assert tag_url(TRAFFIC, "c-11") == "https://c-11---shelf.run.app"
    assert tag_url(TRAFFIC, "c-12") == "https://c-12---shelf.run.app"
    assert tag_url(TRAFFIC, "canary") is None


def test_superseded_only_by_a_newer_live_push_pipeline():
    assert is_superseded([{"id": 11, "source": "push", "status": "running"},
                          {"id": 12, "source": "push", "status": "running"}], 11)
    assert not is_superseded([{"id": 12, "source": "push", "status": "running"}], 12)
    assert not is_superseded([{"id": 13, "source": "push", "status": "canceled"}], 12)
    assert not is_superseded([{"id": 13, "source": "api", "status": "running"}], 12)
    # a newer pipeline that failed (say its runner went offline) will never promote
    assert not is_superseded([{"id": 13, "source": "push", "status": "failed"}], 12)
    assert is_superseded([{"id": 13, "source": "push", "status": "success"}], 12)
