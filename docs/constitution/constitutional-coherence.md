# Constitutional Coherence

Status: **CURRENT CONSTITUTION**

## Jurisdiction

This Constitution governs the admissibility of software change through the
coherence of ontology, semantics, authority, and development through time.

Exact product ontology and meaning belong to the scoped owners in
`docs/domain/`. The Authority Topology maps governed facts to implementation
authority without becoming a second semantic owner.

## Constitutional Coherence

A change is admissible only when it preserves ontological, semantic, and
authority coherence or changes them through explicit legitimate authority, and
when the development motion proves that preservation or lawful evolution.

### Ontological Coherence

Every governed concept has a coherent identity, boundary, lifecycle, and set of
relationships.

### Semantic Coherence

Every governed concept has one legitimate scoped meaning, and assertions made
about it are non-contradictory.

### Authority Coherence

Every governed fact has one lawful decision authority and one governed commit
boundary at the relevant lifecycle point and as-of. Alternative
representations may exist only with explicit subordinate standing.

### Developmental Coherence

Development preserves or explicitly and lawfully evolves ontology, semantics,
and authority through:

```text
Audit -> Plan -> Implement -> Verify
```

## Authority Normal Form

At a relevant as-of and lifecycle point, every governed fact has exactly one
canonical authority and one governed commit boundary through which that fact is
created or lawfully changed. Every other durable or product-material mutable
representation is explicitly classified and cannot exercise independent
decision rights.

**Duplication of representation is permissible. Duplication of authority is
not.**

A governed fact is a proposition whose identity, meaning, currentness,
history, execution binding, or mutation can affect product behavior.

Decision rights include the ability to:

- establish or mutate governed truth;
- select currentness;
- authorize a transition;
- bind execution;
- resolve conflict; or
- answer historical truth as canonical owner.

Authority Normal Form does not require one physical table or service. It does
not collapse Version, Branch, Run, and Result into one owner.

## Representation classifications

Exactly these classifications are admitted:

- `AUTHORITATIVE`: establishes the scoped fact; writes cross its governed
  commit boundary.
- `DERIVED`: reproducible from exact authoritative inputs; has no independent
  governed writer or decision right.
- `CACHE`: replaceable and identity-bound; stale, corrupt, or ambiguous state is
  discarded, rebuilt, refetched, or refused and never outvotes its source.
- `RECEIPT`: immutable evidence of an exact event or binding; authoritative only
  for what its receipt contract proves.
- `LEGACY_ONLY`: isolated old-data state with no successor-generation writes,
  fallback authority, new ordinary consumers, or successor decision rights.
- `EPHEMERAL`: safely losable interaction or computation state; never the sole
  carrier or decision authority for a governed fact.

Working, staged, draft, and candidate are lifecycle standings, not
representation classifications.

## Negative authority invariants

1. **Singular decision authority.** Two independently writable or
   independently deciding representations may not govern the same fact.
2. **Classified representation closure.** Every durable or product-material
   mutable carrier of a governed fact must have an admitted role and denied
   decision rights.
3. **Exclusive governed commit boundary.** Every governed mutation crosses the
   owning authority's declared boundary.
4. **Temporal and binding closure.** Historical truth and exact execution
   bindings may not be reconstructed from mutable present state.
5. **Owner-resolved consumption.** Consumers receive the owner's decision; they
   do not reconcile multiple resources to determine governed truth.
6. **Legacy isolation.** Legacy-only state receives no successor writers or
   successor decision rights and cannot act as fallback authority.
7. **Constitutional failure closure.** Missing, contradictory, or unclassified
   authority fails closed rather than invoking recency, precedence, fallback,
   or best-effort reconstruction.

## Constitutional Delta

Before implementation, the Plan records the legitimately authorized change to:

- `delta O`: concepts, identities, boundaries, and relationships;
- `delta S`: meaning and contracts; and
- `delta A`: owners, carriers, writers, decision rights, historical sources,
  and client responsibility.

An implementation mismatch returns the motion to Audit. The implementing agent
cannot authorize the mismatch by revising its forecast after the fact.
