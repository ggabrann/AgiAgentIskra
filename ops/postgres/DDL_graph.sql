-- DDL for Graph Nodes (GraphRAG Layer)

CREATE TABLE graph_node (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type TEXT NOT NULL, -- e.g., 'Research', 'Data/KG', 'Agents/Tools', 'Safety/Policy'
    title TEXT NOT NULL,
    description TEXT,
    aliases TEXT[], -- Array of alternative names
    metadata JSONB -- For additional structured data
);

-- Index on type for quick filtering
CREATE INDEX ON graph_node (type);

-- DDL for Graph Edges (GraphRAG Layer)

CREATE TABLE graph_edge (
    source_id UUID REFERENCES graph_node(id),
    target_id UUID REFERENCES graph_node(id),
    type TEXT NOT NULL, -- e.g., 'SUPPORTS', 'CONTRADICTS', 'RELATES_TO', 'REQUIRES'
    weight REAL DEFAULT 1.0,
    metadata JSONB,
    PRIMARY KEY (source_id, target_id, type)
);

-- Index on edge type
CREATE INDEX ON graph_edge (type);

-- DDL for Mapping between Evidence and Graph Nodes

CREATE TABLE evidence_graph_mapping (
    evidence_id UUID REFERENCES evidence(id),
    graph_node_id UUID REFERENCES graph_node(id),
    confidence REAL DEFAULT 1.0,
    PRIMARY KEY (evidence_id, graph_node_id)
);

-- Index on graph_node_id for quick lookup of supporting evidence
CREATE INDEX ON evidence_graph_mapping (graph_node_id);

