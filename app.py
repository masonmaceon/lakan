"""
Lakán DLSU-D — AI-Powered Campus Navigation System (`lakan_dlsud`)
Flask backend: map UI, campus pathways, DeepSeek chatbot, memo upload (RAG),
building detection (Roboflow hosted API), admin panel.

Key changes vs the original Railway/MySQL app:
  * PostgreSQL via DATABASE_URL through db.py (Neon / Render / local)
  * Leaked Roboflow keys removed — ROBOFLOW_API_KEY env var only
  * Dead PyTorch / old-SDK code paths removed
  * admin_login rewritten (single query, no password logging, hashed passwords)
  * upload_memo stores files in the DB and passes the memo id to the RAG processor
  * Campus geofence enforced server-side (see geofence.py)
"""

import base64
import hmac
import mimetypes
import os
from io import BytesIO

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, send_file, send_from_directory
from flask_cors import CORS
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

import db
from geofence import inside_campus

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

# ---- Database (PostgreSQL) ----
db.init_pool()

# ---- Roboflow ML detection (hosted API) ----
ROBOFLOW_API_KEY = os.getenv('ROBOFLOW_API_KEY', '')
MODEL_ID = os.getenv('ROBOFLOW_MODEL_ID', 'lakan-5ugrp/1')
# Detections below this confidence are dropped so the UI can say "not sure"
# instead of confidently guessing wrong (model was validated on a narrow set).
ROBOFLOW_MIN_CONFIDENCE = float(os.getenv('ROBOFLOW_MIN_CONFIDENCE', '0.40'))

print("✅ Roboflow HTTP API ready" if ROBOFLOW_API_KEY
      else "⚠️  ROBOFLOW_API_KEY not set — /detect-building disabled")

# ---- Chatbot ----
try:
    from chatbot import CampusChatbot
    chatbot = CampusChatbot()
    print("✅ Chatbot initialized")
