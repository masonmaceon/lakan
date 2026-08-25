"""
Lakán - Firebase/JSON to MySQL Migration Script
Migrates pathway and location data from JSON files to MySQL database
"""

import json
import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_connection():
    """Create MySQL database connection"""
    try:
        connection = mysql.connector.connect(
            host=os.getenv('MYSQL_HOST', 'localhost'),
            user=os.getenv('MYSQL_USER', 'root'),
            password=os.getenv('MYSQL_PASSWORD', ''),
            database=os.getenv('MYSQL_DATABASE', 'lakan_db')
        )
        if connection.is_connected():
            print("✅ Connected to MySQL database")
            return connection
    except Error as e:
        print(f"❌ Error connecting to MySQL: {e}")
        return None

def migrate_locations(connection, json_file='firestore_locations_fixed.json'):
    """Migrate locations from JSON to MySQL"""
    print(f"\n📍 Migrating locations from {json_file}...")
    
    try:
        # Load JSON data
        with open(json_file, 'r', encoding='utf-8') as f:
            locations = json.load(f)
        
        cursor = connection.cursor()
        
        # Clear existing data
        cursor.execute("DELETE FROM locations")
        print(f"  🗑️  Cleared existing locations")
        
        # Insert locations
        insert_query = """
            INSERT INTO locations (id, name, location_type, latitude, longitude, description)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        count = 0
        for location in locations:
            # Extract coordinates
            lat = location['coordinates'][0]
            lng = location['coordinates'][1]
            
            # Determine type (default to 'building')
            loc_type = location.get('type', 'building')
            
            # Get name (fallback to id if missing)
            loc_name = location.get('name', location['id'])
            
            # Insert
            cursor.execute(insert_query, (
                location['id'],
                loc_name,
                loc_type,
                lat,
                lng,
                location.get('description', '')
            ))
            count += 1
        
        connection.commit()
        print(f"  ✅ Migrated {count} locations")
        
    except Exception as e:
        print(f"  ❌ Error migrating locations: {e}")
        connection.rollback()

def migrate_pathways(connection, json_file='firestore_pathways_fixed.json'):
    """Migrate pathways from JSON to MySQL"""
    print(f"\n🛤️  Migrating pathways from {json_file}...")
    
    try:
        # Load JSON data
        with open(json_file, 'r', encoding='utf-8') as f:
            pathways = json.load(f)
        
        cursor = connection.cursor()
        
        # Clear existing data (cascades to pathway_points and pathway_connections)
        cursor.execute("DELETE FROM pathways")
        print(f"  🗑️  Cleared existing pathways")
        
        # Insert pathways and points
        pathway_query = """
            INSERT INTO pathways (id, name, pathway_type, surface, width, is_shaded, is_accessible)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        
        point_query = """
            INSERT INTO pathway_points (pathway_id, point_index, latitude, longitude)
            VALUES (%s, %s, %s, %s)
        """
        
        pathway_count = 0
        point_count = 0
        
        for pathway in pathways:
            # Insert pathway metadata
            cursor.execute(pathway_query, (
                pathway['id'],
                pathway.get('name', pathway['id']),
                pathway.get('type', 'pedestrian'),
                pathway.get('surface', 'concrete'),
                pathway.get('width', 2.0),
                1 if pathway.get('shaded', False) else 0,  # Convert to TINYINT
                1 if pathway.get('accessible', True) else 0  # Convert to TINYINT
            ))
            pathway_count += 1
            
            # Insert pathway points
            for index, point in enumerate(pathway['points']):
                cursor.execute(point_query, (
                    pathway['id'],
                    index,
                    point[0],  # latitude
                    point[1]   # longitude
                ))
                point_count += 1
        
        connection.commit()
        print(f"  ✅ Migrated {pathway_count} pathways with {point_count} points")
        
    except Exception as e:
        print(f"  ❌ Error migrating pathways: {e}")
        connection.rollback()

def auto_detect_connections(connection, tolerance=0.00001):
    """Auto-detect pathway connections based on shared coordinates"""
    print(f"\n🔗 Auto-detecting pathway connections...")
    
    try:
        cursor = connection.cursor()
        
        # Clear existing connections
        cursor.execute("DELETE FROM pathway_connections")
        
        # Find all pathway points
        cursor.execute("""
            SELECT pathway_id, point_index, latitude, longitude 
            FROM pathway_points 
            ORDER BY pathway_id, point_index
        """)
        
        points = cursor.fetchall()
        
        # Compare all points to find matches
        connection_query = """
            INSERT INTO pathway_connections 
            (pathway1_id, pathway1_point_index, pathway2_id, pathway2_point_index, connection_type)
            VALUES (%s, %s, %s, %s, 'auto_detected')
        """
        
        connections = []
        for i, point1 in enumerate(points):
            for point2 in points[i+1:]:
                # Skip same pathway
                if point1[0] == point2[0]:
                    continue
                
                # Check if coordinates match (within tolerance)
                lat_diff = abs(point1[2] - point2[2])
                lng_diff = abs(point1[3] - point2[3])
                
                if lat_diff < tolerance and lng_diff < tolerance:
                    # Found a connection!
                    connections.append((
                        point1[0],  # pathway1_id
                        point1[1],  # pathway1_point_index
                        point2[0],  # pathway2_id
                        point2[1]   # pathway2_point_index
                    ))
        
        # Insert connections
        if connections:
            cursor.executemany(connection_query, connections)
            connection.commit()
            print(f"  ✅ Found and saved {len(connections)} pathway connections")
        else:
            print(f"  ⚠️  No connections found (tolerance = {tolerance})")
        
    except Exception as e:
        print(f"  ❌ Error detecting connections: {e}")
        connection.rollback()

def verify_migration(connection):
    """Verify the migration was successful"""
    print(f"\n✅ Verifying migration...")
    
    cursor = connection.cursor()
    
    # Count locations
    cursor.execute("SELECT COUNT(*) FROM locations")
    location_count = cursor.fetchone()[0]
    print(f"  📍 Locations: {location_count}")
    
    # Count pathways
    cursor.execute("SELECT COUNT(*) FROM pathways")
    pathway_count = cursor.fetchone()[0]
    print(f"  🛤️  Pathways: {pathway_count}")
    
    # Count pathway points
    cursor.execute("SELECT COUNT(*) FROM pathway_points")
    point_count = cursor.fetchone()[0]
    print(f"  📌 Pathway points: {point_count}")
    
    # Count connections
    cursor.execute("SELECT COUNT(*) FROM pathway_connections")
    connection_count = cursor.fetchone()[0]
    print(f"  🔗 Pathway connections: {connection_count}")
    
    print(f"\n🎉 Migration complete!")

if __name__ == "__main__":
    print("=" * 60)
    print("Lakán - JSON to MySQL Migration")
    print("=" * 60)
    
    # Create connection
    conn = create_connection()
    
    if conn:
        try:
            # Run migrations
            migrate_locations(conn)
            migrate_pathways(conn)
            auto_detect_connections(conn)
            verify_migration(conn)
            
        finally:
            conn.close()
            print("\n✅ Database connection closed")
    else:
        print("❌ Could not establish database connection")
        print("Make sure MySQL is running and credentials are correct in .env file")
