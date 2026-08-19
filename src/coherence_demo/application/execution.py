from __future__ import annotations

import sqlite3
from typing import Any, Callable, Mapping
from uuid import uuid4

from coherence_demo.application.authorities import BranchAuthority, VersionAuthority
from coherence_demo.domain.models import Result, Run
from coherence_demo.persistence.sqlite import RunResultRepository


class ExecutionService:
    """Admit an exact Run and atomically publish its immutable Result."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.branch_authority = BranchAuthority(connection)
        self.version_authority = VersionAuthority(connection)
        self.repository = RunResultRepository(connection)

    def execute(
        self,
        branch_id: str,
        calculation: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    ) -> tuple[Run, Result]:
        version_id = self.branch_authority.current_version(branch_id)
        version = self.version_authority.get(version_id)
        run = Run(f"run_{uuid4().hex}", branch_id, version.version_id, "success")
        result = Result.create(run.run_id, calculation(version.content))
        with self.connection:
            self.repository.create_success(run, result)
        return run, result
