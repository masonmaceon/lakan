-- Lakán Campus Navigation System - MariaDB Compatible Schema
-- Fixed for MariaDB compatibility

-- Drop existing tables if they exist
DROP TABLE IF EXISTS pathway_connections;
DROP TABLE IF EXISTS pathway_points;
DROP TABLE IF EXISTS pathways;
DROP TABLE IF EXISTS locations;

-- ==================== LOCATIONS TABLE ====================
CREATE TABLE locations (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    location_type VARCHAR(50) DEFAULT 'building',
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_location_type (location_type),
    INDEX idx_coordinates (latitude, longitude)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==================== PATHWAYS TABLE ====================
CREATE TABLE pathways (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    pathway_type VARCHAR(50) DEFAULT 'pedestrian',
    surface VARCHAR(50) DEFAULT 'concrete',
    width DECIMAL(4, 2) DEFAULT 2.0,
    is_shaded TINYINT(1) DEFAULT 0,
    is_accessible TINYINT(1) DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_pathway_type (pathway_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==================== PATHWAY POINTS TABLE ====================
CREATE TABLE pathway_points (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pathway_id VARCHAR(50) NOT NULL,
    point_index INT NOT NULL,
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (pathway_id) REFERENCES pathways(id) ON DELETE CASCADE,
    INDEX idx_pathway_points (pathway_id, point_index),
    INDEX idx_coordinates (latitude, longitude),
    UNIQUE KEY unique_pathway_point (pathway_id, point_index)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==================== PATHWAY CONNECTIONS TABLE ====================
CREATE TABLE pathway_connections (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pathway1_id VARCHAR(50) NOT NULL,
    pathway1_point_index INT NOT NULL,
    pathway2_id VARCHAR(50) NOT NULL,
    pathway2_point_index INT NOT NULL,
    connection_type VARCHAR(50) DEFAULT 'auto_detected',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (pathway1_id) REFERENCES pathways(id) ON DELETE CASCADE,
    FOREIGN KEY (pathway2_id) REFERENCES pathways(id) ON DELETE CASCADE,
    INDEX idx_pathway1 (pathway1_id, pathway1_point_index),
    INDEX idx_pathway2 (pathway2_id, pathway2_point_index),
    UNIQUE KEY unique_connection (pathway1_id, pathway1_point_index, pathway2_id, pathway2_point_index)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==================== SAMPLE DATA ====================
INSERT INTO locations (id, name, location_type, latitude, longitude, description) VALUES
('Gate 1', 'Gate 1 (Main Entrance)', 'gate', 14.321726, 120.963558, 'Main entrance to DLSU-D'),
('CEAT', 'College of Engineering, Architecture and Technology', 'building', 14.322807, 120.958537, 'Engineering and Architecture building'),
('Library', 'Rizal Library', 'building', 14.320715, 120.961795, 'Main campus library');

INSERT INTO pathways (id, name, pathway_type, surface, width, is_shaded, is_accessible) VALUES
('lakeavenue', 'Lake Avenue', 'pedestrian', 'concrete', 3.0, 1, 1);

INSERT INTO pathway_points (pathway_id, point_index, latitude, longitude) VALUES
('lakeavenue', 0, 14.321557, 120.963225),
('lakeavenue', 1, 14.321526, 120.962675),
('lakeavenue', 2, 14.321489, 120.962313),
('lakeavenue', 3, 14.321419, 120.961694);
