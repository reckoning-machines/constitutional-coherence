from __future__ import annotations

import sqlite3

import pytest

from coherence_demo.api.projections import result_projection, run_receipt
from coherence_demo.application.authorities import BranchAuthority, VersionAuthority
from coherence_demo.application.execution import ExecutionService
from coherence_demo.persistence.sqlite import Database, RunResultRepository


def test_run_binds_exact_version_and_result_is_exact_run_outcome(
    database: Database,
    model: tuple[VersionAuthority, BranchAuthority],
) -> None:
    _versions, branches = model
    service = ExecutionService(database.connection)
    run, result = service.execute("main", lambda content: {"answer": content["value"] * 2})
    repository = RunResultRepository(database.connection)

    assert run.version_id == "version-1"
    assert result.run_id == run.run_id
    assert run_receipt(repository, run.run_id)["version_id"] == "version-1"
    assert result_projection(repository, run.run_id)["payload"] == {"answer": 20}

    branches.advance(
        "main", expected_version_id="version-1", new_version_id="version-2"
    )
    assert branches.current_version("main") == "version-2"
    assert run_receipt(repository, run.run_id)["version_id"] == "version-1"


def test_result_and_run_are_physically_immutable(
    database: Database,
    model: tuple[VersionAuthority, BranchAuthority],
) -> None:
    service = ExecutionService(database.connection)
    run, _result = service.execute("main", lambda content: {"answer": content["value"]})

    with pytest.raises(sqlite3.IntegrityError, match="immutable"):
        database.connection.execute(
            "UPDATE results SET payload_json = '{}' WHERE run_id = ?", (run.run_id,)
        )
    with pytest.raises(sqlite3.IntegrityError, match="immutable"):
        database.connection.execute(
            "UPDATE runs SET version_id = 'version-2' WHERE run_id = ?", (run.run_id,)
        )
