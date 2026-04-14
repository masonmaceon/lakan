"""
RAG Processor - Extracts text from uploaded PDFs and stores in DB
so the chatbot can answer questions about memo contents.
"""

import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    try:
        return mysql.connector.connect(
            host=os.getenv('MYSQL_HOST', 'localhost'),
            port=int(os.getenv('MYSQL_PORT', 3306)),
            user=os.getenv('MYSQL_USER', 'root'),
            password=os.getenv('MYSQL_PASSWORD', ''),
            database=os.getenv('MYSQL_DATABASE', 'lakan_db')
        )
    except Exception as e:
        print(f"⚠️ DB connection error: {e}")
        return None


def extract_text_from_pdf(filepath):
    """Extract plain text from a PDF file"""
    try:
        import pypdf
        text = ""
        with open(filepath, 'rb') as f:
            reader = pypdf.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() or ""
        return text.strip()
    except ImportError:
        # Fallback to PyPDF2 if pypdf not available
        try:
            import PyPDF2
            text = ""
            with open(filepath, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text += page.extract_text() or ""
            return text.strip()
        except Exception as e:
            print(f"⚠️ PDF extraction error: {e}")
            return ""
    except Exception as e:
        print(f"⚠️ PDF extraction error: {e}")
        return ""


def process_uploaded_memo(filepath):
    """Extract text from PDF and store in memos table content column"""
    try:
        filename = os.path.basename(filepath)
        ext = filename.rsplit('.', 1)[-1].lower()

        # Only process text-based files
        if ext not in ('pdf', 'doc', 'docx'):
            print(f"⏭️ Skipping text extraction for {filename} (image file)")
            return {"success": True, "message": "Image file, no text extracted"}

        print(f"📄 Extracting text from {filename}...")
        text = extract_text_from_pdf(filepath)

        if not text:
            print(f"⚠️ No text extracted from {filename}")
            return {"success": False, "message": "No text could be extracted"}

        # Save to DB
        conn = get_db_connection()
        if not conn:
            return {"success": False, "message": "DB connection failed"}

        cursor = conn.cursor()
        cursor.execute(
            "UPDATE memos SET content = %s WHERE filename = %s",
            (text[:10000], filename)  # cap at 10k chars
        )
        conn.commit()
        conn.close()

        print(f"✅ Stored {len(text)} chars of text for {filename}")
        return {"success": True, "message": f"Extracted {len(text)} characters"}

    except Exception as e:
        print(f"❌ RAG processor error: {e}")
        return {"success": False, "message": str(e)}


def query_memos(query):
    """Simple keyword search across memo contents"""
    try:
        conn = get_db_connection()
        if not conn:
            return []

        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT title, content, uploaded_at
            FROM memos
            WHERE content LIKE %s AND content != ''
            ORDER BY uploaded_at DESC
            LIMIT 3
        """, (f"%{query}%",))
        rows = cursor.fetchall()
        conn.close()
        return rows

    except Exception as e:
        print(f"⚠️ query_memos error: {e}")
        return []
