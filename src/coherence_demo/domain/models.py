from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Mapping


def _required(value: str, field: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{field} is required")
    return normalized


def canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(dict(value), sort_keys=True, separators=(",", ":"))


def content_hash(value: Mapping[str, Any]) -> str:
    return sha256(canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class Version:
    version_id: str
    content: Mapping[str, Any]
    content_hash: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "version_id", _required(self.version_id, "version_id"))
        expected = content_hash(self.content)
        if self.content_hash != expected:
            raise ValueError("Version content hash mismatch")

    @classmethod
    def create(cls, version_id: str, content: Mapping[str, Any]) -> "Version":
        return cls(version_id, dict(content), content_hash(content))


@dataclass(frozen=True, slots=True)
class Branch:
    branch_id: str
    head_version_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "branch_id", _required(self.branch_id, "branch_id"))
        object.__setattr__(
            self,
            "head_version_id",
            _required(self.head_version_id, "head_version_id"),
        )


@dataclass(frozen=True, slots=True)
class BranchHeadEvent:
    event_id: str
    branch_id: str
    previous_version_id: str | None
    new_version_id: str
    sequence: int


@dataclass(frozen=True, slots=True)
class Run:
    run_id: str
    branch_id: str
    version_id: str
    status: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required(self.run_id, "run_id"))
        object.__setattr__(self, "branch_id", _required(self.branch_id, "branch_id"))
        object.__setattr__(self, "version_id", _required(self.version_id, "version_id"))
        if self.status not in {"success", "failed"}:
            raise ValueError("Run status must be success or failed")


@dataclass(frozen=True, slots=True)
class Result:
    run_id: str
    payload: Mapping[str, Any]
    content_hash: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required(self.run_id, "run_id"))
        expected = content_hash(self.payload)
        if self.content_hash != expected:
            raise ValueError("Result content hash mismatch")

    @classmethod
    def create(cls, run_id: str, payload: Mapping[str, Any]) -> "Result":
        return cls(run_id, dict(payload), content_hash(payload))
