# Repository Routing

This repository demonstrates Constitutional Coherence.

Before changing implementation:

1. read `docs/constitution/constitutional-coherence.md`;
2. route product meaning through the exact file in `docs/domain/`;
3. inspect `docs/constitution/authority-topology.yaml` for every governed fact
   touched;
4. perform a repository-wide carrier and writer sweep;
5. open one Constitutional Delta under `docs/work/changes/`; and
6. follow `Audit -> Plan -> Implement -> Verify`.

A Plan records authority supplied by a legitimate decision. It does not create
authority. Stop if implementation reveals an undeclared concept, meaning,
carrier, writer, decision right, historical source, or client responsibility.

## What the gate will refuse

Changing anything under `src/coherence_demo/`, `docs/constitution/`, or
`docs/domain/` requires an open change record. The gate refuses a change that:

- touches those paths with no `constitutional-delta.yaml` selected by the diff;
- cites a decision record that the same change created or edited;
- amends `docs/constitution/` while declaring `authority: NO_CHANGE`;
- edits `docs/domain/` while declaring `semantics: NO_CHANGE`;
- attaches new work to a change record marked `status: COMPLETED`; or
- declares a delta that disagrees with the delta measured from the repository.

You cannot satisfy the last one by editing your forecast. The measurement comes
from `git`, not from your Plan.

## Verify

```bash
python -m constitutional.measure --root . --record   # write the measured delta
python -m constitutional.validate --root .           # compare it to the Plan
pytest
```

Tests cannot legalize an unauthorized constitutional change.
