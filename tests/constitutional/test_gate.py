"""Witnesses for the gate: which changes the development motion refuses to admit.

The standing tests in `test_authority_topology.py` ask whether the repository is
coherent right now. These ask a different question: was *this change* authorized.
That question needs a baseline, so every case builds a real git repository,
commits it, then mutates the working tree.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from constitutional.measure import resolve_base_ref
from constitutional.validate import validate_repository


CASES = sorted((Path(__file__).parent / "gate").glob("*.yaml"))


@pytest.mark.parametrize("case_path", CASES, ids=lambda path: path.stem)
def test_gate_case(
    baselined_repository: Path, apply_mutation, case_path: Path
) -> None:
    case = yaml.safe_load(case_path.read_text(encoding="utf-8"))
    repository = baselined_repository
    for mutation in case["mutations"]:
        apply_mutation(repository, mutation)

    errors = validate_repository(repository, require_gate=True)

    if case["expect"] == "pass":
        assert errors == [], errors
    else:
        assert any(case["expected_error"] in error for error in errors), errors


def test_gate_is_skipped_without_a_baseline(plain_repository: Path) -> None:
    """Outside git there is no baseline, so the gate reports its own absence."""

    repository = plain_repository

    assert resolve_base_ref(repository) is None
    assert validate_repository(repository) == []
    assert any(
        "constitutional gate unavailable" in error
        for error in validate_repository(repository, require_gate=True)
    )


def test_measured_delta_is_generated_not_declared(
    baselined_repository: Path,
) -> None:
    """Verify reads the repository. It never reads the Plan it is checking."""

    repository = baselined_repository
    base = resolve_base_ref(repository)
    assert base is not None

    from constitutional.discover import discover_repository, load_yaml, TOPOLOGY_PATH
    from constitutional.measure import measure_delta

    topology = load_yaml(repository / TOPOLOGY_PATH)
    rules = load_yaml(repository / "constitutional/dependency_rules.yaml")
    observed = discover_repository(repository, topology)

    unchanged = measure_delta(
        repository, base, topology=topology, rules=rules, observed=observed
    )
    assert unchanged["ontology"]["status"] == "NO_CHANGE"
    assert unchanged["authority"]["status"] == "NO_CHANGE"

    (repository / "docs/domain/run.md").write_text(
        "# Run Semantics\n\nA Run is now something else entirely.\n", encoding="utf-8"
    )
    changed = measure_delta(
        repository, base, topology=topology, rules=rules, observed=observed
    )
    assert changed["semantics"]["status"] == "CHANGE"
