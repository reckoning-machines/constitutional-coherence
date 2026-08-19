# CHANGE-043 Plan: Refuse unread schema files

Status: **COMPLETED**.

Legitimate authority:
`docs/decisions/DEC-014-version-currentness.md`, which preserves Branch
Authority as the sole owner of `branch.current_version`.

Constitutional Delta:

- delta O: `NO_CHANGE`;
- delta S: `NO_CHANGE`; and
- delta A: `NO_CHANGE`.

Delta A remains `NO_CHANGE` because `constitutional/` and `tests/` are outside
the governed paths by prior declaration in `constitutional/gate_rules.yaml`.
The checker cannot assign itself a governed product decision right; its source
is protected by review ownership rather than the Authority Topology.

Audit -> Plan -> Implement -> Verify:

1. record a blind-spot witness showing that a configured `ALTER TABLE`-only
   schema file yields no discovery or validation error;
2. make zero-table schema discovery fail with the file and reason, surfaced by
   validation as a refusal without broadening SQL parsing;
3. reclassify the detected witness as adversarial and record the retired gap in
   the README; and
4. disclose the separate bypass where removing a file from `schema_files`
   returns it to silent, unread state, without fixing that bypass; and
5. measure the repository, validate the declared delta, and run the suite.

Discovery of any new product concept, meaning, carrier, writer, decision right,
historical source, or client responsibility stops this motion and returns it to
Audit.
