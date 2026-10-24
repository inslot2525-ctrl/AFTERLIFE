from ci.publish_savings import with_links


def test_links_point_back_to_mr_job_and_release(monkeypatch):
    monkeypatch.setenv("CI_PROJECT_URL", "https://gitlab.com/afterlife-transcend/AFTERLIFE")
    monkeypatch.setenv("CI_JOB_URL", "https://gitlab.com/afterlife-transcend/AFTERLIFE/-/jobs/9")
    monkeypatch.setenv("RELEASE_TAG", "retire-books_v1")
    linked = with_links({"feature": "books_v1", "mr_iid": 7})
    assert linked["mr_url"].endswith("/-/merge_requests/7")
    assert linked["measured_job_url"].endswith("/-/jobs/9")
    assert linked["release_url"].endswith("/-/releases/retire-books_v1")


def test_without_ci_env_savings_are_unchanged(monkeypatch):
    monkeypatch.delenv("CI_PROJECT_URL", raising=False)
    assert with_links({"feature": "books_v1", "mr_iid": 7}) == {"feature": "books_v1", "mr_iid": 7}
