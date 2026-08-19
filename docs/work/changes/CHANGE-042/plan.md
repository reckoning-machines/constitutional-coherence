# CHANGE-042 Plan — Branch summary projection

Legitimate authority: `docs/decisions/DEC-014-version-currentness.md`.

Add one backend-owned read-only Branch summary projection. It repeats the
canonical `head_version_id` and does not receive mutation, conflict-resolution,
historical, or currentness decision rights.

The implementation is bounded by
`constitutional-delta.yaml`. Discovery of another carrier, writer, or decision
right returns this motion to Audit.
