"""
Lakán - AI-Powered Campus Navigation System
Flask Backend - Complete Integration with ML Building Detection
"""

from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
from pathlib import Path
import json
import base64
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv
from mysql.connector import pooling
import mysql.connector
import requests

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Configuration
UPLOAD_FOLDER = 'uploads/memos'
TEMP_UPLOAD_FOLDER = 'temp_uploads'
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TEMP_UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# MySQL Connection Pool
try:
    db_pool = pooling.MySQLConnectionPool(
        pool_name="lakan_pool",
        pool_size=5,
        host=os.getenv('MYSQL_HOST', 'localhost'),
        port=int(os.getenv('MYSQL_PORT', 3306)),
        user=os.getenv('MYSQL_USER', 'root'),
        password=os.getenv('MYSQL_PASSWORD', ''),
        database=os.getenv('MYSQL_DATABASE', 'lakan_db')
    )
    print("✅ MySQL connection pool created")
except Exception as e:
    print(f"⚠️ MySQL connection error: {e}")
    db_pool = None

def get_db_connection():
    """Get a connection from the pool"""
    try:
        return db_pool.get_connection()
    except Exception as e:
        print(f"Error getting database connection: {e}")
        return None

# Roboflow ML Detection Model Setup
ROBOFLOW_API_KEY = os.getenv('ROBOFLOW_API_KEY', 'a7egLGQSh1aNH2WQs2xC')
os.environ['ROBOFLOW_API_KEY'] = ROBOFLOW_API_KEY
MODEL_ID = "lakan-okc8g/7"

print("✅ Roboflow HTTP API ready")

# Import your modules
try:
    from chatbot import CampusChatbot
    from rag_processor import process_uploaded_memo, query_memos
    chatbot = CampusChatbot()
    print("✅ Chatbot initialized")
except Exception as e:
    print(f"⚠️  Chatbot initialization error: {e}")
    chatbot = None

# Building Recognition Model (Old PyTorch - keep for backup)
building_model = None
building_classes = None

def load_building_recognition_model():
    """Load the trained PyTorch building recognition model"""
    global building_model, building_classes
    
    if building_model is not None:
        return True
    
    try:
        model_path = 'building_recognizer.pth'
        classes_path = 'building_recognizer_classes.json'
        
        if not os.path.exists(model_path):
            print(f"⚠️  Model not found: {model_path}")
            return False
        
        # Load classes
        with open(classes_path, 'r') as f:
            building_classes = json.load(f)
        
        # Load model
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        building_model = torch.load(model_path, map_location=device)
        building_model.eval()
        
        print(f"✅ Building recognition model loaded ({len(building_classes)} classes)")
        return True
        
    except Exception as e:
        print(f"❌ Error loading model: {e}")
        return False

