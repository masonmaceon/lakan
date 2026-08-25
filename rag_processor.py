"""
RAG Processor (lakan_dlsud) — the real RAG pipeline.

Upload flow (process_uploaded_memo):
    PDF bytes → extract text → chunk (~800 chars, overlap) → embed each
    chunk (Gemini text-embedding-004, free tier, via embeddings.py) →
    store in memo_chunks with the vector. Whole text (≤10k) is still kept
    in memos.content as display/fallback. Images are stored, not processed.

Query flow (retrieve_relevant_chunks):
    question → embed → cosine similarity vs stored chunk embeddings →
    top-k chunks into the chatbot prompt.
    Fallbacks: no key / no vectors → keyword scoring over chunks →
    else latest memo texts (v1 behavior).

No pgvector needed — embeddings live as double precision[] and cosine is
computed in Python (trivial at hundreds of chunks).
"""

import math
import re
from io import BytesIO

from dotenv import load_dotenv

import db

load_dotenv()

CHUNK_SIZE = 800      # characters
CHUNK_OVERLAP = 100
TOP_K = 4             # chunks injected into the chat prompt
KEYWORD_SCAN_LIMIT = 500  # newest chunks scanned for fallback scoring


# ==================== extraction ====================

def extract_text_from_pdf_bytes(file_bytes):
    """Extract plain text from PDF bytes (in-memory — no disk needed)."""
    try:
        import pypdf
        reader = pypdf.PdfReader(BytesIO(file_bytes))
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text.strip()
    except Exception as e:
        print(f"⚠️ PDF extraction error: {e}")
        return ""


def extract_text_from_pdf(filepath):
    """Extract plain text from a PDF file (legacy helper)."""
    try:
        with open(filepath, 'rb') as f:
            return extract_text_from_pdf_bytes(f.read())
    except Exception as e:
        print(f"⚠️ PDF extraction error: {e}")
        return ""


# ==================== chunking ====================

