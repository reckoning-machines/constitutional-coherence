from __future__ import annotations

import sqlite3

import pytest

from coherence_demo.api.projections import branch_summary
from coherence_demo.application.authorities import BranchAuthority, VersionAuthority
from coherence_demo.application.history import branch_head_at_sequence
from coherence_demo.persistence.sqlite import BranchHistoryRepository, Database
from coherence_demo.web.state import BranchViewState


def test_branch_head_advances_only_through_expected_head_cas(
    model: tuple[VersionAuthority, BranchAuthority],
) -> None:
    _versions, branches = model

    updated = branches.advance(
        "main", expected_version_id="version-1", new_version_id="version-2"
    )

    assert updated.head_version_id == "version-2"
    assert branches.current_version("main") == "version-2"
    with pytest.raises(ValueError, match="Branch HEAD conflict"):
        branches.advance(
            "main", expected_version_id="version-1", new_version_id="version-2"
        )


def test_historical_head_comes_from_immutable_receipts(
    database: Database,
    model: tuple[VersionAuthority, BranchAuthority],
) -> None:
    _versions, branches = model
    branches.advance(
        "main", expected_version_id="version-1", new_version_id="version-2"
    )
    history = BranchHistoryRepository(database.connection)

    assert branch_head_at_sequence(history, "main", 1) == "version-1"
    assert branch_head_at_sequence(history, "main", 2) == "version-2"
    with pytest.raises(sqlite3.IntegrityError, match="immutable"):
        database.connection.execute(
            "UPDATE branch_head_events SET new_version_id = ? WHERE sequence = 1",
            ("version-2",),
        )


def test_api_and_browser_are_subordinate_representations(
    model: tuple[VersionAuthority, BranchAuthority],
) -> None:
    _versions, branches = model
    view = BranchViewState()
    view.observe(branch_summary(branches, "main"))

    assert view.observed_head_version_id == "version-1"
    view.observed_head_version_id = "version-2"

    assert branches.current_version("main") == "version-1"
