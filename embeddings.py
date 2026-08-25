"""
Lakán DLSU-D — text embeddings for the RAG pipeline.

Uses Google's Gemini `text-embedding-004` model (free API tier, 768 dims).
DeepSeek does not offer an embeddings endpoint, hence a separate provider.

Get a free key: https://aistudio.google.com/apikey → set GEMINI_API_KEY.

Everything here degrades gracefully: no key / any API error → returns None,
and the RAG pipeline falls back to keyword search (see rag_processor.py).
"""

import os

import requests
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
EMBED_MODEL = "models/text-embedding-004"
EMBED_DIM = 768
_BATCH = 80  # requests per batchEmbedContents call


def embeddings_available() -> bool:
    return bool(GEMINI_API_KEY)


def embed_texts(texts):
    """Embed a list of strings → list of 768-dim lists, or None on failure.

    Returns None (never raises) so callers can fall back to keyword search.
    """
    if not GEMINI_API_KEY or not texts:
        return None
    try:
        out = []
        for i in range(0, len(texts), _BATCH):
            batch = texts[i:i + _BATCH]
            resp = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/"
                f"text-embedding-004:batchEmbedContents",
                params={"key": GEMINI_API_KEY},
                json={
                    "requests": [
                        {"model": EMBED_MODEL,
                         "content": {"parts": [{"text": t}]}}
                        for t in batch
                    ]
                },
                timeout=30,
            )
            if resp.status_code != 200:
                print(f"⚠️ Gemini embedding API {resp.status_code}: "
                      f"{resp.text[:200]}")
                return None
            data = resp.json()
            for item in data.get("embeddings", []):
                out.append(item.get("values"))
        if len(out) != len(texts) or any(v is None for v in out):
            print("⚠️ Gemini embedding count mismatch — falling back")
            return None
        return out
    except Exception as e:
        print(f"⚠️ Embedding error: {e}")
        return None
