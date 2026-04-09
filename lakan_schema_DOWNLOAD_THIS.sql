-- Lakán Campus Navigation System - MySQL Database Schema
-- Complete database design for campus navigation

-- Drop existing tables if they exist (for clean setup)
DROP TABLE IF EXISTS pathway_connections;
DROP TABLE IF EXISTS pathway_points;
DROP TABLE IF EXISTS pathways;
DROP TABLE IF EXISTS locations;

-- ==================== LOCATIONS TABLE ====================
-- Stores all buildings, gates, amenities, etc.
CREATE TABLE locations (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type ENUM('building', 'gate', 'amenity', 'service', 'landmark', 'parking') DEFAULT 'building',
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_location_type (type),
    INDEX idx_coordinates (latitude, longitude)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==================== PATHWAYS TABLE ====================
-- Stores pathway metadata (the routes themselves)
CREATE TABLE pathways (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type ENUM('pedestrian', 'vehicle', 'mixed') DEFAULT 'pedestrian',
    surface VARCHAR(50) DEFAULT 'concrete',
    width DECIMAL(4, 2) DEFAULT 2.0,
    shaded BOOLEAN DEFAULT FALSE,
    accessible BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_pathway_type (type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==================== PATHWAY POINTS TABLE ====================
-- Stores the actual GPS coordinates for each pathway
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
-- Stores connections between pathways (intersections)
CREATE TABLE pathway_connections (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pathway1_id VARCHAR(50) NOT NULL,
    pathway1_point_index INT NOT NULL,
    pathway2_id VARCHAR(50) NOT NULL,
    pathway2_point_index INT NOT NULL,
    connection_type ENUM('intersection', 'endpoint', 'auto_detected') DEFAULT 'auto_detected',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (pathway1_id) REFERENCES pathways(id) ON DELETE CASCADE,
    FOREIGN KEY (pathway2_id) REFERENCES pathways(id) ON DELETE CASCADE,
    INDEX idx_pathway1 (pathway1_id, pathway1_point_index),
    INDEX idx_pathway2 (pathway2_id, pathway2_point_index),
    UNIQUE KEY unique_connection (pathway1_id, pathway1_point_index, pathway2_id, pathway2_point_index)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==================== SAMPLE DATA ====================
-- Insert sample location
INSERT INTO locations (id, name, type, latitude, longitude, description) VALUES
('Gate 1', 'Gate 1 (Main Entrance)', 'gate', 14.321726, 120.963558, 'Main entrance to DLSU-D'),
('CEAT', 'College of Engineering, Architecture and Technology', 'building', 14.322807, 120.958537, 'Engineering and Architecture building'),
('Library', 'Rizal Library', 'building', 14.320715, 120.961795, 'Main campus library');

-- Insert sample pathway
INSERT INTO pathways (id, name, type, surface, width, shaded, accessible) VALUES
('lakeavenue', 'Lake Avenue', 'pedestrian', 'concrete', 3.0, TRUE, TRUE);

-- Insert sample pathway points
INSERT INTO pathway_points (pathway_id, point_index, latitude, longitude) VALUES
('lakeavenue', 0, 14.321557, 120.963225),
('lakeavenue', 1, 14.321526, 120.962675),
('lakeavenue', 2, 14.321489, 120.962313),
('lakeavenue', 3, 14.321419, 120.961694);

-- ==================== USEFUL QUERIES ====================

-- Query 1: Get all points for a pathway (ordered)
-- SELECT * FROM pathway_points WHERE pathway_id = 'lakeavenue' ORDER BY point_index;

-- Query 2: Find pathways near a location (within ~100m = ~0.001 degrees)
-- SELECT DISTINCT p.* FROM pathways p
-- JOIN pathway_points pp ON p.id = pp.pathway_id
-- WHERE pp.latitude BETWEEN (14.321726 - 0.001) AND (14.321726 + 0.001)
-- AND pp.longitude BETWEEN (120.963558 - 0.001) AND (120.963558 + 0.001);

-- Query 3: Find all connections for a pathway
-- SELECT * FROM pathway_connections 
-- WHERE pathway1_id = 'lakeavenue' OR pathway2_id = 'lakeavenue';

-- Query 4: Get complete pathway with all points (for navigation)
-- SELECT p.*, pp.point_index, pp.latitude, pp.longitude
-- FROM pathways p
-- LEFT JOIN pathway_points pp ON p.id = pp.pathway_id
-- WHERE p.id = 'lakeavenue'
-- ORDER BY pp.point_index;
