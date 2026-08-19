PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS versions (
    version_id TEXT PRIMARY KEY,
    content_json TEXT NOT NULL,
    content_hash TEXT NOT NULL
);

CREATE TRIGGER IF NOT EXISTS versions_immutable_update
BEFORE UPDATE ON versions
BEGIN
    SELECT RAISE(ABORT, 'versions are immutable');
END;

CREATE TRIGGER IF NOT EXISTS versions_immutable_delete
BEFORE DELETE ON versions
BEGIN
    SELECT RAISE(ABORT, 'versions are immutable');
END;

CREATE TABLE IF NOT EXISTS branches (
    branch_id TEXT PRIMARY KEY,
    head_version_id TEXT NOT NULL REFERENCES versions(version_id)
);

CREATE TABLE IF NOT EXISTS branch_head_events (
    event_id TEXT PRIMARY KEY,
    branch_id TEXT NOT NULL REFERENCES branches(branch_id),
    previous_version_id TEXT REFERENCES versions(version_id),
    new_version_id TEXT NOT NULL REFERENCES versions(version_id),
    sequence INTEGER NOT NULL,
    UNIQUE (branch_id, sequence)
);

CREATE TRIGGER IF NOT EXISTS branch_head_events_immutable_update
BEFORE UPDATE ON branch_head_events
BEGIN
    SELECT RAISE(ABORT, 'branch head receipts are immutable');
END;

CREATE TRIGGER IF NOT EXISTS branch_head_events_immutable_delete
BEFORE DELETE ON branch_head_events
BEGIN
    SELECT RAISE(ABORT, 'branch head receipts are immutable');
END;

CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    branch_id TEXT NOT NULL REFERENCES branches(branch_id),
    version_id TEXT NOT NULL REFERENCES versions(version_id),
    status TEXT NOT NULL CHECK (status IN ('success', 'failed'))
);

CREATE TRIGGER IF NOT EXISTS runs_immutable_update
BEFORE UPDATE ON runs
BEGIN
    SELECT RAISE(ABORT, 'runs are immutable');
END;

CREATE TRIGGER IF NOT EXISTS runs_immutable_delete
BEFORE DELETE ON runs
BEGIN
    SELECT RAISE(ABORT, 'runs are immutable');
END;

CREATE TABLE IF NOT EXISTS results (
    run_id TEXT PRIMARY KEY REFERENCES runs(run_id),
    payload_json TEXT NOT NULL,
    content_hash TEXT NOT NULL
);

CREATE TRIGGER IF NOT EXISTS results_immutable_update
BEFORE UPDATE ON results
BEGIN
    SELECT RAISE(ABORT, 'results are immutable');
END;

CREATE TRIGGER IF NOT EXISTS results_immutable_delete
BEFORE DELETE ON results
BEGIN
    SELECT RAISE(ABORT, 'results are immutable');
END;
