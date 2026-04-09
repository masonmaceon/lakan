# 🚀 LAKÁN - SETUP GUIDE FOR TESTING

## 📁 File Structure You Need:

```
Lakán/
├── app.py                          ← Download new version
├── chatbot.py                      ← You already have this ✅
├── rag_processor.py                ← You already have this ✅
├── campus_navigation.js            ← You already have this ✅
├── .env                            ← CREATE THIS (see below)
├── requirements.txt                ← You already have this ✅
│
├── templates/
│   ├── index.html                  ← You already have this ✅
│   ├── camera.html                 ← Download new file
│   └── admin_upload.html           ← You already have this ✅
│
├── static/
│   ├── css/
│   │   └── style.css               ← You already have this ✅
│   └── js/
│       ├── campus_navigation.js    ← Move here from root
│       ├── map_controller.js       ← Move here from root
│       └── main_mobile.js          ← Move here from root
│
├── uploads/
│   └── memos/                      ← Will be created automatically
│
└── dataset/                        ← Your 8,000 images (being collected)
    ├── train/
    ├── valid/
    └── test/
```

---

## 🔧 STEP-BY-STEP SETUP:

### **Step 1: Create .env File**

Create a file named `.env` in your `Lakán` folder:

```env
# DeepSeek API Key
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# Optional: Flask settings
FLASK_ENV=development
FLASK_DEBUG=True
```

**Get DeepSeek API Key:**
1. Go to: https://platform.deepseek.com/
2. Sign up / Login
3. Go to API Keys section
4. Create new key
5. Copy and paste into `.env` file

---

### **Step 2: Organize Your Files**

#### **Move JavaScript files to static/js:**

```bash
# In your Lakán folder
mkdir -p static/js
mkdir -p static/css

# Move JS files
move campus_navigation.js static\js\
move map_controller.js static\js\
move main_mobile.js static\js\

# Move CSS
move style.css static\css\
```

#### **Move HTML files to templates:**

```bash
mkdir templates

# Move HTML files
move index.html templates\
move admin_upload.html templates\
move camera.html templates\  # Download this new file first!
```

---

### **Step 3: Update index.html Script Paths**

Open `templates/index.html` and find these lines near the bottom:

**Change FROM:**
```html
<script src="{{ url_for('static', filename='js/campus_navigation.js') }}"></script>
<script src="{{ url_for('static', filename='js/map_controller.js') }}"></script>
<script src="{{ url_for('static', filename='js/main_mobile.js') }}"></script>
```

**TO:**
```html
<script src="/static/js/campus_navigation.js"></script>
<script src="/static/js/map_controller.js"></script>
<script src="/static/js/main_mobile.js"></script>
```

---

### **Step 4: Install Dependencies**

```bash
pip install flask flask-cors python-dotenv requests PyPDF2 sentence-transformers torch torchvision pillow
```

Or use your requirements.txt:

```bash
pip install -r requirements.txt
```

---

### **Step 5: Test Your Setup**

#### **Quick Test - Check if everything loads:**

```bash
cd C:\Users\Adam\dev\udb\Lakán
python app.py
```

You should see:
```
============================================================
  🗺️  LAKÁN - CAMPUS NAVIGATION SYSTEM
============================================================
  Chatbot: ✅ Ready
  GPU: ✅ Available
============================================================

 * Running on http://0.0.0.0:5000
```

---

### **Step 6: Open in Browser**

Open your browser and go to:

```
http://localhost:5000
```

You should see your navigation interface! 🎉

---

### **Step 7: Test Each Feature**

#### **Test 1: Chatbot**
1. Click on chat overlay
2. Type: "How do I get to JFH?"
3. Should get DeepSeek response

#### **Test 2: Camera** (after you have trained model)
1. Go to: `http://localhost:5000/camera`
2. Allow camera permissions
3. Point at building
4. Take photo
5. Should recognize building

#### **Test 3: Admin Upload**
1. Go to: `http://localhost:5000/admin`
2. Upload a PDF memo
3. Should process successfully
4. Test chatbot with question about the memo

---

## ⚠️ COMMON ISSUES:

### **Issue 1: "Module not found: chatbot"**
**Fix:** Make sure `chatbot.py` is in the same folder as `app.py`

### **Issue 2: "Template not found: index.html"**
**Fix:** Make sure all HTML files are in `templates/` folder

### **Issue 3: "DeepSeek API error"**
**Fix:** Check your `.env` file has the correct API key

### **Issue 4: "Building recognition not working"**
**Fix:** Wait until your team finishes collecting images and you train the model

### **Issue 5: JavaScript files not loading**
**Fix:** Make sure they're in `static/js/` and paths are correct in HTML

---

## 📊 What Works Right Now:

✅ **Map display** (Leaflet.js)
✅ **Chatbot** (DeepSeek API)
✅ **RAG upload** (PDF processing)
✅ **GPS tracking**
✅ **Route visualization**

⏳ **Building recognition** (waiting for images + training)

---

## 🎯 Next Steps After Setup:

1. **Test chatbot** - Make sure DeepSeek responds
2. **Upload test PDF** - Test RAG system
3. **Wait for team** - Let them finish collecting 8,000 images
4. **Train model** - Run `python train_roboflow.py`
5. **Test camera** - Test building recognition
6. **Polish UI** - Make it look perfect for demo
7. **Prepare for defense** - Practice demo flow

---

## 🔥 Quick Start Commands:

```bash
# 1. Navigate to project
cd C:\Users\Adam\dev\udb\Lakán

# 2. Activate virtual environment (if using one)
# venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create .env file with DeepSeek API key

# 5. Run app
python app.py

# 6. Open browser to http://localhost:5000
```

---

## 📝 Files to Download:

1. **app.py** - New version (replaces old one)
2. **camera.html** - New file for building recognition
3. **.env** - Create this yourself with your API key

---

## 💡 Pro Tips:

- Keep Terminal open to see logs
- Use `Ctrl+C` to stop server
- Refresh browser after code changes
- Check Terminal for errors
- Test on mobile browser too! (use your IP: `http://192.168.x.x:5000`)

---

**Ready to test? Download the files and follow Step 1!** 🚀
