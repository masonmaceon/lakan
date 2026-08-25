-- ============================================================
-- Lakán DLSU-D — RAG chunk table
-- No pgvector extension needed: embeddings are stored as plain
-- double precision[] arrays and cosine similarity is computed in
-- the app (fine at this scale: hundreds of chunks, not millions).
-- Apply with:  psql "$DATABASE_URL" -f schema_rag.sql
-- ============================================================

CREATE TABLE IF NOT EXISTS memo_chunks (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    memo_id BIGINT NOT NULL,
    chunk_index INT NOT NULL,
    content TEXT NOT NULL,
    embedding DOUBLE PRECISION[],
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (memo_id) REFERENCES memos (id) ON DELETE CASCADE,
    UNIQUE (memo_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS idx_memo_chunks_memo ON memo_chunks (memo_id);
