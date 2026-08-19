from __future__ import annotations

import json
from pathlib import Path
import sqlite3
from typing import Iterator

from coherence_demo.domain.models import Branch, BranchHeadEvent, Result, Run, Version


class Database:
    def __init__(self, path: str | Path = ":memory:") -> None:
        self.connection = sqlite3.connect(str(path))
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")

    def initialize(self) -> None:
        schema = Path(__file__).resolve().parents[1] / "schema.sql"
        self.connection.executescript(schema.read_text(encoding="utf-8"))

    def close(self) -> None:
        self.connection.close()


class VersionRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def create(self, version: Version) -> None:
        self.connection.execute(
            "INSERT INTO versions (version_id, content_json, content_hash) VALUES (?, ?, ?)",
            (version.version_id, json.dumps(dict(version.content)), version.content_hash),
        )

    def get(self, version_id: str) -> Version | None:
        row = self.connection.execute(
            "SELECT version_id, content_json, content_hash FROM versions WHERE version_id = ?",
            (version_id,),
        ).fetchone()
        if row is None:
            return None
        return Version(row["version_id"], json.loads(row["content_json"]), row["content_hash"])


class BranchRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def create(self, branch_id: str, head_version_id: str, event_id: str) -> Branch:
        self.connection.execute(
            "INSERT INTO branches (branch_id, head_version_id) VALUES (?, ?)",
            (branch_id, head_version_id),
        )
        self.connection.execute(
            """INSERT INTO branch_head_events
               (event_id, branch_id, previous_version_id, new_version_id, sequence)
               VALUES (?, ?, NULL, ?, 1)""",
            (event_id, branch_id, head_version_id),
        )
        return Branch(branch_id, head_version_id)

    def get(self, branch_id: str) -> Branch | None:
        row = self.connection.execute(
            "SELECT branch_id, head_version_id FROM branches WHERE branch_id = ?",
            (branch_id,),
        ).fetchone()
        return None if row is None else Branch(row["branch_id"], row["head_version_id"])

    def advance_head(
        self,
        branch_id: str,
        *,
        expected_version_id: str,
        new_version_id: str,
        event_id: str,
    ) -> Branch:
        changed = self.connection.execute(
            """UPDATE branches SET head_version_id = ?
               WHERE branch_id = ? AND head_version_id = ?""",
            (new_version_id, branch_id, expected_version_id),
        ).rowcount
        if changed != 1:
            raise ValueError("Branch HEAD conflict")
        sequence = self.connection.execute(
            "SELECT COALESCE(MAX(sequence), 0) + 1 FROM branch_head_events WHERE branch_id = ?",
            (branch_id,),
        ).fetchone()[0]
        self.connection.execute(
            """INSERT INTO branch_head_events
               (event_id, branch_id, previous_version_id, new_version_id, sequence)
               VALUES (?, ?, ?, ?, ?)""",
            (event_id, branch_id, expected_version_id, new_version_id, sequence),
        )
        return Branch(branch_id, new_version_id)


class BranchHistoryRepository:
    """Read-only historical carrier over immutable Branch-head receipts."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def list_events(self, branch_id: str) -> tuple[BranchHeadEvent, ...]:
        rows: Iterator[sqlite3.Row] = self.connection.execute(
            """SELECT event_id, branch_id, previous_version_id, new_version_id, sequence
               FROM branch_head_events WHERE branch_id = ? ORDER BY sequence""",
            (branch_id,),
        )
        return tuple(
            BranchHeadEvent(
                row["event_id"],
                row["branch_id"],
                row["previous_version_id"],
                row["new_version_id"],
                row["sequence"],
            )
            for row in rows
        )


class RunResultRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def create_success(self, run: Run, result: Result) -> None:
        if run.status != "success" or run.run_id != result.run_id:
            raise ValueError("Successful Run and Result identity must agree")
        self.connection.execute(
            "INSERT INTO runs (run_id, branch_id, version_id, status) VALUES (?, ?, ?, ?)",
            (run.run_id, run.branch_id, run.version_id, run.status),
        )
        self.connection.execute(
            "INSERT INTO results (run_id, payload_json, content_hash) VALUES (?, ?, ?)",
            (result.run_id, json.dumps(dict(result.payload)), result.content_hash),
        )

    def get_run(self, run_id: str) -> Run | None:
        row = self.connection.execute(
            "SELECT run_id, branch_id, version_id, status FROM runs WHERE run_id = ?",
            (run_id,),
        ).fetchone()
        if row is None:
            return None
        return Run(row["run_id"], row["branch_id"], row["version_id"], row["status"])

    def get_result(self, run_id: str) -> Result | None:
        row = self.connection.execute(
            "SELECT run_id, payload_json, content_hash FROM results WHERE run_id = ?",
            (run_id,),
        ).fetchone()
        if row is None:
            return None
        return Result(row["run_id"], json.loads(row["payload_json"]), row["content_hash"])
