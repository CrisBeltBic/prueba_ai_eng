-- Initialisation script for chat_db.
-- PostgreSQL runs this automatically on first startup (docker-entrypoint-initdb.d).

SET client_encoding = 'UTF8'; --Encoding
SET search_path TO public;


-- Tables
CREATE TABLE IF NOT EXISTS chats (
    chat_id    VARCHAR(255) NOT NULL,
    user_id    VARCHAR(255),               -- nullable, reserved for future auth
    role       VARCHAR(20)  NOT NULL,      -- 'user' | 'assistant'
    content    TEXT         NOT NULL,
    sources    JSONB        NOT NULL DEFAULT '[]',
    timestamp  TIMESTAMP    NOT NULL DEFAULT NOW(),
    PRIMARY KEY (chat_id, timestamp)
);

-- Indexes
-- Speeds up the most common query: fetch all messages for a given chat_id
CREATE INDEX IF NOT EXISTS idx_chats_chat_id  ON chats(chat_id);

-- Speeds up ordering and the DESC+LIMIT subquery for short-term memory
CREATE INDEX IF NOT EXISTS idx_chats_timestamp ON chats(chat_id, timestamp DESC);
