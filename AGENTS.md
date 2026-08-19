# Repository Routing

This repository demonstrates Constitutional Coherence.

Before changing implementation:

1. read `docs/constitution/constitutional-coherence.md`;
2. route product meaning through the exact file in `docs/domain/`;
3. inspect `docs/constitution/authority-topology.yaml` for every governed fact
   touched;
4. perform a repository-wide carrier and writer sweep;
5. write or update one Constitutional Delta under `docs/work/changes/`; and
6. follow `Audit -> Plan -> Implement -> Verify`.

A Plan records authority supplied by a legitimate decision. It does not create
authority. Stop if implementation reveals an undeclared concept, meaning,
carrier, writer, decision right, historical source, or client responsibility.

Run these checks before completion:

```bash
python -m constitutional.validate --root .
pytest
```

Tests cannot legalize an unauthorized constitutional change.
