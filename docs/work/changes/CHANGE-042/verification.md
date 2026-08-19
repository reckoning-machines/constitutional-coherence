# CHANGE-042 Verification — Branch summary projection

Behavioral tests establish that the projection reports Branch Authority's
current Version and changes only after the canonical Branch transition.

Constitutional verification establishes:

- `NO ONTOLOGY CHANGE`;
- `NO SEMANTIC CHANGE`;
- canonical authority and commit boundary unchanged;
- one `DERIVED` representation added;
- no durable carrier added;
- no writer or decision right added;
- no historical source changed; and
- no client-owned currentness introduced.

The measured state is recorded separately in
`actual-constitutional-delta.yaml`. Validation compares it structurally with
the admitted `constitutional-delta.yaml`; the actual delta cannot redefine its
authorization.
