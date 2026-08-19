from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(slots=True)
class BranchViewState:
    """Safely losable observation of one backend-owned Branch projection."""

    branch_id: str | None = None
    observed_head_version_id: str | None = None

    def observe(self, projection: Mapping[str, Any]) -> None:
        if projection.get("authority") != "BranchAuthority":
            raise ValueError("Branch projection lacks backend authority evidence")
        self.branch_id = str(projection["branch_id"])
        self.observed_head_version_id = str(projection["head_version_id"])

    def clear(self) -> None:
        self.branch_id = None
        self.observed_head_version_id = None
