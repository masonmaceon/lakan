-- ============================================================
-- Lakán DLSU-D — PostgreSQL schema (Render + Neon friendly)
-- Replaces the old MariaDB schema, and adds the tables that
-- previously only existed on the dead Railway MySQL instance:
--   memos, admins
-- Apply with:  psql "$DATABASE_URL" -f schema_postgres.sql
-- ============================================================

BEGIN;

DROP TABLE IF EXISTS memo_chunks CASCADE;
DROP TABLE IF EXISTS pathway_connections CASCADE;
DROP TABLE IF EXISTS pathway_points CASCADE;
DROP TABLE IF EXISTS pathways CASCADE;
DROP TABLE IF EXISTS locations CASCADE;
DROP TABLE IF EXISTS memos CASCADE;
DROP TABLE IF EXISTS admins CASCADE;

-- ==================== LOCATIONS ====================
CREATE TABLE locations (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    location_type VARCHAR(50) DEFAULT 'building',
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT lat_range  CHECK (latitude  BETWEEN  -90 AND  90),
    CONSTRAINT lng_range  CHECK (longitude BETWEEN -180 AND 180)
);
CREATE INDEX idx_location_type ON locations (location_type);
CREATE INDEX idx_location_coordinates ON locations (latitude, longitude);

-- ==================== PATHWAYS ====================
CREATE TABLE pathways (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    pathway_type VARCHAR(50) DEFAULT 'pedestrian',
    surface VARCHAR(50) DEFAULT 'concrete',
    width NUMERIC(4, 2) DEFAULT 2.0,
    is_shaded BOOLEAN DEFAULT FALSE,
    is_accessible BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_pathway_type ON pathways (pathway_type);

-- ==================== PATHWAY POINTS ====================
CREATE TABLE pathway_points (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pathway_id VARCHAR(50) NOT NULL,
    point_index INT NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (pathway_id) REFERENCES pathways (id) ON DELETE CASCADE,
    UNIQUE (pathway_id, point_index)
);
CREATE INDEX idx_pathway_points ON pathway_points (pathway_id, point_index);
CREATE INDEX idx_pathway_point_coordinates ON pathway_points (latitude, longitude);

-- ==================== PATHWAY CONNECTIONS ====================
CREATE TABLE pathway_connections (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pathway1_id VARCHAR(50) NOT NULL,
    pathway1_point_index INT NOT NULL,
    pathway2_id VARCHAR(50) NOT NULL,
    pathway2_point_index INT NOT NULL,
    connection_type VARCHAR(50) DEFAULT 'auto_detected',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (pathway1_id) REFERENCES pathways (id) ON DELETE CASCADE,
    FOREIGN KEY (pathway2_id) REFERENCES pathways (id) ON DELETE CASCADE,
    UNIQUE (pathway1_id, pathway1_point_index, pathway2_id, pathway2_point_index)
);

-- ==================== MEMOS (RAG source documents) ====================
CREATE TABLE memos (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    content TEXT,
    file_data BYTEA,
    uploaded_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_memos_uploaded ON memos (uploaded_at DESC);
CREATE INDEX idx_memos_filename ON memos (filename);

-- ==================== ADMINS ====================
-- lakan_dlsud stores passwords as werkzeug hashes (see seed.py / app.py).
CREATE TABLE admins (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ==================== auto-update updated_at ====================
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_locations_updated BEFORE UPDATE ON locations
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_pathways_updated BEFORE UPDATE ON pathways
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

COMMIT;
