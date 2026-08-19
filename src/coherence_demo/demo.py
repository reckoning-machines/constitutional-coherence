from __future__ import annotations

import json

from coherence_demo.api.projections import branch_summary, result_projection, run_receipt
from coherence_demo.application.authorities import BranchAuthority, VersionAuthority
from coherence_demo.application.execution import ExecutionService
from coherence_demo.persistence.sqlite import Database, RunResultRepository
from coherence_demo.web.state import BranchViewState


def main() -> None:
    database = Database()
    database.initialize()
    try:
        versions = VersionAuthority(database.connection)
        branches = BranchAuthority(database.connection)
        versions.create("version-1", {"revenue": 100, "multiple": 8})
        versions.create("version-2", {"revenue": 120, "multiple": 9})
        branches.create("main", "version-1")
        branches.advance(
            "main", expected_version_id="version-1", new_version_id="version-2"
        )

        run, _result = ExecutionService(database.connection).execute(
            "main", lambda model: {"value": model["revenue"] * model["multiple"]}
        )
        repository = RunResultRepository(database.connection)
        projection = branch_summary(branches, "main")
        browser = BranchViewState()
        browser.observe(projection)

        print(
            json.dumps(
                {
                    "branch": projection,
                    "browser_observation": {
                        "branch_id": browser.branch_id,
                        "head_version_id": browser.observed_head_version_id,
                    },
                    "run_receipt": run_receipt(repository, run.run_id),
                    "result": result_projection(repository, run.run_id),
                },
                indent=2,
                sort_keys=True,
            )
        )
    finally:
        database.close()


if __name__ == "__main__":
    main()