def predict_building(image_data):
    """Predict building from image (Old PyTorch model)"""
    if not load_building_recognition_model():
        return None
    
    try:
        from torchvision import transforms
        
        # Preprocess image
        transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                               std=[0.229, 0.224, 0.225])
        ])
        
        # Convert to PIL Image
        image = Image.open(BytesIO(image_data)).convert('RGB')
        image_tensor = transform(image).unsqueeze(0)
        
        # Predict
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        image_tensor = image_tensor.to(device)
        
        with torch.no_grad():
            outputs = building_model(image_tensor)
            probabilities = torch.nn.functional.softmax(outputs, dim=1)
            confidence, predicted = torch.max(probabilities, 1)
        
        predicted_class = building_classes[predicted.item()]
        confidence_score = confidence.item()
        
        # Get top 3 predictions
        top3_prob, top3_idx = torch.topk(probabilities, 3)
        top3_predictions = [
            {
                'building': building_classes[idx.item()],
                'confidence': prob.item()
            }
            for prob, idx in zip(top3_prob[0], top3_idx[0])
        ]
        
        return {
            'building': predicted_class,
            'confidence': confidence_score,
            'top_3': top3_predictions
        }
        
    except Exception as e:
        print(f"Prediction error: {e}")
        return None

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_image_file(filename):
    """Check if image file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

# Campus Data (from your Firestore export)
CAMPUS_DATA = {
    "buildings": {
        "Admin": {
            "name": "Ayuntamiento de Gonzales Building",
            "type": "Administrative",
            "coordinates": [14.320744, 120.962984]
        },
        "CBAA": {
            "name": "College of Business Administration and Accountancy",
            "type": "Academic",
            "coordinates": [14.323751375633886, 120.95819680416969]
        },
        "CEAT": {
            "name": "College of Engineering, Architecture and Technology",
            "type": "Academic",
            "coordinates": [14.3217, 120.9636]
        },
        "CTH": {
            "name": "Candido Tirona Hall (High School)",
            "type": "Academic",
            "coordinates": [14.323247310827597, 120.95951498463104]
        },
        "CTHM": {
            "name": "College of Tourism and Hospitality Management",
            "type": "Academic",
            "coordinates": [14.32163, 120.962651]
        },
        "JFH": {
            "name": "Julian Felipe Hall",
            "type": "Academic",
            "coordinates": [14.321201, 120.962876]
        },
        "Library": {
            "name": "Aklatang Emilio Aguinaldo",
            "type": "Service",
            "coordinates": [14.320715, 120.961795]
        },
        "Square": {
            "name": "Food Square",
            "type": "Service",
            "coordinates": [14.321522543715924, 120.96011706908381]
        }
    }
}

# ==================== ROUTES ====================

@app.route('/')
def index():
    """Serve main page"""
    return render_template('index.html')

@app.route('/mobile')
def mobile_app():
    """Serve new mobile app with camera integration"""
    return render_template('mobile_app.html')

@app.route('/camera')
def camera():
    """Serve camera page"""
    return render_template('camera.html')

@app.route('/admin')
def admin():
    """Serve admin page"""
    return render_template('admin_upload.html')

@app.route('/pathway-collector')
def pathway_collector():
    """Serve pathway coordinate collection tool"""
    return render_template('pathway_collector.html')

# ==================== ML BUILDING DETECTION (NEW ROBOFLOW) ====================

@app.route('/detect-building', methods=['POST'])
def detect_building():
    print("📸 /detect-building endpoint called")

    if 'image' not in request.files:
        return jsonify({'success': False, 'error': 'No image provided'})

    file = request.files['image']
    if file.filename == '' or not allowed_image_file(file.filename):
        return jsonify({'success': False, 'error': 'Invalid file'})

    try:
        # Convert image to base64
        image_data = file.read()
        image_b64 = base64.b64encode(image_data).decode('utf-8')

        # Call Roboflow HTTP API
        response = requests.post(
            f"https://detect.roboflow.com/{MODEL_ID}",
            params={"api_key": ROBOFLOW_API_KEY},
            data=image_b64,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        if response.status_code != 200:
            return jsonify({'success': False, 'error': f'Roboflow API error: {response.status_code}'})

        result = response.json()
        predictions = result.get('predictions', [])

        detection_list = [
            {
                'class_name': pred.get('class', 'Unknown'),
                'confidence': float(pred.get('confidence', 0))
            }
            for pred in predictions
        ]

        print(f"✅ Detected {len(detection_list)} buildings")
        return jsonify({
            'success': True,
            'detections': detection_list,
            'count': len(detection_list),
            'message': 'No buildings detected' if not detection_list else ''
        })

    except Exception as e:
        print(f"❌ Detection error: {e}")
        return jsonify({'success': False, 'error': str(e)})
    
    """
    Building detection endpoint for camera feature
    Uses Roboflow ML model to identify buildings from photos
    """
    print("📸 /detect-building endpoint called")
    
    if 'image' not in request.files:
        return jsonify({'success': False, 'error': 'No image provided'})
    
    file = request.files['image']
    
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'})
    
    if not allowed_image_file(file.filename):
        return jsonify({'success': False, 'error': 'Invalid file type. Use JPG or PNG'})
    
    try:
        # Save uploaded file
        filename = secure_filename(file.filename)
        filepath = os.path.join(TEMP_UPLOAD_FOLDER, filename)
        file.save(filepath)
        print(f"💾 Saved file: {filepath}")
        
        # Read image
        image = cv2.imread(filepath)
        print(f"📷 Image loaded: {image.shape if image is not None else 'Failed'}")
        
        if image is None:
            return jsonify({'success': False, 'error': 'Could not read image'})
        
        # Run inference
        if detection_model is None:
            return jsonify({'success': False, 'error': 'Model not loaded. Check API key and model ID'})
        
        print("🤖 Running Roboflow model inference...")
        results = detection_model.infer(image)[0]
        print("✅ Inference complete!")
        
        # Parse results (Pydantic objects from Roboflow)
        detection_list = []
        
        if hasattr(results, 'predictions') and results.predictions:
            print(f"🔍 Found {len(results.predictions)} predictions")
            
            for pred in results.predictions:
                # Extract class name
                class_name = 'Unknown'
                if hasattr(pred, 'class_name'):
                    class_name = pred.class_name
                elif hasattr(pred, 'top'):
                    class_name = pred.top
                else:
                    class_name = getattr(pred, 'class', 'Unknown')
                
                # Extract confidence
                confidence = 0.0
                if hasattr(pred, 'confidence'):
                    confidence = pred.confidence
                
                detection_list.append({
                    'class_name': class_name,
                    'confidence': float(confidence)
                })
                
                print(f"✅ Detected: {class_name} ({confidence:.1%})")
        else:
            print("❌ No predictions found")
        
        # Clean up
        os.remove(filepath)
        
        if len(detection_list) == 0:
            return jsonify({
                'success': True,
                'detections': [],
                'count': 0,
                'message': 'No buildings detected in this image'
            })
        
        return jsonify({
            'success': True,
            'detections': detection_list,
            'count': len(detection_list)
        })
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"❌ ERROR in /detect-building endpoint:")
        print(error_details)
        return jsonify({'success': False, 'error': str(e)})

# ==================== MYSQL DATABASE ROUTES ====================

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
                'type': conn_data.get('connection_type', 'auto_detected')
            })
        
        conn.close()
        return jsonify(result)
        
    except Exception as e:
        print(f"Error loading connections from MySQL: {e}")
        return jsonify([])

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
                'type': pathway.get('pathway_type', 'pedestrian'),
                'surface': pathway.get('surface', 'concrete'),
                'width': float(pathway.get('width', 2.0)),
                'shaded': bool(pathway.get('is_shaded', 0)),
                'accessible': bool(pathway.get('is_accessible', 1)),
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
                'type': loc.get('location_type', 'building'),
                'coordinates': [float(loc['latitude']), float(loc['longitude'])],
                'description': loc.get('description', '')
            })
        
        conn.close()
        return jsonify(result)
        
    except Exception as e:
        print(f"Error loading locations from MySQL: {e}")
        return jsonify([])

# ==================== CHATBOT ROUTES ====================

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chatbot queries"""
    try:
        data = request.get_json()
        message = data.get('message', '')
        
        if not chatbot:
            return jsonify({
                'response': "Sorry, the chatbot is not available right now.",
                'destination': None
            })
        
        response = chatbot.get_response(message)
        return jsonify(response)
        
    except Exception as e:
        print(f"Chat error: {e}")
        return jsonify({
            'response': f"Error: {str(e)}",
            'destination': None
        })

