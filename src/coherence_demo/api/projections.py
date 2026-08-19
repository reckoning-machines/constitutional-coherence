from __future__ import annotations

from typing import Any

from coherence_demo.application.authorities import BranchAuthority
from coherence_demo.persistence.sqlite import RunResultRepository


def branch_summary(authority: BranchAuthority, branch_id: str) -> dict[str, Any]:
    return {
        "branch_id": branch_id,
        "head_version_id": authority.current_version(branch_id),
        "authority": "BranchAuthority",
    }


def run_receipt(repository: RunResultRepository, run_id: str) -> dict[str, Any]:
    run = repository.get_run(run_id)
    if run is None:
        raise KeyError(f"Unknown Run: {run_id}")
    return {
        "run_id": run.run_id,
        "branch_id": run.branch_id,
        "version_id": run.version_id,
        "status": run.status,
    }


def result_projection(
    repository: RunResultRepository,
    run_id: str,
) -> dict[str, Any]:
    result = repository.get_result(run_id)
    if result is None:
        raise KeyError(f"No Result for Run: {run_id}")
    return {
        "results_ref": result.run_id,
        "payload": dict(result.payload),
        "content_hash": result.content_hash,
    }
