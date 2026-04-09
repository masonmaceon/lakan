"""
Lakán - MySQL Database Integration for Flask
Replace these endpoints in your app.py
"""

import mysql.connector
from mysql.connector import Error
import os
from flask import jsonify

# MySQL Connection Pool (add this at the top of app.py after imports)
from mysql.connector import pooling

db_pool = pooling.MySQLConnectionPool(
    pool_name="lakan_pool",
    pool_size=5,
    host=os.getenv('MYSQL_HOST', 'localhost'),
    user=os.getenv('MYSQL_USER', 'root'),
    password=os.getenv('MYSQL_PASSWORD', ''),
    database=os.getenv('MYSQL_DATABASE', 'lakan_db')
)

def get_db_connection():
    """Get a connection from the pool"""
    try:
        return db_pool.get_connection()
    except Error as e:
        print(f"Error getting database connection: {e}")
        return None

# ==================== REPLACE THESE ENDPOINTS ====================

@app.route('/get-all-pathways', methods=['GET'])
def get_all_pathways():
    """Get all pathways from MySQL database"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify([])
        
        cursor = conn.cursor(dictionary=True)
        
        # Get all pathways
        cursor.execute("SELECT * FROM pathways")
        pathways = cursor.fetchall()
        
        # Get points for each pathway
        result = []
        for pathway in pathways:
            cursor.execute("""
                SELECT latitude, longitude 
                FROM pathway_points 
                WHERE pathway_id = %s 
                ORDER BY point_index
            """, (pathway['id'],))
            
            points = cursor.fetchall()
            
            result.append({
                'id': pathway['id'],
                'name': pathway['name'],
                'type': pathway['type'],
                'surface': pathway['surface'],
                'width': float(pathway['width']),
                'shaded': bool(pathway['shaded']),
                'accessible': bool(pathway['accessible']),
                'points': [[float(p['latitude']), float(p['longitude'])] for p in points]
            })
        
        conn.close()
        return jsonify(result)
        
    except Exception as e:
        print(f"Error loading pathways from MySQL: {e}")
        return jsonify([])

@app.route('/get-all-locations', methods=['GET'])
def get_all_locations():
    """Get all locations from MySQL database"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify([])
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM locations")
        locations = cursor.fetchall()
        
        result = []
        for loc in locations:
            result.append({
                'id': loc['id'],
                'name': loc['name'],
                'type': loc['type'],
                'coordinates': [float(loc['latitude']), float(loc['longitude'])],
                'description': loc.get('description', '')
            })
        
        conn.close()
        return jsonify(result)
        
    except Exception as e:
        print(f"Error loading locations from MySQL: {e}")
        return jsonify([])

