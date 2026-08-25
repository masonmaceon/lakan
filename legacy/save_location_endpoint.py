"""
Add this endpoint to your app.py
Put it right after the save_pathway endpoint
"""

@app.route('/api/save-location', methods=['POST'])
def save_location():
    """Save location directly to firestore_locations_fixed.json"""
    try:
        data = request.json
        location_id = data.get('id')
        location_name = data.get('name')
        coordinates = data.get('coordinates', [])
        location_type = data.get('type', 'building')
        
        if not location_id or not location_name or len(coordinates) != 2:
            return jsonify({'error': 'Invalid location data'}), 400
        
        # Load existing locations
        locations_file = 'firestore_locations_fixed.json'
        locations = []
        
        if os.path.exists(locations_file):
            with open(locations_file, 'r', encoding='utf-8') as f:
                locations = json.load(f)
        
        # Check if location ID already exists
        existing_index = None
        for i, location in enumerate(locations):
            if location.get('id') == location_id:
                existing_index = i
                break
        
        # Create new location
        new_location = {
            'id': location_id,
            'name': location_name,
            'coordinates': coordinates,
            'type': location_type
        }
        
        # Update or append
        if existing_index is not None:
            locations[existing_index] = new_location
            message = f'Updated location "{location_name}" - Live now!'
        else:
            locations.append(new_location)
            message = f'Added location "{location_name}" - Live now!'
        
        # Save to file
        with open(locations_file, 'w', encoding='utf-8') as f:
            json.dump(locations, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Saved location: {location_name} at {coordinates}")
        
        return jsonify({
            'success': True,
            'message': message,
            'total_locations': len(locations),
            'needs_restart': False
        })
        
    except Exception as e:
        print(f"Save location error: {e}")
        return jsonify({'error': str(e)}), 500