except Exception as e:
    print(f"⚠️  Chatbot initialization error: {e}")
    chatbot = None


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def allowed_image_file(filename):
    """Check if image file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


# ==================== PAGES ====================

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/mobile')
def mobile_app():
    return render_template('mobile_app.html')


@app.route('/camera')
def camera():
    return render_template('camera.html')


@app.route('/admin')
def admin():
    return render_template('admin_upload.html')


@app.route('/pathway-collector')
def pathway_collector():
    return render_template('pathway_collector.html')


# ==================== ML BUILDING DETECTION (ROBOFLOW HOSTED API) ====================

@app.route('/detect-building', methods=['POST'])
def detect_building():
    print("📸 /detect-building endpoint called")

    if not ROBOFLOW_API_KEY:
        return jsonify({'success': False, 'error': 'Detection not configured (missing ROBOFLOW_API_KEY)'})

    if 'image' not in request.files:
        return jsonify({'success': False, 'error': 'No image provided'})

    file = request.files['image']
    if file.filename == '' or not allowed_image_file(file.filename):
        return jsonify({'success': False, 'error': 'Invalid file'})

    try:
        image_data = file.read()
        image_b64 = base64.b64encode(image_data).decode('utf-8')

        response = requests.post(
            f"https://detect.roboflow.com/{MODEL_ID}",
            params={"api_key": ROBOFLOW_API_KEY},
            data=image_b64,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )

        if response.status_code != 200:
            return jsonify({'success': False, 'error': f'Roboflow API error: {response.status_code}'})

        result = response.json()
        predictions = result.get('predictions', [])

        detection_list = [
            {
                'class_name': pred.get('class', 'Unknown'),
                'confidence': float(pred.get('confidence', 0)),
            }
            for pred in predictions
            if float(pred.get('confidence', 0)) >= ROBOFLOW_MIN_CONFIDENCE
        ]
        detection_list.sort(key=lambda d: d['confidence'], reverse=True)

        message = ''
        if not detection_list:
            message = ('No buildings detected in this image. '
                       'Try a clearer, closer shot of a single building.') if predictions \
                else 'No buildings detected in this image'

        print(f"✅ Detected {len(detection_list)} buildings "
              f"({len(predictions)} raw, threshold {ROBOFLOW_MIN_CONFIDENCE:.0%})")
        return jsonify({
            'success': True,
            'detections': detection_list,
            'count': len(detection_list),
            'message': message,
        })

    except Exception as e:
        print(f"❌ Detection error: {e}")
        return jsonify({'success': False, 'error': str(e)})


# ==================== DATABASE ROUTES ====================

@app.route('/get-all-links', methods=['GET'])
def get_all_links():
    """Get pathway connections from the database"""
    try:
        connections = db.query("SELECT * FROM pathway_connections")
        result = [{
            'pathway1': c['pathway1_id'],
            'pathway1_index': c['pathway1_point_index'],
            'pathway2': c['pathway2_id'],
            'pathway2_index': c['pathway2_point_index'],
            'type': c.get('connection_type', 'auto_detected'),
        } for c in connections]
        return jsonify(result)
    except Exception as e:
        print(f"Error loading connections: {e}")
        return jsonify([])


@app.route('/get-all-pathways', methods=['GET'])
def get_all_pathways():
    """Get all pathways with their points"""
    try:
        pathways = db.query("SELECT * FROM pathways")
        result = []
        for pathway in pathways:
            points = db.query("""
                SELECT latitude, longitude
                FROM pathway_points
                WHERE pathway_id = %s
                ORDER BY point_index
            """, (pathway['id'],))
            result.append({
                'id': pathway['id'],
                'name': pathway['name'],
                'type': pathway.get('pathway_type', 'pedestrian'),
                'surface': pathway.get('surface', 'concrete'),
                'width': float(pathway.get('width') or 2.0),
                'shaded': bool(pathway.get('is_shaded', False)),
                'accessible': bool(pathway.get('is_accessible', True)),
                'points': [[float(p['latitude']), float(p['longitude'])] for p in points],
            })
        return jsonify(result)
    except Exception as e:
        print(f"Error loading pathways: {e}")
        return jsonify([])


@app.route('/get-all-locations', methods=['GET'])
def get_all_locations():
    """Get all locations"""
    try:
        locations = db.query("SELECT * FROM locations")
        result = [{
            'id': loc['id'],
            'name': loc['name'],
            'type': loc.get('location_type', 'building'),
            'coordinates': [float(loc['latitude']), float(loc['longitude'])],
            'description': loc.get('description', ''),
        } for loc in locations]
        return jsonify(result)
    except Exception as e:
        print(f"Error loading locations: {e}")
        return jsonify([])


# ==================== CHATBOT ROUTES ====================

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chatbot queries"""
    try:
        data = request.get_json()
        message = data.get('message', '')
        user_location = data.get('userLocation', None)

        if not chatbot:
            return jsonify({
                'response': "Sorry, the chatbot is not available right now.",
                'destination': None,
            })

        response = chatbot.get_response(message, user_location=user_location)

        # 🎓 Geofence (server-side, authoritative): map features (routing AND
        # building reveals) require a verified location INSIDE the campus
        # bounding box. No location → ask for GPS; outside → decline.
        try:
            loc = (user_location or {})
            has_loc = loc.get('lat') is not None and loc.get('lng') is not None
            if response.get('action') in ('navigate', 'show_location'):
                if not has_loc:
                    response = {
                        'response': ("📍 Please turn on GPS first so Lakán can verify "
                                     "you're inside the DLSU-D campus — building "
                                     "locations and routes are on-campus features."),
                        'action': None,
                    }
                elif not inside_campus(loc.get('lat'), loc.get('lng')):
                    response = {
                        'response': ("🎓 Lakán's map and navigation features are available "
                                     "on-campus only — your location appears to be outside "
                                     "the DLSU-D campus. Come visit us! Animo!"),
                        'action': None,
                    }
        except Exception as e:
            print(f"⚠️ Geofence check skipped: {e}")

        return jsonify(response)

    except Exception as e:
        print(f"Chat error: {e}")
        return jsonify({'response': f"Error: {str(e)}", 'destination': None})


