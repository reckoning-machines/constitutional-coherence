# CHANGE-043 Verification: Refuse unread listed schema files

Status: **COMPLETED**.

The development motion preserved the before/after evidence:

- before implementation, `unread_alter_only_schema` passed in `blindspots/`
  because validation returned no errors;
- after implementation, that same blindspot failed with a refusal naming
  `src/coherence_demo/recovery_schema.sql` and explaining both operator exits;
- after reclassification, `adversarial/unread_alter_only_schema` passes because
  validation refuses the unread listed file; and
- all remaining blindspot witnesses still pass, including
  `unlisted_schema_file`; and
- `removed_schema_file` passes as a new disclosure proving that removing a file
  from `schema_files` returns its durable state to silent, unread status.

Repository measurement established:

- delta O: `NO_CHANGE`;
- delta S: `NO_CHANGE`;
- delta A: `NO_CHANGE`;
- no governed fact changed;
- no carrier, writer, decision right, historical source, representation, or
  client responsibility changed; and
- no constitutional failure flag was introduced.

The closure is limited to files explicitly listed in
`discovery.schema_files` that yield zero tables under the existing parser. The
parser was not broadened. ORM declarations and state in unlisted files remain
outside discovery coverage.

Verification commands:

```text
python -m constitutional.measure --root . --record
python -m constitutional.validate --root . \
  --delta docs/work/changes/CHANGE-043/constitutional-delta.yaml \
  --actual-delta docs/work/changes/CHANGE-043/actual-constitutional-delta.yaml
python -m pytest
```

Results: measured delta matched the Plan, constitutional validation passed, and
all 34 tests passed.
