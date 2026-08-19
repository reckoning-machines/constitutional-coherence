from __future__ import annotations

from coherence_demo.domain.models import BranchHeadEvent
from coherence_demo.persistence.sqlite import BranchHistoryRepository


def branch_head_at_sequence(
    repository: BranchHistoryRepository,
    branch_id: str,
    sequence: int,
) -> str:
    """Resolve historical HEAD exclusively from immutable transition receipts."""

    matches: list[BranchHeadEvent] = [
        event for event in repository.list_events(branch_id) if event.sequence == sequence
    ]
    if len(matches) != 1:
        raise KeyError("Exact historical Branch HEAD is unavailable")
    return matches[0].new_version_id