# ==================== ADMIN / PATHWAY ROUTES ====================

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    try:
        data = request.get_json() or {}
        email = (data.get('email') or '').strip()
        password = data.get('password') or ''

        if not email or not password:
            return jsonify({'success': False, 'error': 'Email and password are required.'})

        admin = db.query_one("SELECT id, name, password FROM admins WHERE email = %s", (email,))

        ok = False
        if admin and admin.get('password'):
            stored = admin['password']
            if stored.startswith(('pbkdf2:', 'scrypt:')):
                ok = check_password_hash(stored, password)
            else:
                # legacy plaintext row (e.g. migrated from old MySQL)
                ok = stored == password

        if ok:
            print(f"🔑 Admin login OK: {email}")
            return jsonify({'success': True, 'name': admin.get('name') or ''})

        print(f"🔑 Admin login failed: {email}")
        return jsonify({'success': False, 'error': 'Invalid email or password.'})

    except Exception as e:
        print(f"Admin login error: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/admin/create', methods=['POST'])
def admin_create():
    """Create (or update) an admin account with a hashed password.

    Allowed only when:
      * bootstrap: the admins table is still empty (fresh install), OR
      * the request carries X-Setup-Token matching the ADMIN_SETUP_TOKEN
        env var (set it temporarily in Render when you need this).
    """
    try:
        expected = os.getenv('ADMIN_SETUP_TOKEN', '')
        provided = request.headers.get('X-Setup-Token', '')
        token_ok = bool(expected) and hmac.compare_digest(expected, provided)

        if not token_ok:
            any_admin = db.query_one("SELECT id FROM admins LIMIT 1")
            if any_admin:
                return jsonify({'success': False,
                                'error': 'Not allowed. Set ADMIN_SETUP_TOKEN in the server env '
                                         'and send it as the X-Setup-Token header.'}), 403

        data = request.get_json() or {}
        email = (data.get('email') or '').strip().lower()
        password = data.get('password') or ''
        name = data.get('name') or ''

        if not email or len(password) < 8:
            return jsonify({'success': False,
                            'error': 'Valid email and a password of 8+ characters are required.'})

        rowcount = db.execute("""
            INSERT INTO admins (email, password, name)
            VALUES (%s, %s, %s)
            ON CONFLICT (email) DO UPDATE
                SET password = EXCLUDED.password, name = EXCLUDED.name
        """, (email, generate_password_hash(password), name))

        if rowcount == -1:
            return jsonify({'success': False, 'error': 'Database unavailable.'}), 503
        return jsonify({'success': True, 'message': f'Admin "{email}" saved.'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/upload-memo', methods=['POST'])
def upload_memo():
    try:
        if 'memo' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['memo']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not (allowed_file(file.filename) or allowed_image_file(file.filename)):
            return jsonify({'error': 'Only PDF/DOC/DOCX or PNG/JPG files allowed'}), 400

        filename = secure_filename(file.filename)

        # Strip extension for display title, replace underscores/dashes with spaces
        title = os.path.splitext(filename)[0].replace('_', ' ').replace('-', ' ')

        # Store the file bytes IN the database — free hosts have ephemeral
        # filesystems, so anything on disk vanishes on restart.
        file_bytes = file.read()

        conn_ok = True
        memo_id = None
        with db.get_conn() as conn:
            if conn is None:
                conn_ok = False
            else:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO memos (title, filename, content, file_data)
                        VALUES (%s, %s, %s, %s)
                        RETURNING id
                    """, (title, filename, '', file_bytes))
                    memo_id = cursor.fetchone()['id']

        if not conn_ok:
            return jsonify({'error': 'Database unavailable — memo not saved.'}), 503

        # Extract text for RAG (chunking + embeddings; keyword fallback)
        try:
            from rag_processor import process_uploaded_memo
            process_uploaded_memo(filename, file_bytes, memo_id=memo_id)
        except Exception as e:
            print(f"⚠️  RAG processing skipped: {e}")

        return jsonify({'message': f'Memo "{filename}" uploaded successfully!'})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/announcements', methods=['GET'])
def get_announcements():
    try:
        rows = db.query("""
            SELECT id, title, filename, uploaded_at
            FROM memos
            ORDER BY uploaded_at DESC
            LIMIT 3
        """)
        result = [{
            'id': row['id'],
            'title': row['title'],
            'filename': row['filename'],
            'uploaded_at': row['uploaded_at'].strftime('%b %d, %Y') if row.get('uploaded_at') else '',
        } for row in rows]
        return jsonify(result)
    except Exception as e:
        print(f"❌ Error loading announcements: {e}")
        return jsonify([])


@app.route('/uploads/memos/<path:filename>')
def serve_memo(filename):
    """Serve uploaded memo PDFs/images from the database (disk fallback for
    legacy rows uploaded before Phase 3)."""
    row = db.query_one("""
        SELECT file_data FROM memos
        WHERE filename = %s
        ORDER BY uploaded_at DESC
        LIMIT 1
    """, (filename,))
    data = row.get('file_data') if row else None
    if data is not None:
        mimetype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        return send_file(
            BytesIO(bytes(data)),
            mimetype=mimetype,
            download_name=filename,
            as_attachment=False,
        )
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route('/api/save-pathway', methods=['POST'])
def save_pathway():
    try:
        data = request.get_json()
        name = data.get('name', 'Unnamed Pathway')
        points = data.get('points', [])
        pathway_type = data.get('type', 'pedestrian')
        accessible = bool(data.get('accessible', True))

        if not points or len(points) < 2:
            return jsonify({'success': False, 'error': 'Need at least 2 points'})

        pathway_id = data.get('id', 'pathway_' + str(int(__import__('time').time())))

        with db.get_conn() as conn:
            if conn is None:
                return jsonify({'success': False, 'error': 'Database unavailable.'}), 503
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO pathways (id, name, pathway_type, is_accessible)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE
                        SET name = EXCLUDED.name, pathway_type = EXCLUDED.pathway_type,
                            is_accessible = EXCLUDED.is_accessible
                """, (pathway_id, name, pathway_type, accessible))

                # Replace points for re-saved pathways
                cursor.execute("DELETE FROM pathway_points WHERE pathway_id = %s", (pathway_id,))
                for i, point in enumerate(points):
                    cursor.execute("""
                        INSERT INTO pathway_points (pathway_id, point_index, latitude, longitude)
                        VALUES (%s, %s, %s, %s)
                    """, (pathway_id, i, point[0], point[1]))

        return jsonify({'success': True,
                        'message': f'Pathway "{name}" saved with {len(points)} points!'})

    except Exception as e:
        print(f"Error saving pathway: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


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

        rowcount = db.execute("""
            INSERT INTO locations (id, name, latitude, longitude, location_type)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE
                SET name = EXCLUDED.name,
                    latitude = EXCLUDED.latitude,
                    longitude = EXCLUDED.longitude,
                    location_type = EXCLUDED.location_type
        """, (loc_id, name, coords[0], coords[1], loc_type))

        if rowcount == -1:
            return jsonify({'success': False, 'error': 'Database unavailable.'}), 503
        return jsonify({'success': True, 'message': f'Location "{name}" saved!'})

    except Exception as e:
        print(f"Error saving location: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== STATIC FILES ====================

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files"""
    return send_from_directory('static', filename)


@app.route('/healthz', methods=['GET'])
def healthz():
    """Cheap endpoint for uptime pings (UptimeRobot) — no page render."""
    return jsonify({'status': 'ok', 'db': db.pool_is_up()})


# ==================== START SERVER ====================

if __name__ == '__main__':
    print("=" * 60)
    print("  🗺️  LAKÁN - CAMPUS NAVIGATION SYSTEM · DLSU-D")
    print("=" * 60)
    print("  Chatbot: ✅ Ready" if chatbot else "  Chatbot: ❌ Not loaded")
    print("  Database: ✅ Connected" if db.pool_is_up() else "  Database: ❌ Not connected")
    print("  ML Detection: ✅ Ready (Roboflow HTTP API)" if ROBOFLOW_API_KEY
          else "  ML Detection: ❌ ROBOFLOW_API_KEY not set")
    print("=" * 60)

    app.run(
        debug=os.getenv('FLASK_DEBUG', '0') == '1',
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
    )
