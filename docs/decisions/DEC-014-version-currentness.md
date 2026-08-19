# DEC-014 — Branch currentness projections

Status: **ADMITTED**

Branch Authority remains the sole owner of `branch.current_version`.

The Branch summary API may expose `head_version_id` as a read-only `DERIVED`
representation. Browser state may retain the returned identity as `EPHEMERAL`
selection state. Neither representation may select currentness, authorize a
Branch transition, resolve conflict, or answer historical Branch truth.
