"""
Structural validation tests for .github/workflows/ci.yml.

Tests:
- actionlint lint check (skipped if actionlint not installed)
- YAML structural invariants
- Action version pinning

Requirements: 1.1, 1.3, 1.4, 6.1
"""

import os
import re
import subprocess

import pytest
import yaml

# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WORKFLOW_PATH = os.path.join(PROJECT_ROOT, ".github", "workflows", "ci.yml")


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def workflow() -> dict:
    """
    Load and parse the workflow YAML once for all tests in the module.

    PyYAML's safe_load maps the bare YAML keyword ``on`` to the Python boolean
    ``True``.  We normalise the parsed dict so that the key ``"on"`` is always
    present, matching the YAML source and making tests readable.

    The file is opened with utf-8-sig so that an optional BOM is transparently
    stripped.
    """
    with open(WORKFLOW_PATH, encoding="utf-8-sig") as fh:
        data = yaml.safe_load(fh)

    # PyYAML converts 'on:' → True; normalise to the string "on" for clarity
    if True in data and "on" not in data:
        data["on"] = data.pop(True)

    return data


# ---------------------------------------------------------------------------
# Test: actionlint
# ---------------------------------------------------------------------------


def test_actionlint():
    """
    Run actionlint against the workflow file.
    If actionlint is not installed the test is skipped rather than failed.
    """
    try:
        result = subprocess.run(
            ["actionlint", WORKFLOW_PATH],
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        pytest.skip("actionlint is not installed — skipping lint check")

    assert result.returncode == 0, (
        f"actionlint reported errors:\n{result.stdout}\n{result.stderr}"
    )


# ---------------------------------------------------------------------------
# Test: YAML structural invariants
# ---------------------------------------------------------------------------


def test_on_push_branches_is_main_only(workflow):
    """on.push.branches must contain exactly ['main']."""
    branches = workflow["on"]["push"]["branches"]
    assert branches == ["main"], (
        f"Expected on.push.branches == ['main'], got {branches!r}"
    )


def test_workflow_dispatch_present(workflow):
    """workflow_dispatch trigger must be present under 'on'."""
    assert "workflow_dispatch" in workflow["on"], (
        "'workflow_dispatch' is missing from the 'on' triggers"
    )


def test_concurrency_cancel_in_progress(workflow):
    """concurrency.cancel-in-progress must be True."""
    cancel = workflow["concurrency"]["cancel-in-progress"]
    assert cancel is True, (
        f"Expected concurrency.cancel-in-progress == True, got {cancel!r}"
    )


def test_permissions_contents_write(workflow):
    """permissions.contents must be 'write'."""
    contents_perm = workflow["permissions"]["contents"]
    assert contents_perm == "write", (
        f"Expected permissions.contents == 'write', got {contents_perm!r}"
    )


def test_build_and_push_fail_fast_false(workflow):
    """jobs.build-and-push.strategy.fail-fast must be False."""
    fail_fast = workflow["jobs"]["build-and-push"]["strategy"]["fail-fast"]
    assert fail_fast is False, (
        f"Expected jobs.build-and-push.strategy.fail-fast == False, got {fail_fast!r}"
    )


def test_pipeline_summary_if_always(workflow):
    """jobs.pipeline-summary.if must contain 'always()'."""
    if_condition = workflow["jobs"]["pipeline-summary"]["if"]
    assert "always()" in str(if_condition), (
        f"Expected jobs.pipeline-summary.if to contain 'always()', got {if_condition!r}"
    )


# ---------------------------------------------------------------------------
# Test: action versions pinned
# ---------------------------------------------------------------------------

# Patterns that indicate an UNpinned version reference
_UNPINNED_PATTERNS = re.compile(r"@(main|master|latest)$", re.IGNORECASE)

# A valid pinned reference contains '@' followed by a version tag or SHA,
# e.g. '@v4', '@v2.1.0', '@abc1234' (SHA), but NOT '@main'/'@master'/'@latest'
_PINNED_PATTERN = re.compile(r"@.+")


def _collect_steps(workflow: dict) -> list[tuple[str, dict]]:
    """Return a flat list of (job_name, step) tuples for all jobs."""
    steps = []
    for job_name, job in (workflow.get("jobs") or {}).items():
        for step in job.get("steps") or []:
            steps.append((job_name, step))
    return steps


def test_action_versions_pinned(workflow):
    """
    Every step that uses an action (has a 'uses:' key) must be pinned to a
    specific version tag or commit SHA — not '@main', '@master', or '@latest'.
    """
    violations = []
    for job_name, step in _collect_steps(workflow):
        uses = step.get("uses")
        if uses is None:
            continue

        # Must contain '@' at all
        if "@" not in uses:
            violations.append(
                f"  [{job_name}] '{uses}' has no version pin (missing '@')"
            )
            continue

        # Must not point to a floating branch/tag
        if _UNPINNED_PATTERNS.search(uses):
            violations.append(
                f"  [{job_name}] '{uses}' is pinned to a floating ref "
                f"(@main/@master/@latest)"
            )

    assert not violations, (
        "The following action references are not properly pinned:\n"
        + "\n".join(violations)
    )