def chunk_text(text, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """Split text into overlapping chunks, preferring sentence boundaries."""
    text = re.sub(r'\s+', ' ', text).strip()
    if not text:
        return []

    # split into sentences (simple heuristic)
    sentences = re.split(r'(?<=[.!?]) +', text)

    chunks, current = [], ""
    for sentence in sentences:
        # a single sentence longer than `size` gets hard-split
        while len(sentence) > size:
            if current:
                chunks.append(current)
                current = ""
            chunks.append(sentence[:size])
            sentence = sentence[size - overlap:]

        if len(current) + len(sentence) + 1 <= size:
            current = f"{current} {sentence}".strip()
        else:
            if current:
                chunks.append(current)
            # keep overlap from the previous chunk
            current = (current[-overlap:] + " " + sentence).strip() if current else sentence

    if current:
        chunks.append(current)
    return chunks


# ==================== upload pipeline ====================

def process_uploaded_memo(filename, file_bytes=None, memo_id=None, filepath=None):
    """Extract → chunk → embed → store. Images are stored, not processed.

    Matches by memo id when provided (v1 matched by filename, so duplicate
    names corrupted each other's text).
    """
    try:
        ext = filename.rsplit('.', 1)[-1].lower()

        if ext in ('png', 'jpg', 'jpeg', 'gif', 'webp'):
            print(f"🖼️ {filename} is an image — stored as announcement, no text RAG")
            return {"success": True, "message": "Image announcement stored"}

        if ext not in ('pdf', 'doc', 'docx'):
            print(f"⏭️ Skipping text extraction for {filename} (unsupported)")
            return {"success": True, "message": "Unsupported type, nothing extracted"}

        print(f"📄 Extracting text from {filename}...")
        if file_bytes is not None:
            text = extract_text_from_pdf_bytes(file_bytes)
        elif filepath:
            text = extract_text_from_pdf(filepath)
        else:
            return {"success": False, "message": "No file content provided"}

        if not text:
            print(f"⚠️ No text extracted from {filename}")
            return {"success": False, "message": "No text could be extracted"}

        if memo_id is None:
            row = db.query_one(
                "SELECT id FROM memos WHERE filename = %s ORDER BY uploaded_at DESC LIMIT 1",
                (filename,))
            memo_id = row['id'] if row else None
        if memo_id is None:
            return {"success": False, "message": "Memo row not found"}

        # store whole text (display + fallback), chunked text (retrieval)
        chunks = chunk_text(text)
        db.execute("UPDATE memos SET content = %s WHERE id = %s",
                   (text[:10000], memo_id))
        db.execute("DELETE FROM memo_chunks WHERE memo_id = %s", (memo_id,))

        vectors = None
        try:
            from embeddings import embed_texts
            vectors = embed_texts(chunks)
        except Exception as e:
            print(f"⚠️ Embedding step skipped: {e}")

        inserted = 0
        with db.get_conn() as conn:
            if conn is None:
                return {"success": False, "message": "DB connection failed"}
            with conn.cursor() as cur:
                for i, chunk in enumerate(chunks):
                    vec = vectors[i] if vectors else None
                    cur.execute("""
                        INSERT INTO memo_chunks (memo_id, chunk_index, content, embedding)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (memo_id, chunk_index)
                        DO UPDATE SET content = EXCLUDED.content, embedding = EXCLUDED.embedding
                    """, (memo_id, i, chunk, vec))
                    inserted += 1

        mode = f"+ embeddings ({len(vectors)} vecs)" if vectors else "(keyword fallback — no GEMINI_API_KEY)"
        print(f"✅ Stored {len(text)} chars / {inserted} chunks {mode} for {filename}")
        return {"success": True,
                "message": f"Extracted {len(text)} chars into {inserted} chunks {mode}"}

    except Exception as e:
        print(f"❌ RAG processor error: {e}")
        return {"success": False, "message": str(e)}


# ==================== retrieval ====================

def _cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def retrieve_relevant_chunks(query, k=TOP_K):
    """Return a formatted context string of the most relevant memo chunks."""
    # ---- path 1: vector similarity ----
    try:
        from embeddings import embed_texts
        qvec = (embed_texts([query]) or [None])[0]
        if qvec:
            rows = db.query("""
                SELECT c.content, c.embedding, m.title
                FROM memo_chunks c JOIN memos m ON m.id = c.memo_id
                WHERE c.embedding IS NOT NULL
                ORDER BY c.created_at DESC
                LIMIT 500
            """)
            if rows:
                scored = sorted(
                    ((_cosine(qvec, r['embedding']), r) for r in rows),
                    key=lambda t: t[0], reverse=True)[:k]
                hits = [r for score, r in scored if score > 0.30]
                if hits:
                    return _format(hits, "vector")
    except Exception as e:
        print(f"⚠️ Vector retrieval failed: {e}")

    # ---- path 2: keyword scoring over chunks ----
    try:
        words = [w for w in re.findall(r'[a-z0-9]{3,}', query.lower())]
        if words:
            rows = db.query("""
                SELECT c.content, m.title
                FROM memo_chunks c JOIN memos m ON m.id = c.memo_id
                ORDER BY c.created_at DESC
                LIMIT %s
            """, (KEYWORD_SCAN_LIMIT,))
            scored = []
            for r in rows:
                low = r['content'].lower()
                score = sum(low.count(w) for w in words)
                if score > 0:
                    scored.append((score, r))
            scored.sort(key=lambda t: t[0], reverse=True)
            if scored:
                return _format([r for _, r in scored[:k]], "keyword")
    except Exception as e:
        print(f"⚠️ Keyword retrieval failed: {e}")

    # ---- path 3: latest memos (v1 behavior) ----
    try:
        rows = db.query("""
            SELECT title, content FROM memos
            WHERE content IS NOT NULL AND content != ''
            ORDER BY uploaded_at DESC LIMIT 3
        """)
        if rows:
            return _format(rows, "latest")
    except Exception as e:
        print(f"⚠️ Latest-memo fallback failed: {e}")
    return ""


def _format(rows, mode):
    parts = [f"Official DLSU-D announcements and memos (retrieved by {mode} search):"]
    for r in rows:
        title = r.get('title') or 'Memo'
        content = r.get('content') or ''
        parts.append(f"\n--- {title} ---\n{content[:1500]}")
    return "\n".join(parts)


def query_memos(query):
    """Legacy keyword search across whole memo contents (kept for compat)."""
    try:
        rows = db.query("""
            SELECT title, content, uploaded_at FROM memos
            WHERE content LIKE %s AND content != ''
            ORDER BY uploaded_at DESC LIMIT 3
        """, (f"%{query}%",))
        for row in rows:
            if row.get('uploaded_at') is not None:
                row['uploaded_at'] = row['uploaded_at'].isoformat()
        return rows
    except Exception as e:
        print(f"⚠️ query_memos error: {e}")
        return []
