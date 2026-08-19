# Constitutional Coherence Reference Repository

This repository is a runnable reference implementation of constitutional
coherence for agentic software development.

The application is intentionally small: Versions exist, a Branch selects its
current Version, Runs bind exact Versions, and immutable Results bind exact
Runs. The point is not the application. The point is that its ontology,
semantics, decision rights, mutation boundaries, and permitted duplicate
representations are explicit and checked.

## The controlled state

The software constitution governs three dimensions:

- **Ontology:** what exists and what gives each concept identity.
- **Semantics:** what those concepts mean.
- **Authority:** which representation may establish or change each governed
  fact.

Development preserves or lawfully evolves that state through:

```text
Audit -> Plan -> Implement -> Verify
```

Every meaningful change records a Constitutional Delta: `delta O`, `delta S`,
and `delta A`. The Plan records legitimate authorization; it does not create
authority for itself.

## Repository tour

```text
docs/constitution/        compact standing constitution and authority topology
docs/domain/              scoped semantic owners
docs/work/changes/        one example Audit/Plan/Delta/Verify record
src/coherence_demo/       small Branch/Version/Run/Result application
constitutional/           repository discovery and deterministic validation
tests/constitutional/     clean and adversarial constitutional witnesses
tests/product/            ordinary behavioral tests
```

The machine-readable Authority Topology is
[`docs/constitution/authority-topology.yaml`](docs/constitution/authority-topology.yaml).
It maps exact governed facts to their semantic owners, canonical carriers,
commit boundaries, writers, historical carriers, and lawful alternatives. It
does not redefine product meaning.

## Run it

Python 3.11 or newer is required.

```bash
python -m pip install -e '.[dev]'
python -m constitutional.discover --root .
python -m constitutional.validate --root .
pytest
constitutional-coherence-demo
```

Discovery writes `build/constitutional/observed-authority.json`. That file is
evidence, not authority. Validation compares the observed repository with the
standing topology, the admitted sample Constitutional Delta, and the separately
recorded actual delta from Verify.

## Try the failure mode

The adversarial tests inject shapes such as:

- a second durable `recovered_head_version_id`;
- an unauthorized writer to `branches.head_version_id`;
- browser code importing persistence to reconcile currentness; and
- historical code consulting the mutable present Branch row.

They must fail even when the added code is locally plausible. Lawful API
projections, immutable receipts, and ephemeral client selection continue to
pass.

## What this demonstrates

This is not a universal semantic inference engine. Repository discovery cannot
deduce product meaning from names alone. Instead, the example combines:

1. scoped human semantic authority;
2. a fact-level topology of decision rights;
3. owner-shaped code boundaries;
4. independent inspection of schemas, writers, imports, and change records;
5. negative architectural witnesses; and
6. fail-closed treatment of unexplained durable carriers.

The useful test is whether an ordinary patch can introduce a second authority
without the development system noticing. In this repository, the supplied
adversarial examples cannot.
