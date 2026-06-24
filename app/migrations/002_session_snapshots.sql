-- Migration 002: Session snapshots for Paid tier session pinning.
-- When a Paid session ends, its annotation history is saved here so the user
-- can resume it in a later session. Snapshots contain annotation metadata only —
-- no audio, no raw transcription text unless the user has opted in to STT retention.
--
-- Privacy: user_id scopes snapshots to the authenticated user. For self-hosted
-- installs with no cloud auth, user_id is an empty string (instance-shared).

CREATE TABLE IF NOT EXISTS session_snapshots (
    id              TEXT    PRIMARY KEY,            -- UUID
    user_id         TEXT    NOT NULL DEFAULT '',    -- cf_user from cloud mode; '' for self-hosted
    session_id      TEXT    NOT NULL,               -- original session_id (short 8-char)
    created_at      REAL    NOT NULL,               -- Unix epoch (time.time())
    ended_at        REAL    NOT NULL,               -- Unix epoch
    elcor           INTEGER NOT NULL DEFAULT 0,     -- 1 = Elcor subtext mode was active
    event_count     INTEGER NOT NULL DEFAULT 0,
    events_json     TEXT    NOT NULL DEFAULT '[]'   -- JSON array of ToneEvent dicts
);

CREATE INDEX IF NOT EXISTS idx_snapshots_user_time
    ON session_snapshots (user_id, ended_at DESC);
