-- DDL for Evidence table (Vector Layer)

CREATE TABLE evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_uri TEXT NOT NULL,
    fragment_span TEXT, -- e.g., "line 10-15" or "page 2"
    text TEXT NOT NULL,
    checksum TEXT, -- SHA256 of the text fragment
    embedding vector(384) -- Assuming a 384-dimensional embedding model
);

-- Index for fast vector search (choose one based on scale and tuning)
-- For smaller scale or initial PoC:
-- CREATE INDEX ON evidence USING ivfflat (embedding vector_l2_ops);

-- For larger scale or better recall/latency trade-offs:
-- CREATE INDEX ON evidence USING hnsw (embedding vector_l2_ops);

-- Index on source_uri for quick filtering/grouping
CREATE INDEX ON evidence (source_uri);

-- Index on checksum for deduplication
CREATE UNIQUE INDEX ON evidence (checksum);

