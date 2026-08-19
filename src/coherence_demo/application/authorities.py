from __future__ import annotations

import sqlite3
from typing import Any, Mapping
from uuid import uuid4

from coherence_demo.domain.models import Branch, BranchHeadEvent, Version
from coherence_demo.persistence.sqlite import (
    BranchHistoryRepository,
    BranchRepository,
    VersionRepository,
)


class VersionAuthority:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.repository = VersionRepository(connection)

    def create(self, version_id: str, content: Mapping[str, Any]) -> Version:
        version = Version.create(version_id, content)
        with self.connection:
            self.repository.create(version)
        return version

    def get(self, version_id: str) -> Version:
        version = self.repository.get(version_id)
        if version is None:
            raise KeyError(f"Unknown Version: {version_id}")
        return version


class BranchAuthority:
    """Sole application commit and decision boundary for Branch HEAD."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.repository = BranchRepository(connection)
        self.history_repository = BranchHistoryRepository(connection)

    def create(self, branch_id: str, head_version_id: str) -> Branch:
        with self.connection:
            return self.repository.create(
                branch_id,
                head_version_id,
                event_id=f"head_event_{uuid4().hex}",
            )

    def current_version(self, branch_id: str) -> str:
        branch = self.repository.get(branch_id)
        if branch is None:
            raise KeyError(f"Unknown Branch: {branch_id}")
        return branch.head_version_id

    def advance(
        self,
        branch_id: str,
        *,
        expected_version_id: str,
        new_version_id: str,
    ) -> Branch:
        with self.connection:
            return self.repository.advance_head(
                branch_id,
                expected_version_id=expected_version_id,
                new_version_id=new_version_id,
                event_id=f"head_event_{uuid4().hex}",
            )

    def history(self, branch_id: str) -> tuple[BranchHeadEvent, ...]:
        return self.history_repository.list_events(branch_id)
