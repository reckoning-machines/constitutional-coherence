# CHANGE-042 Verification: Branch summary projection

Status: **COMPLETED**. This is a historical record, retained as a worked
example of the standing development motion. It is not re-measured.

Behavioral tests establish that the projection reports Branch Authority's
current Version and changes only after the canonical Branch transition.

Constitutional verification established:

- `NO ONTOLOGY CHANGE`;
- `NO SEMANTIC CHANGE`;
- canonical authority and commit boundary unchanged;
- one `DERIVED` representation added;
- no durable carrier added;
- no writer or decision right added;
- no historical source changed; and
- no client-owned currentness introduced.

## Why this record cannot be re-verified

Measuring an actual Constitutional Delta requires the repository state *before*
the change. That state is a commit. This change was merged before the measuring
harness existed, so its baseline is no longer distinguishable from its result,
and re-running the measurement against `HEAD` would only prove that nothing has
changed since.

The record is therefore marked `status: COMPLETED` in
`constitutional-delta.yaml`, and the gate refuses to let new governed work
attach itself to it. Live verification happens on open changes, where a
baseline exists:

```bash
python -m constitutional.measure --root . --record
python -m constitutional.validate --root .
```

`actual-constitutional-delta.yaml` in an open change is **generated** by that
first command from repository observation. It is not written by hand, and it is
not derived from `constitutional-delta.yaml`. Validation then compares the two.
An agent that revises its forecast to match its implementation changes only one
side of that comparison.
