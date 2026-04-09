"""
Lakán Building Detection - Web Interface
Simple drag-and-drop interface for testing building recognition
"""

from flask import Flask, request, jsonify, render_template_string
from inference import get_model
import supervision as sv
import cv2
import os
import base64
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'test_uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Set your Roboflow API key
ROBOFLOW_API_KEY = os.getenv('ROBOFLOW_API_KEY', 'a7egLGQSh1aNH2WQs2xC')
os.environ['ROBOFLOW_API_KEY'] = ROBOFLOW_API_KEY

# Model configuration
MODEL_ID = "lakan-okc8g/7"  # Your Roboflow model ID

# Load model once at startup
print("🔄 Loading building detection model...")
try:
    model = get_model(model_id=MODEL_ID)
    print("✅ Model loaded successfully!")
except Exception as e:
    print(f"❌ Error loading model: {e}")
    model = None

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Lakán Building Detector</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        
        .container {
            background: white;
            border-radius: 20px;
            padding: 40px;
            max-width: 800px;
            width: 100%;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        
        h1 {
            color: #006341;
            text-align: center;
            margin-bottom: 10px;
        }
        
        .subtitle {
            text-align: center;
            color: #666;
            margin-bottom: 30px;
        }
        
        .upload-area {
            border: 3px dashed #006341;
            border-radius: 15px;
            padding: 60px 20px;
            text-align: center;
            background: #f8f9fa;
            cursor: pointer;
            transition: all 0.3s;
            margin-bottom: 20px;
        }
        
        .upload-area:hover {
            background: #e9ecef;
            border-color: #004d30;
        }
        
        .upload-area.dragover {
            background: #d4edda;
            border-color: #28a745;
        }
        
        .upload-icon {
            font-size: 60px;
            margin-bottom: 20px;
        }
        
        .upload-text {
            font-size: 18px;
            color: #495057;
            margin-bottom: 10px;
        }
        
        .upload-hint {
            font-size: 14px;
            color: #6c757d;
        }
        
        input[type="file"] {
            display: none;
        }
        
        button {
            background: #006341;
            color: white;
            border: none;
            padding: 15px 40px;
            border-radius: 10px;
            font-size: 16px;
            cursor: pointer;
            width: 100%;
            margin-top: 20px;
            transition: background 0.3s;
        }
        
        button:hover {
            background: #004d30;
        }
        
        button:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        
        .preview {
            margin-top: 20px;
            display: none;
        }
        
        .preview img {
            max-width: 100%;
            border-radius: 10px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }
        
        .results {
            margin-top: 30px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
            display: none;
        }
        
        .result-item {
            padding: 15px;
            background: white;
            margin-bottom: 10px;
            border-radius: 8px;
            border-left: 4px solid #006341;
        }
        
        .building-name {
            font-size: 20px;
            font-weight: bold;
            color: #006341;
        }
        
        .confidence {
            color: #28a745;
            font-size: 14px;
            margin-top: 5px;
        }
        
        .loading {
            text-align: center;
            padding: 20px;
            display: none;
        }
        
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #006341;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            animation: spin 1s linear infinite;
            margin: 0 auto;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .error {
            background: #f8d7da;
            color: #721c24;
            padding: 15px;
            border-radius: 8px;
            margin-top: 20px;
            display: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🏛️ Lakán Building Detector</h1>
        <p class="subtitle">DLSU-Dasmariñas Campus Navigation System</p>
        
        <div class="upload-area" id="uploadArea">
            <div class="upload-icon">📸</div>
            <div class="upload-text">Drag & Drop Building Image Here</div>
            <div class="upload-hint">or click to browse (JPG, PNG)</div>
            <input type="file" id="fileInput" accept="image/*">
        </div>
        
        <div class="preview" id="preview">
            <img id="previewImg" src="" alt="Preview">
        </div>
        
        <button id="detectBtn" disabled>🔍 Detect Building</button>
        
        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p style="margin-top: 15px;">Detecting building...</p>
        </div>
        
        <div class="results" id="results"></div>
        
        <div class="error" id="error"></div>
    </div>
    
    <script>
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        const preview = document.getElementById('preview');
        const previewImg = document.getElementById('previewImg');
        const detectBtn = document.getElementById('detectBtn');
        const loading = document.getElementById('loading');
        const results = document.getElementById('results');
        const error = document.getElementById('error');
        
        let selectedFile = null;
        
        // Click to upload
        uploadArea.addEventListener('click', () => fileInput.click());
        
        // Drag and drop
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });
        
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });
        
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            const file = e.dataTransfer.files[0];
            handleFile(file);
        });
        
        fileInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            handleFile(file);
        });
        
        function handleFile(file) {
            if (!file || !file.type.startsWith('image/')) {
                showError('Please select an image file (JPG or PNG)');
                return;
            }
            
            selectedFile = file;
            
            // Show preview
            const reader = new FileReader();
            reader.onload = (e) => {
                previewImg.src = e.target.result;
                preview.style.display = 'block';
                detectBtn.disabled = false;
                results.style.display = 'none';
                error.style.display = 'none';
            };
            reader.readAsDataURL(file);
        }
        
        detectBtn.addEventListener('click', async () => {
            if (!selectedFile) return;
            
            const formData = new FormData();
            formData.append('image', selectedFile);
            
            loading.style.display = 'block';
            results.style.display = 'none';
            error.style.display = 'none';
            detectBtn.disabled = true;
            
            try {
                const response = await fetch('/detect', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                loading.style.display = 'none';
                detectBtn.disabled = false;
                
                if (data.success) {
                    showResults(data);
                } else {
                    showError(data.error || 'Detection failed');
                }
            } catch (err) {
                loading.style.display = 'none';
                detectBtn.disabled = false;
                showError('Network error: ' + err.message);
            }
        });
        
        function showResults(data) {
            results.innerHTML = '';
            
            if (data.detections.length === 0) {
                results.innerHTML = '<p style="text-align: center; color: #666;">No buildings detected. Try a different image!</p>';
            } else {
                data.detections.forEach(det => {
                    const item = document.createElement('div');
                    item.className = 'result-item';
                    item.innerHTML = `
                        <div class="building-name">${det.class_name}</div>
                        <div class="confidence">Confidence: ${(det.confidence * 100).toFixed(1)}%</div>
                    `;
                    results.appendChild(item);
                });
            }
            
            results.style.display = 'block';
        }
        
        function showError(message) {
            error.textContent = message;
            error.style.display = 'block';
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/detect', methods=['POST'])
def detect():
    print("🔍 /detect endpoint called")
    
    if 'image' not in request.files:
        return jsonify({'success': False, 'error': 'No image provided'})
    
    file = request.files['image']
    
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'})
    
    if not allowed_file(file.filename):
        return jsonify({'success': False, 'error': 'Invalid file type. Use JPG or PNG'})
    
    try:
        # Save uploaded file
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        print(f"💾 Saved file: {filepath}")
        
        # Read image
        image = cv2.imread(filepath)
        print(f"📷 Image loaded: {image.shape if image is not None else 'Failed'}")
        
        if image is None:
            return jsonify({'success': False, 'error': 'Could not read image'})
        
        # Run inference
        if model is None:
            return jsonify({'success': False, 'error': 'Model not loaded. Check API key and model ID'})
        
        print("🤖 Running model inference...")
        results = model.infer(image)[0]
        print("✅ Inference complete!")
        
        # Debug: Print raw results structure
        print(f"🔍 Results type: {type(results)}")
        print(f"🔍 Results keys: {results.__dict__.keys() if hasattr(results, '__dict__') else 'No __dict__'}")
        
        # Parse results manually
        detection_list = []
        
        # Check if results has predictions
        if hasattr(results, 'predictions') and results.predictions:
            print(f"🔍 Found {len(results.predictions)} predictions")
            
            for pred in results.predictions:
                # Predictions are Pydantic objects, access attributes directly
                print(f"🔍 Prediction type: {type(pred)}")
                print(f"🔍 Prediction attributes: {dir(pred)}")
                
                # Extract class name - try different attribute names
                class_name = 'Unknown'
                if hasattr(pred, 'class_name'):
                    class_name = pred.class_name
                elif hasattr(pred, 'top'):
                    class_name = pred.top
                else:
                    # Try to get 'class' attribute using getattr (since 'class' is reserved)
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
            print("❌ No predictions found in results")
            return jsonify({
                'success': True,
                'detections': [],
                'count': 0,
                'message': 'No buildings detected in this image'
            })
        
        # Clean up
        os.remove(filepath)
        
        return jsonify({
            'success': True,
            'detections': detection_list,
            'count': len(detection_list)
        })
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"❌ ERROR in /detect endpoint:")
        print(error_details)
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    print("=" * 60)
    print("  🏛️  LAKÁN BUILDING DETECTOR")
    print("=" * 60)
    print(f"  Model: {MODEL_ID}")
    print(f"  API Key: {'✅ Set' if ROBOFLOW_API_KEY != 'YOUR_API_KEY_HERE' else '❌ Not set'}")
    print("=" * 60)
    print("\n🌐 Starting web interface...")
    print("📍 Open in browser: http://localhost:5001\n")
    
    app.run(debug=True, port=5001)