# ==================== ADMIN/PATHWAY ROUTES ====================

@app.route('/api/save-pathway', methods=['POST'])
def save_pathway():
    try:
        data = request.get_json()
        name = data.get('name', 'Unnamed Pathway')
        points = data.get('points', [])
        pathway_type = data.get('type', 'pedestrian')
        accessible = data.get('accessible', True)

        if not points or len(points) < 2:
            return jsonify({'success': False, 'error': 'Need at least 2 points'})

        conn = get_db_connection()
        cursor = conn.cursor()

        pathway_id = data.get('id', 'pathway_' + str(int(__import__('time').time())))
        cursor.execute("""
            INSERT INTO pathways (id, name, pathway_type, is_accessible) 
            VALUES (%s, %s, %s, %s)
        """, (pathway_id, name, pathway_type, int(accessible)))

        for i, point in enumerate(points):
            cursor.execute("""
                INSERT INTO pathway_points (pathway_id, point_index, latitude, longitude)
                VALUES (%s, %s, %s, %s)
            """, (pathway_id, i, point[0], point[1]))

        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': f'Pathway "{name}" saved with {len(points)} points!'})

    except Exception as e:
        print(f"Error saving pathway: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/save-location', methods=['POST'])
def save_location():
    try:
        data = request.get_json()
        loc_id = data.get('id', '')
        name = data.get('name', '')
        coords = data.get('coordinates', [0, 0])
        loc_type = data.get('type', 'building')

        if not loc_id or not name:
            return jsonify({'success': False, 'error': 'ID and name are required'})

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO locations (id, name, latitude, longitude, location_type)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE name=%s, latitude=%s, longitude=%s, location_type=%s
        """, (loc_id, name, coords[0], coords[1], loc_type,
              name, coords[0], coords[1], loc_type))

        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': f'Location "{name}" saved!'})

    except Exception as e:
        print(f"Error saving location: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ==================== STATIC FILES ====================

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files"""
    return send_from_directory('static', filename)

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    try:
        data = request.get_json()
        email = data.get('email', '')
        password = data.get('password', '')
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM admins WHERE email = %s AND password = %s", (email, password))
        admin = cursor.fetchone()
        cursor.execute("SELECT * FROM admins WHERE email = %s AND password = %s", (email, password))
        admin = cursor.fetchone()
        print(f"🔍 Login: email={email} password={password} result={admin}")
        conn.close()
        cursor.execute("SELECT DATABASE()")
        db_name = cursor.fetchone()
        print(f"🔍 Connected to database: {db_name}")
        cursor.execute("SELECT COUNT(*) as cnt FROM admins")
        count = cursor.fetchone()
        print(f"🔍 Admins count: {count}")
        cursor.execute("SELECT * FROM admins WHERE email = %s AND password = %s", (email, password))
        admin = cursor.fetchone()
        print(f"🔍 Login result: {admin}")
        if admin:
            return jsonify({'success': True, 'name': admin.get('name', '')})
        else:
            return jsonify({'success': False, 'error': 'Invalid email or password.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
    
@app.route('/admin/upload-memo', methods=['POST'])
def upload_memo():
    try:
        if 'memo' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['memo']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not allowed_file(file.filename):
            return jsonify({'error': 'Only PDF files allowed'}), 400

        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        # Strip extension for display title, replace underscores/dashes with spaces
        title = os.path.splitext(filename)[0].replace('_', ' ').replace('-', ' ')

        # Save memo metadata to DB
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS memos (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        title VARCHAR(255) NOT NULL,
                        filename VARCHAR(255) NOT NULL,
                        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cursor.execute(
                    "INSERT INTO memos (title, filename) VALUES (%s, %s)",
                    (title, filename)
                )
                conn.commit()
            finally:
                conn.close()

        # Process for RAG if available
        try:
            process_uploaded_memo(filepath)
        except Exception:
            pass

        return jsonify({'message': f'Memo "{filename}" uploaded successfully!'})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/announcements', methods=['GET'])
def get_announcements():
    try:
        conn = get_db_connection()
        if not conn:
            print("❌ No DB connection")
            return jsonify([])

        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT DATABASE()")
        print("📦 Connected DB:", cursor.fetchone())
        cursor.execute("SELECT COUNT(*) as cnt FROM memos")
        print("📊 Memos count:", cursor.fetchone())
        cursor.execute("SELECT id, title, filename, uploaded_at FROM memos ORDER BY uploaded_at DESC LIMIT 3")
        rows = cursor.fetchall()
        print(f"✅ Memos found: {rows}")
        conn.close()

        result = []
        for row in rows:
            result.append({
                'id': row['id'],
                'title': row['title'],
                'filename': row['filename'],
                'uploaded_at': row['uploaded_at'].strftime('%b %d, %Y') if row['uploaded_at'] else ''
            })

        print(f"✅ Result: {result}")
        return jsonify(result)

    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify([])

@app.route('/uploads/memos/<path:filename>')
def serve_memo(filename):
    """Serve uploaded memo PDFs"""
    return send_from_directory(UPLOAD_FOLDER, filename)

# ==================== START SERVER ====================

if __name__ == '__main__':
    print("=" * 60)
    print("  🗺️  LAKÁN - CAMPUS NAVIGATION SYSTEM")
    print("=" * 60)
    print("  Chatbot: ✅ Ready" if chatbot else "  Chatbot: ❌ Not loaded")
    print("  Database: ✅ Connected" if db_pool else "  Database: ❌ Not connected")
    print("  ML Detection: ✅ Ready (Roboflow HTTP API)")    
    print("=" * 60)
    print("\n🚀 Starting Flask server...")
    print("📍 Main app: http://localhost:5000")
    print("📱 Mobile app: http://localhost:5000/mobile")
    print("\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
