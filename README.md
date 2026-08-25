# Lakán DLSU-D — AI-Powered Campus Navigation (`lakan_dlsud`)

Free-hosting revival of the original Railway/MySQL deployment, migrated to
**Flask + PostgreSQL** targeting **$0/month** hosting (Render + Neon).
See [CHANGELOG.md](CHANGELOG.md) for everything that changed, and
[REHOSTING_PLAN.md](REHOSTING_PLAN.md) for the roadmap and stack rationale.

## Features
- 🗺️ Campus map + pathway routing (Leaflet.js) — all 20 buildings reachable;
  routes start from your verified location (GPS or admin pin), not a fixed gate
- 🎓 **Campus geofence** (official DLSU-D bounding box): routing and building
  reveals are on-campus only — enforced in the frontend and the chat API
- 🤖 Chatbot (DeepSeek) with navigation intents, gate finder, and **real RAG**
  over uploaded memos (chunking → embeddings → cosine retrieval; keyword
  fallback without a Gemini key)
- 📄 Admin uploads: PDFs **and images** for announcements — stored in the
  database (survives host restarts), displayed in the mobile announcement sheet
- 📷 Building detection via Roboflow hosted API (confidence-filtered)
- 🔐 Admin flow: login on the welcome modal → 🔧 Admin Mode (set a demo
  location by clicking the map) → upload tools
- 🛟 Graceful degradation: runs even without DB/keys configured

## Quick start (local)

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt   # Windows: venv\Scripts\pip
cp .env.example .env            # then edit values

# 1. Create the schema (any Postgres; psql or Neon's SQL editor)
psql "$DATABASE_URL" -f schema_postgres.sql
psql "$DATABASE_URL" -f schema_rag.sql      # memo chunk table (RAG)

# 2. Seed campus data + admin accounts (or paste seed_data.sql in Neon's editor)
.venv/bin/python seed.py

# 3. Run
.venv/bin/python app.py         # → http://localhost:5000
```

**Admin accounts:** the owner account (`aaf4837@dlsud.edu.ph`) is seeded
automatically — its password is never stored in this repo. Add more admins
via the token-protected `/api/admin/create` (see the deploy guide).

Pages: `/` desktop · `/mobile` student app · `/camera` detection ·
`/admin` uploads · `/healthz` uptime ping.

## Deploying (Render + Neon, $0)
Follow [PHASE2_DEPLOY_GUIDE.md](PHASE2_DEPLOY_GUIDE.md) Parts A–E:
GitHub repo `lakan_dlsud` → Neon (paste `schema_postgres.sql`,
`schema_rag.sql`, `seed_data.sql` in the SQL editor) → Render web service
(name it `lakan-dlsud` — Render disallows underscores) with env vars
`DATABASE_URL`, `DEEPSEEK_API_KEY`, `ROBOFLOW_API_KEY` (+ optional
`GEMINI_API_KEY`).

## Project layout
```
app.py                  Flask app (routes, geofence enforcement, admin, detection)
chatbot.py              DeepSeek chatbot + navigation intents + memo context
rag_processor.py        PDF extraction → chunking → embeddings → retrieval
embeddings.py           Gemini text-embedding-004 client (free tier, optional)
db.py                   Postgres connection layer (psycopg3 pool)
geofence.py / .js       Official campus bounding box (server + client mirror)
schema_postgres.sql     full schema (locations/pathways/memos/admins)
schema_rag.sql          memo_chunks table
seed.py / seed_data.sql campus data + admin accounts (idempotent)
migrations/             incremental SQL for DBs created before a change
legacy/                 old Firestore/MySQL-era scripts (not used at runtime)
templates/, static/     frontend (Leaflet map, mobile app, camera, geofence.js)
```
