"""
Campus Chatbot - DeepSeek Integration
AUTO-LOADS buildings from JSON - no manual mapping needed!
"""

import os
import re
import random
import requests
import json
from dotenv import load_dotenv

load_dotenv()

class CampusChatbot:
    def __init__(self):
        self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
        self.deepseek_enabled = self.deepseek_api_key is not None
        
        # Load building data from JSON
        self.load_campus_data()
        
        # Auto-generate building mappings from loaded data
        self.generate_building_mappings()
    
    def load_campus_data(self):
        """Load campus data from JSON files"""
        try:
            # Load locations
            if os.path.exists('firestore_locations_fixed.json'):
                with open('firestore_locations_fixed.json', 'r') as f:
                    self.buildings = json.load(f)
                print(f"✅ Loaded {len(self.buildings)} buildings from JSON")
            else:
                self.buildings = []
                print("⚠️  No building data file found")
        except Exception as e:
            print(f"Error loading campus data: {e}")
            self.buildings = []
    
    def generate_building_mappings(self):
        """Auto-generate building name mappings from loaded buildings"""
        self.building_mappings = {}
        self.building_info = {}
        
        # Descriptions for places that need clarification (not just buildings)
        self.place_descriptions = {
            'Square': 'an open-air area with food stalls and small stores, not a building',
        }

        # Add manual aliases for common terms
        manual_aliases = {
            'administration': 'Admin',
            'main entrance': 'Gate 1',
            'main gate': 'Gate 1',
            'cafeteria': 'Square',
            'canteen': 'Square',
            'food court': 'Square',
        }
        
        # Auto-generate from building data
        for building in self.buildings:
            building_id = building.get('id', '')
            building_name = building.get('name', building.get('name ', ''))
            
            if not building_id:
                continue
            
            # Add ID itself (lowercase)
            self.building_mappings[building_id.lower()] = building_id
            
            # Add full name (lowercase)
            if building_name:
                self.building_mappings[building_name.lower()] = building_id
                
                # Add each word from the name
                words = building_name.lower().split()
                for word in words:
                    if len(word) > 3:  # Only meaningful words
                        # Don't overwrite if already exists
                        if word not in self.building_mappings:
                            self.building_mappings[word] = building_id
            
            # Store building info
            self.building_info[building_id] = building_name if building_name else building_id
        
        # Add manual aliases (these override auto-generated)
        self.building_mappings.update(manual_aliases)
        
        print(f"📍 Auto-generated {len(self.building_mappings)} building name variations")
    
    def get_response(self, user_input, context="", conversation=[], user_location=None):
        """Main entry point - get chatbot response"""
        user_input_lower = user_input.lower()

        # Inject location context if available
        location_context = ""
        if user_location:
            nearest = self.find_nearest_gate(user_location)
            if nearest:
                location_context = f"\nUser's current location: lat={user_location.get('lat')}, lng={user_location.get('lng')}. Nearest gate to user: {nearest['name']} ({nearest['distance_m']}m away)."

        # Check for nearest gate intent - handle directly with location awareness
        if self.is_gate_query(user_input_lower):
            return self.handle_gate_query(user_location)
        
        # 1. Check for greetings
        if self.is_greeting(user_input_lower):
            return {
                'response': random.choice([
                    "Hello! I'm Lakán, your DLSU-D navigation assistant. Ask me how to get somewhere!",
                    "Hi there! Need directions around campus? Just ask!",
                    "Greetings! Where would you like to go today?"
                ]),
                'action': None
            }
        
        # 2. Check for farewells
        if self.is_farewell(user_input_lower):
            return {
                'response': "Safe travels! Feel free to ask if you need directions again. Animo La Salle!",
                'action': None
            }
        
        # 3. Detect navigation intent
        nav_intent = self.detect_navigation_intent(user_input_lower)
        
        if nav_intent['is_navigation']:
            # Extract locations
            locations = self.extract_locations(user_input_lower)
            
            # Buildings known to be disconnected from pathways
            disconnected_buildings = []
            
            if nav_intent['type'] == 'directions' and locations:
                if len(locations) >= 2:
                    # Check if destination is disconnected
                    if locations[1] in disconnected_buildings:
                        building_info = self.get_building_info(locations[1])
                        building_name = building_info['name'] if building_info else locations[1]
                        return {
                            'response': f"📍 {building_name} is shown on the map, but it's not connected to our pathway system yet. I can show you its location, but can't provide turn-by-turn directions.",
                            'action': 'show_location',
                            'location': locations[1]
                        }
                    
                    # User specified both start and destination
                    building_info = self.get_building_info(locations[1])
                    building_name = building_info['name'] if building_info else locations[1]
                    return {
                        'response': f"🗺️ Showing route from {locations[0]} to {building_name}. Follow the green path!",
                        'action': 'navigate',
                        'start': locations[0],
                        'destination': locations[1]
                    }
                elif len(locations) == 1:
                    # Check if destination is disconnected
                    if locations[0] in disconnected_buildings:
                        building_info = self.get_building_info(locations[0])
                        building_name = building_info['name'] if building_info else locations[0]
                        return {
                            'response': f"📍 {building_name} is shown on the map, but it's not connected to our pathway system yet. You'll need to navigate there manually once you're on campus.",
                            'action': 'show_location',
                            'location': locations[0]
                        }
                    
                    # Only destination specified - use Gate 1 as default start
                    building_info = self.get_building_info(locations[0])
                    building_name = building_info['name'] if building_info else locations[0]
                    return {
                        'response': f"🗺️ Showing route to {building_name}. Follow the green path!",                        'action': 'navigate',
                        'start': 'Gate 1',
                        'destination': locations[0]
                    }
            
            elif nav_intent['type'] == 'location_query' and locations:
                building_id = locations[0]
                building_info = self.get_building_info(building_id)
                
                if building_info:
                    if building_id in disconnected_buildings:
                        return {
                            'response': f"📍 {building_info['name']} is shown on the map. Note: This building isn't connected to our pathway system yet.",
                            'action': 'show_location',
                            'location': building_id
                        }
                    return {
                        'response': f"📍 {building_info['name']} is shown on the map. Want directions? Ask 'How do I get to {building_id}?'",
                        'action': 'show_location',
                        'location': building_id
                    }
        
        # 4. Use DeepSeek for general queries
        if self.deepseek_enabled:
            return self.query_deepseek(user_input, context + location_context, conversation)
        else:
            return {
                'response': "I'm not sure how to help with that. Try asking 'How do I get to JFH?' or 'Where is the library?'",
                'action': None
            }
    
    def is_greeting(self, text):
        """Check if message is a greeting"""
        import re
        greetings = ['hello', 'hi', 'hey', 'greetings', 'good morning', 'good afternoon']
        return any(re.search(r'\b' + g + r'\b', text) for g in greetings)

    def is_farewell(self, text):
        """Check if message is a farewell"""
        import re
        farewells = ['bye', 'goodbye', 'see you', 'thanks', 'thank you']
        return any(re.search(r'\b' + g + r'\b', text) for g in farewells)
    
    def detect_navigation_intent(self, text):
        """Detect if user wants navigation"""
        
        # Direction/navigation keywords (more variations)
        direction_keywords = [
            'how do i get', 'how to get', 'how can i get', 'how do i go',
            'directions to', 'navigate to', 'route to', 
            'take me to', 'guide me to', 'show me the way', 'show me how',
            'i want to go to', 'i need to go to', 'going to',
            'walk to', 'get to'
        ]
        
        # Location query keywords
        location_keywords = [
            'where is', 'where\'s', 'location of', 'find',
            'show me', 'point me to', 'locate'
        ]
        
        # Check for direction intent
        for keyword in direction_keywords:
            if keyword in text:
                return {'is_navigation': True, 'type': 'directions'}
        
        # Check for location query
        for keyword in location_keywords:
            if keyword in text:
                # If they say "show me how to get" it's directions, not just location
                if any(d in text for d in ['how to get', 'how do i get', 'how can i get']):
                    return {'is_navigation': True, 'type': 'directions'}
                return {'is_navigation': True, 'type': 'location_query'}
        
        # Check if message contains a building name (might be implicit navigation)
        locations = self.extract_locations(text)
        if locations and len(text.split()) <= 5:  # Short query with building name
            # Probably asking for location/directions
            return {'is_navigation': True, 'type': 'directions'}
        
        return {'is_navigation': False, 'type': None}
    
    def extract_locations(self, text):
        """Extract building names from text using auto-generated mappings"""
        found_locations = []
        
        # Sort by length (longest first) to match full names before partial matches
        sorted_mappings = sorted(self.building_mappings.items(), 
                                key=lambda x: len(x[0]), 
                                reverse=True)
        
        for phrase, building_id in sorted_mappings:
            if re.search(r'\b' + re.escape(phrase) + r'\b', text):
                if building_id not in found_locations:
                    found_locations.append(building_id)
        
        return found_locations
    
    def get_building_info(self, building_id):
        """Get building information"""
        for building in self.buildings:
            if building.get('id') == building_id:
                # Get name from building data or use description
                name = building.get('name') or building.get('name ') or self.building_info.get(building_id, building_id)
                return {
                    'id': building_id,
                    'name': name,
                    'coordinates': building.get('coordinates', [0, 0])
                }
        return None
    
    # Gate coordinates and access rules
    GATES = {
        'Gate 1': {
            'coords': (14.321726, 120.963558),
            'pedestrian': True,
            'vehicle': False,
            'note': 'Main entrance. Pedestrians only — no vehicles allowed.'
        },
        'Gate 2': {
            'coords': (14.322526, 120.96341),
            'pedestrian': False,
            'vehicle': True,
            'note': 'Vehicles only. Nearest to Dasmariñas Bagong Bayan area.'
        },
        'Gate 3': {
            'coords': (14.32825137, 120.9569752),
            'pedestrian': True,
            'vehicle': True,
            'note': 'Open to both pedestrians and vehicles. Auxiliary entry.'
        },
        'Gate 4': {
            'coords': (14.320437, 120.963697),
            'pedestrian': False,
            'vehicle': True,
            'note': 'Vehicles only. Nearest to PCH, COS, and Admin buildings.'
        },
    }

    def is_gate_query(self, text):
        """Detect if user is asking about nearest gate or exit"""
        keywords = [
            'nearest gate', 'closest gate', 'nearest exit', 'closest exit',
            'how do i exit', 'how to exit', 'where is the exit', 'how to leave',
            'which gate', 'what gate', 'gate near me', 'exit campus',
            'leave campus', 'way out', 'get out'
        ]
        return any(k in text for k in keywords)

    def find_nearest_gate(self, user_location):
        """Find the nearest gate to the user's location"""
        if not user_location:
            return None
        try:
            import math
            lat = float(user_location.get('lat', 0))
            lng = float(user_location.get('lng', 0))

            nearest = None
            min_dist = float('inf')

            for gate_name, info in self.GATES.items():
                g_lat, g_lng = info['coords']
                # Simple Euclidean approximation (good enough for campus scale)
                dlat = (lat - g_lat) * 111320
                dlng = (lng - g_lng) * 111320 * abs(math.cos(math.radians(lat)))
                dist = math.sqrt(dlat**2 + dlng**2)
                if dist < min_dist:
                    min_dist = dist
                    nearest = {'name': gate_name, 'distance_m': round(dist), 'info': info}

            return nearest
        except Exception:
            return None

    def handle_gate_query(self, user_location):
        """Handle nearest gate / exit queries with location awareness"""
        if not user_location:
            return {
                'response': "To find your nearest gate, please enable GPS or set your location first. On foot, you can use Gate 1 (main) or Gate 3. By vehicle, use Gate 2, Gate 3, or Gate 4.",
                'action': None
            }

        nearest = self.find_nearest_gate(user_location)
        if not nearest:
            return {
                'response': "I couldn't determine your nearest gate. On foot, you can use Gate 1 or Gate 3. By vehicle, use Gate 2, Gate 3, or Gate 4.",
                'action': None
            }

        gate = nearest['name']
        dist = nearest['distance_m']
        info = nearest['info']

        if info['pedestrian'] and info['vehicle']:
            access = "open to both pedestrians and vehicles"
        elif info['pedestrian']:
            access = "for pedestrians only"
        else:
            access = "for vehicles only"

        response = (
            f"Your nearest gate is {gate}, about {dist}m away — {info['note']} "
            f"On foot, you can use Gate 1 or Gate 3. By vehicle, use Gate 2, Gate 3, or Gate 4."
        )

        return {
            'response': response,
            'action': 'navigate',
            'destination': gate,
            'start': 'current'
        }

    def get_memo_context(self):
        """Fetch memo contents from DB to inject into system prompt"""
        try:
            import mysql.connector
            from dotenv import load_dotenv
            load_dotenv()

            conn = mysql.connector.connect(
                host=os.getenv('MYSQL_HOST', 'localhost'),
                port=int(os.getenv('MYSQL_PORT', 3306)),
                user=os.getenv('MYSQL_USER', 'root'),
                password=os.getenv('MYSQL_PASSWORD', ''),
                database=os.getenv('MYSQL_DATABASE', 'lakan_db')
            )
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT title, content FROM memos WHERE content != '' ORDER BY uploaded_at DESC LIMIT 5")
            rows = cursor.fetchall()
            conn.close()

            if not rows:
                return ""

            memo_text = "Official DLSU-D announcements and memos:\n"
            for row in rows:
                memo_text += f"\n--- {row['title']} ---\n{row['content'][:4000]}\n"
            return memo_text

        except Exception as e:
            print(f"⚠️ Could not load memo context: {e}")
            return ""

    def query_deepseek(self, user_message, context="", conversation=[]):
        """Query DeepSeek API"""
        try:
            # Build system prompt with all known buildings
            building_list = ', '.join([b.get('id', '') for b in self.buildings])

            place_notes = '\n'.join([
                f"- {place}: {desc}"
                for place, desc in self.place_descriptions.items()
            ])

            # Fetch memo contents from DB for RAG
            memo_context = self.get_memo_context()

            system_prompt = f"""You are Lakán, the official campus navigation assistant for De La Salle University - Dasmariñas (DLSU-D).

Your ONLY purpose is to help with:
- Finding buildings, offices, and facilities on the DLSU-D campus
- Walking directions between campus locations
- Questions about campus services, departments, and offices
- Information from official DLSU-D memos or announcements
- Academic schedules, enrollment dates, and university calendars
- School events, activities, intramurals, and university programs
- Any question answerable from the uploaded memos above

Known campus locations: {building_list}

Gate access rules:
- Gate 1 (main entrance): pedestrians only, no vehicles
- Gate 2: vehicles only, nearest to Dasmariñas Bagong Bayan
- Gate 3 (Magdiwang Gate): open to both pedestrians and vehicles
- Gate 4: vehicles only, nearest to PCH/COS/Admin buildings

Important clarifications about specific places:
{place_notes}

{memo_context}

{context}

STRICT RULES:
- If the user asks about anything completely unrelated to DLSU-D — such as general knowledge, math, coding, other schools, national news, or personal advice — reply ONLY with: "I'm only here to help you navigate the DLSU-D campus! Try asking me where a building is or how to get somewhere. 😊"
- When in doubt, if the question could be related to university life, answer it.
- Never answer general knowledge, math, coding, other schools, current events, or personal advice — even if the user insists or rephrases.
- Never break character or pretend to be a different assistant.
- Keep all campus-related responses to 1-2 sentences, no bullet points.
- Never use markdown formatting like **bold**, *italic*, or # headers in your responses. Plain text only."""
            
            # Build messages
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add conversation history
            for msg in conversation[-5:]:  # Last 5 messages for context
                messages.append(msg)
            
            # Add current message
            messages.append({"role": "user", "content": user_message})
            
            # Call DeepSeek API
            response = requests.post(
                'https://api.deepseek.com/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {self.deepseek_api_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': 'deepseek-chat',
                    'messages': messages,
                    'temperature': 0.7,
                    'max_tokens': 300
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                bot_response = data['choices'][0]['message']['content']
                
                return {
                    'response': bot_response,
                    'action': None
                }
            else:
                print(f"DeepSeek API error: {response.status_code}")
                return {
                    'response': "I'm having trouble thinking right now. Please try asking about campus navigation!",
                    'action': None
                }
                
        except Exception as e:
            print(f"Error querying DeepSeek: {e}")
            return {
                'response': "Sorry, I'm having connection issues. Try asking 'How do I get to JFH?'",
                'action': None
            }


# For testing
if __name__ == "__main__":
    chatbot = CampusChatbot()
    
    # Test queries
    test_queries = [
        "Hello!",
        "Where is CEAT?",
        "How do I get to MLH?",
        "How to get from Admin to Square?",
    ]
    
    for query in test_queries:
        print(f"\nUser: {query}")
        response = chatbot.get_response(query)
        print(f"Bot: {response['response']}")
        if response['action']:
            print(f"Action: {response['action']}")