@app.route('/get-all-links', methods=['GET'])
def get_all_links():
    """Get pathway connections from MySQL database"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify([])
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM pathway_connections")
        connections = cursor.fetchall()
        
        result = []
        for conn_data in connections:
            result.append({
                'pathway1': conn_data['pathway1_id'],
                'pathway1_index': conn_data['pathway1_point_index'],
                'pathway2': conn_data['pathway2_id'],
                'pathway2_index': conn_data['pathway2_point_index'],
                'type': conn_data['connection_type']
            })
        
        conn.close()
        return jsonify(result)
        
    except Exception as e:
        print(f"Error loading connections from MySQL: {e}")
        return jsonify([])

@app.route('/api/save-pathway', methods=['POST'])
def save_pathway():
    """Save a new pathway to MySQL database"""
    try:
        data = request.get_json()
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        # Insert or update pathway
        cursor.execute("""
            INSERT INTO pathways (id, name, type, surface, width, shaded, accessible)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
            name = VALUES(name),
            type = VALUES(type),
            surface = VALUES(surface),
            width = VALUES(width),
            shaded = VALUES(shaded),
            accessible = VALUES(accessible)
        """, (
            data['id'],
            data.get('name', data['id']),
            data.get('type', 'pedestrian'),
            data.get('surface', 'concrete'),
            data.get('width', 2.0),
            data.get('shaded', False),
            data.get('accessible', True)
        ))
        
        # Delete old points
        cursor.execute("DELETE FROM pathway_points WHERE pathway_id = %s", (data['id'],))
        
        # Insert new points
        point_query = """
            INSERT INTO pathway_points (pathway_id, point_index, latitude, longitude)
            VALUES (%s, %s, %s, %s)
        """
        
        for index, point in enumerate(data['points']):
            cursor.execute(point_query, (data['id'], index, point[0], point[1]))
        
        conn.commit()
        conn.close()
        
        # Auto-detect new connections
        auto_detect_pathway_connections(data['id'])
        
        return jsonify({
            'message': f'Pathway {data["id"]} saved successfully',
            'points': len(data['points'])
        })
        
    except Exception as e:
        print(f"Error saving pathway: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/save-location', methods=['POST'])
def save_location():
    """Save a new location to MySQL database"""
    try:
        data = request.get_json()
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO locations (id, name, type, latitude, longitude, description)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
            name = VALUES(name),
            type = VALUES(type),
            latitude = VALUES(latitude),
            longitude = VALUES(longitude),
            description = VALUES(description)
        """, (
            data['id'],
            data['name'],
            data.get('type', 'building'),
            data['coordinates'][0],
            data['coordinates'][1],
            data.get('description', '')
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': f'Location {data["id"]} saved successfully'
        })
        
    except Exception as e:
        print(f"Error saving location: {e}")
        return jsonify({'error': str(e)}), 500

def auto_detect_pathway_connections(pathway_id=None, tolerance=0.00001):
    """Auto-detect connections for a specific pathway or all pathways"""
    try:
        conn = get_db_connection()
        if not conn:
            return
        
        cursor = conn.cursor()
        
        # If specific pathway, delete its old connections
        if pathway_id:
            cursor.execute("""
                DELETE FROM pathway_connections 
                WHERE pathway1_id = %s OR pathway2_id = %s
            """, (pathway_id, pathway_id))
        
        # Get points to check
        if pathway_id:
            cursor.execute("""
                SELECT pathway_id, point_index, latitude, longitude 
                FROM pathway_points 
                WHERE pathway_id = %s
            """, (pathway_id,))
            new_points = cursor.fetchall()
            
            cursor.execute("""
                SELECT pathway_id, point_index, latitude, longitude 
                FROM pathway_points 
                WHERE pathway_id != %s
            """, (pathway_id,))
            all_points = cursor.fetchall()
        else:
            cursor.execute("""
                SELECT pathway_id, point_index, latitude, longitude 
                FROM pathway_points 
                ORDER BY pathway_id, point_index
            """)
            all_points = cursor.fetchall()
            new_points = all_points
        
        # Find connections
        connections = []
        for point1 in new_points:
            for point2 in all_points:
                # Skip same pathway
                if point1[0] == point2[0]:
                    continue
                
                # Check if coordinates match
                lat_diff = abs(point1[2] - point2[2])
                lng_diff = abs(point1[3] - point2[3])
                
                if lat_diff < tolerance and lng_diff < tolerance:
                    # Add connection (avoid duplicates)
                    if point1[0] < point2[0]:  # Alphabetical order
                        connections.append((point1[0], point1[1], point2[0], point2[1]))
                    else:
                        connections.append((point2[0], point2[1], point1[0], point1[1]))
        
        # Remove duplicates
        connections = list(set(connections))
        
        # Insert connections
        if connections:
            cursor.executemany("""
                INSERT INTO pathway_connections 
                (pathway1_id, pathway1_point_index, pathway2_id, pathway2_point_index, connection_type)
                VALUES (%s, %s, %s, %s, 'auto_detected')
                ON DUPLICATE KEY UPDATE connection_type = 'auto_detected'
            """, connections)
        
        conn.commit()
        conn.close()
        
        print(f"✅ Auto-detected {len(connections)} connections")
        
    except Exception as e:
        print(f"Error auto-detecting connections: {e}")
