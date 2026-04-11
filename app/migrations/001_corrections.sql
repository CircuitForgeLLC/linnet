-- Migration 001: Corrections table for tone annotation training data.
-- Users can rate annotations (up/down) and submit corrected versions.
-- Only opted_in=1 rows are exported to the Avocet SFT pipeline.

CREATE TABLE IF NOT EXISTS corrections (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id          TEXT    NOT NULL DEFAULT '',   -- session_id or event_id
    product          TEXT    NOT NULL DEFAULT 'linnet',
    correction_type  TEXT    NOT NULL DEFAULT 'annotation',
    input_text       TEXT    NOT NULL,              -- the utterance that was annotated
    original_output  TEXT    NOT NULL,              -- the LLM annotation produced
    corrected_output TEXT    NOT NULL DEFAULT '',   -- user's correction (empty = thumbs up)
    rating           TEXT    NOT NULL DEFAULT 'down', -- 'up' | 'down'
    context          TEXT    NOT NULL DEFAULT '{}', -- JSON: session_id, model, elcor flag, etc.
    opted_in         INTEGER NOT NULL DEFAULT 0,    -- 1 = user consented to share for training
    created_at       TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_corrections_product  ON corrections (product);
CREATE INDEX IF NOT EXISTS idx_corrections_opted_in ON corrections (opted_in);
CREATE INDEX IF NOT EXISTS idx_corrections_item_id  ON corrections (item_id);
