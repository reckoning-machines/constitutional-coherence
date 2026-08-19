# CHANGE-043 Audit: Refuse unread schema files

Status: **COMPLETED**.

Governed fact exercised: `branch.current_version`.

Semantic owner: `docs/domain/version.md#branch-current-version`.

Legitimate authority: `docs/decisions/DEC-014-version-currentness.md`.

Repository-wide carrier and writer sweep found:

- canonical `sqlite.branches.head_version_id`;
- immutable `sqlite.branch_head_events.previous_version_id` and
  `sqlite.branch_head_events.new_version_id` receipts;
- `BranchRepository.create` and `BranchRepository.advance_head` as the only
  declared writers;
- Branch Authority as the owning commit boundary;
- the read-only API projection and ephemeral browser state; and
- one configured schema file, `src/coherence_demo/schema.sql`, parsed by a
  `CREATE TABLE` regular expression in `constitutional/discover.py`.

Discovery currently records columns yielded by that expression but records no
per-file evidence that a configured schema was readable. A listed, valid SQL
file containing only `ALTER TABLE` therefore yields zero tables and is silently
treated like a file containing no durable state.

No new product carrier, writer, decision right, historical source, or client
responsibility is required. The fixture will expose the existing observation
failure by adding a duplicate Branch HEAD carrier only inside a disposable test
repository.
