# CHANGE-042 Audit — Branch summary projection

Governed fact touched: `branch.current_version`.

Semantic owner: `docs/domain/version.md#branch-current-version`.

Repository sweep found:

- canonical `branches.head_version_id`;
- immutable `branch_head_events.previous_version_id` and `new_version_id`;
- Branch repository create and advance writers;
- Branch Authority as the application commit boundary;
- the read-only API projection; and
- ephemeral browser selection state.

No second durable currentness carrier or writer is required.
