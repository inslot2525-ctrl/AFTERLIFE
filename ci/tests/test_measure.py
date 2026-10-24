import copy
from pathlib import Path

import yaml

from ci.diff_checks import cve_diff, new_unused
from ci.measure import build_savings, cve_ids, deps_removed, line_totals, sci
from ci.obituary import census_issue, render
from ci.release_notes import deprecation_note
from ci.release_notes import render as render_release
from ci.resurrect import resurrection_note
from ci.runner_minutes import job_minutes

# Fixed test values, so the formula tests don't move when the real
# coefficients in afterlife/sci_coefficients.yaml are updated.
COEFFICIENTS = {
    "compute": {"min_watts_per_vcpu": 0.71, "max_watts_per_vcpu": 4.26, "assumed_utilisation": 0.5},
    "memory_kwh_per_gb_hour": 0.000392,
    "pue": 1.1,
    "grid": {"gco2e_per_kwh": 30},
    "embodied": {"gco2e_per_vcpu_hour": None},
    "runner": {"vcpus": 2, "memory_gb": 8},
}
SHIPPED = yaml.safe_load(Path("afterlife/sci_coefficients.yaml").read_text())
REQUIREMENTS_BEFORE = "fastapi\npyyaml\n# importer only\nrequests==2.31.0\n-r extra.txt\n"
REQUIREMENTS_AFTER = "fastapi\npyyaml\n"
AUDIT_BEFORE = {"dependencies": [
    {"name": "requests", "vulns": [{"id": "GHSA-9wx4-h78v-vm56"}, {"id": "GHSA-9hjg-9r4m-mvj7"}]},
    {"name": "fastapi", "vulns": []},
]}
AUDIT_AFTER = {"dependencies": [{"name": "fastapi", "vulns": []}]}
DESCRIPTION = (
    "Sunset.\n\nCensus-Issue: #3\n\n### Deprecation note\nUse `GET /v2/books`.\n\n### Verdict\n"
    '```afterlife-verdict\n{"feature": "books_v1", "verdict": "DEAD", "confidence": 0.9, '
    '"evidence": ["0 calls in 30 days"], "files": ["app/features/books_v1.py"]}\n```\n'
)


def complete(coefficients):
    c = copy.deepcopy(coefficients)
    c["embodied"]["gco2e_per_vcpu_hour"] = 1.0
    return c


def savings(coefficients=COEFFICIENTS, **overrides):
    kwargs = dict(
        feature="import_goodreads", mr_iid=7, sha="abcdef1234567890",
        numstat="0\t120\tapp/features/import_goodreads.py\n-\t-\tlogo.png\n",
        requirements_before=REQUIREMENTS_BEFORE, requirements_after=REQUIREMENTS_AFTER,
        audit_before=AUDIT_BEFORE, audit_after=AUDIT_AFTER,
        image_before=212_400_000, image_after=198_100_000,
        minutes_before=6.0, minutes_after=5.2, coefficients=coefficients, measured_by="https://ci/job/1",
    )
    kwargs.update(overrides)
    return build_savings(**kwargs)


def test_line_totals_skip_binaries():
    assert line_totals("3\t40\ta.py\n-\t-\tlogo.png\n0\t12\tb.py\n") == {"lines_added": 3, "lines_removed": 52}


def test_deps_removed():
    assert deps_removed(REQUIREMENTS_BEFORE, REQUIREMENTS_AFTER) == ["requests"]
    assert deps_removed("Foo_Bar==1\n", "foo-bar==2\n") == []


def test_cve_ids():
    assert len(cve_ids(AUDIT_BEFORE)) == 2
    assert cve_ids({}) == set()


def test_sci_refuses_missing_coefficients():
    assert sci(10, COEFFICIENTS) is None  # embodied is null in the fixture


def test_shipped_coefficients_are_complete_and_sourced():
    assert sci(10, SHIPPED) is not None
    for section in ("grid", "embodied"):
        assert SHIPPED[section]["source"].startswith("https://")
    assert SHIPPED["source_checked_on"] is not None


def test_sci_formula():
    result = sci(60, complete(COEFFICIENTS))  # one hour on a 2 vCPU / 8 GB runner
    watts = 0.71 + 0.5 * (4.26 - 0.71)
    energy = (watts * 2 / 1000 + 8 * 0.000392) * 1.1
    assert abs(result["E_kwh"] - round(energy, 6)) < 1e-9
    assert result["M_gco2e"] == 2.0
    assert abs(result["sci_gco2e"] - round(energy * 30 + 2.0, 4)) < 1e-9


def test_savings_are_measured_only():
    s = savings()
    assert s["lines_removed"] == 120
    assert s["deps_removed"] == ["requests"]
    assert (s["cves_before"], s["cves_after"]) == (2, 0)
    assert s["image_mb_saved"] == 14.3
    assert s["sci"] is None and "coefficients" in s["sci_missing"]


def test_savings_with_sci():
    s = savings(complete(COEFFICIENTS))
    assert s["sci"]["delta_gco2e"] > 0
    assert "sci_missing" not in s


def test_savings_with_missing_inputs():
    s = savings(image_before=None, minutes_before=None)
    assert s["image_mb_saved"] is None
    assert s["sci_missing"] == "runner minutes not available"


def test_obituary():
    text = render(savings(complete(COEFFICIENTS)), "https://gitlab.com/r/1")
    for expected in ("`import_goodreads`", "!7", "abcdef12", "requests", "2 → 0", "SCI per pipeline run", "ci/job/1"):
        assert expected in text
    assert "SCI | not computed" in render(savings(image_before=None))


def test_census_issue():
    assert census_issue("text\nCensus-Issue: #42\n") == 42
    assert census_issue("Census-Issue: 42") is None


def test_release_notes():
    assert deprecation_note(DESCRIPTION) == "Use `GET /v2/books`."
    text = render_release("books_v1", 12, DESCRIPTION)
    assert "Use `GET /v2/books`." in text and "- 0 calls in 30 days" in text and "!12" in text
    assert "`wrapped` has been removed." in render_release("wrapped", 1, "")


def test_resurrection_note_lists_knocks():
    text = resurrection_note("embed_widget", [{"at": "2026-10-26T12:03:00+00:00", "caller": "acme"}], False)
    assert "1 knock(s)" in text
    assert "| 2026-10-26T12:03:00 | acme |" in text
    assert "Mention" in text


def test_runner_minutes_compare_like_for_like():
    jobs = [
        {"name": "test", "status": "success", "duration": 90},
        {"name": "build-image", "status": "success", "duration": 30},
        {"name": "vulture", "status": "failed", "duration": 600},
        {"name": "deploy-canary", "status": "success", "duration": 999},
    ]
    assert job_minutes(jobs) == 2.0


def test_vulture_recheck():
    target = "app/features/import_goodreads.py:3: unused import 'requests' (90% confidence)\n"
    orphaned = "app/catalog.py:12: unused function 'goodreads_rows' (60% confidence)\n"
    assert new_unused(target, "") == {}
    assert new_unused(target, orphaned) == {"app/catalog.py": 1}


def test_cve_diff():
    assert cve_diff(AUDIT_BEFORE, AUDIT_AFTER)["cves_removed"] == sorted(cve_ids(AUDIT_BEFORE))
    assert cve_diff(AUDIT_AFTER, AUDIT_BEFORE)["cves_added"]
