from __future__ import annotations

import pytest

from coherence_demo.application.authorities import BranchAuthority, VersionAuthority
from coherence_demo.persistence.sqlite import Database


@pytest.fixture
def database() -> Database:
    value = Database()
    value.initialize()
    try:
        yield value
    finally:
        value.close()


@pytest.fixture
def model(database: Database) -> tuple[VersionAuthority, BranchAuthority]:
    versions = VersionAuthority(database.connection)
    branches = BranchAuthority(database.connection)
    versions.create("version-1", {"value": 10})
    versions.create("version-2", {"value": 20})
    branches.create("main", "version-1")
    return versions, branches
