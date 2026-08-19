"""Executable limitations: pathologies this harness does not detect.

Every case here introduces a genuine constitutional violation and then asserts
that validation reports **nothing**. These tests pass because the harness is
blind, and each fixture records exactly why.

They exist because a README bullet saying "discovery is name-based" is easy to
read past, and easy to leave behind when the code moves on. A test that fails
the moment the blind spot closes is not.

**If one of these fails, the harness got better.** Confirm the new error is the
right one, move the fixture into `adversarial/` with its expected error, and
delete the corresponding caveat from the README. Do not weaken the fixture to
make it pass again.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from constitutional.validate import validate_repository


CASES = sorted((Path(__file__).parent / "blindspots").glob("*.yaml"))


@pytest.mark.parametrize("case_path", CASES, ids=lambda path: path.stem)
def test_known_blind_spot_is_still_blind(
    plain_repository: Path,
    apply_mutation,
    case_path: Path,
) -> None:
    case = yaml.safe_load(case_path.read_text(encoding="utf-8"))
    for mutation in case["mutations"]:
        apply_mutation(plain_repository, mutation)

    errors = validate_repository(plain_repository)

    assert errors == [], (
        f"The harness now detects '{case['name']}'. This is good news. "
        f"Promote {case_path.name} into adversarial/ with its expected error "
        "and remove the matching caveat from the README, rather than relaxing "
        f"this fixture.\nDetected: {errors}"
    )


def test_every_blind_spot_documents_itself() -> None:
    """A limitation nobody explained is not documentation."""

    assert CASES, "blind-spot fixtures are missing"
    for case_path in CASES:
        case = yaml.safe_load(case_path.read_text(encoding="utf-8"))
        for field in ("name", "pathology", "why_it_is_missed", "caught_by"):
            assert case.get(field), f"{case_path.name} is missing '{field}'"


def test_paperwork_alone_does_not_make_a_blind_spot_lawful(
    baselined_repository: Path,
    apply_mutation,
) -> None:
    """The gate forces review; it cannot supply the sight the checker lacks.

    A change the harness cannot see still needs an authorized change record, so
    it cannot land silently. But a truthful-as-far-as-the-author-knows delta
    declaring NO_CHANGE passes, because the measurement is just as blind as the
    discovery it is built on. The gate closes the loop. It does not widen the
    aperture.
    """

    case = yaml.safe_load(
        (Path(__file__).parent / "blindspots" / "renamed_durable_carrier.yaml")
        .read_text(encoding="utf-8")
    )
    for mutation in case["mutations"]:
        apply_mutation(baselined_repository, mutation)

    ungated = validate_repository(baselined_repository, require_gate=True)
    assert any(
        "governed change without a Constitutional Delta" in error for error in ungated
    ), ungated

    delta = """change_id: CHANGE-906
status: OPEN
authorized_by: docs/decisions/DEC-014-version-currentness.md
touched_facts: []
ontology:
  status: NO_CHANGE
semantics:
  status: NO_CHANGE
authority:
  status: NO_CHANGE
  canonical_authority_changed: false
  commit_boundary_changed: false
  writers_added: []
  decision_rights_added: []
  historical_sources_changed: false
  client_responsibility_changed: false
  representations_added: []
duplicate_independent_writers: false
legacy_successor_writes: false
browser_owned_truth: false
mutable_present_historical_dependency: false
"""
    for name in ("constitutional-delta.yaml", "actual-constitutional-delta.yaml"):
        apply_mutation(
            baselined_repository,
            {
                "operation": "write",
                "path": f"docs/work/changes/CHANGE-906/{name}",
                "content": delta,
            },
        )

    assert validate_repository(baselined_repository, require_gate=True) == []
