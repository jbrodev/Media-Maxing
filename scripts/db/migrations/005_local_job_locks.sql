CREATE TABLE IF NOT EXISTS local_job_locks (
  id TEXT PRIMARY KEY,
  owner TEXT NOT NULL,
  locked_at TEXT NOT NULL,
  expires_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_local_job_locks_expires_at
  ON local_job_locks(expires_at);
