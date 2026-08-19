from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from constitutional.discover import TOPOLOGY_PATH, discover_repository, load_yaml
from constitutional.validate import (
    CLASSIFICATIONS,
    DEFAULT_ACTUAL_DELTA,
    DEFAULT_DELTA,
    validate_actual_delta,
    validate_delta,
    validate_repository,
)


ROOT = Path(__file__).resolve().parents[2]


def test_repository_is_constitutionally_coherent() -> None:
    assert validate_repository(ROOT) == []


def test_discovery_observes_every_governed_identifier_carrier() -> None:
    topology = load_yaml(ROOT / TOPOLOGY_PATH)
    observed = discover_repository(ROOT, topology)

    assert {carrier.locator for carrier in observed.durable_carriers} == {
        "sqlite.branch_head_events.new_version_id",
        "sqlite.branch_head_events.previous_version_id",
        "sqlite.branches.head_version_id",
        "sqlite.results.run_id",
        "sqlite.runs.run_id",
        "sqlite.runs.version_id",
        "sqlite.versions.version_id",
    }


def test_constitution_admits_exactly_six_representation_classes() -> None:
    topology = load_yaml(ROOT / TOPOLOGY_PATH)
    assert tuple(topology["classifications"]) == CLASSIFICATIONS


def test_delta_cannot_claim_an_unregistered_representation() -> None:
    topology = load_yaml(ROOT / TOPOLOGY_PATH)
    delta = deepcopy(load_yaml(ROOT / DEFAULT_DELTA))
    delta["authority"]["representations_added"][0]["id"] = "api.unknown.current"

    errors = validate_delta(ROOT, topology, delta)

    assert any("absent from topology" in error for error in errors)


def test_new_governed_fact_fails_closed_without_topology_entry() -> None:
    topology = load_yaml(ROOT / TOPOLOGY_PATH)
    delta = deepcopy(load_yaml(ROOT / DEFAULT_DELTA))
    delta["touched_facts"].append("branch.approval_status")

    errors = validate_delta(ROOT, topology, delta)

    assert any("unknown fact: branch.approval_status" in error for error in errors)


def test_actual_delta_must_match_authorized_delta() -> None:
    authorized = load_yaml(ROOT / DEFAULT_DELTA)
    actual = deepcopy(load_yaml(ROOT / DEFAULT_ACTUAL_DELTA))
    actual["authority"]["writers_added"] = ["recovery.restore_head"]

    errors = validate_actual_delta(authorized, actual)

    assert any("does not match authorization: authority" in error for error in errors)
