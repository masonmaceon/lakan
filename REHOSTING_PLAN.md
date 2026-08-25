# Lakán DLSU-D — Free-Hosting Revival Plan

> Goal: bring the DLSU-D campus navigation system back online for **$0/month**
> so students can try it, then iterate.
> Status: Phases 0–4 complete (see CHANGELOG.md). Deployment (Phase 2 guide
> parts A–E) deliberately deferred while features are polished.

---

## 1. Recommended stack (all free)

| Component | Service | Free tier | Notes |
|---|---|---|---|
| Web app (Flask + gunicorn) | **Render** free web service | 512 MB RAM, 750 hr/mo | Sleeps after ~15 min idle → UptimeRobot ping |
| Database | **Neon** serverless Postgres | 0.5 GB storage, autosuspend | No pgvector needed (embeddings as arrays) |
| PDF/image storage | **Postgres itself** (`BYTEA`) | (within 0.5 GB) | Hosts have ephemeral disks — DB is the durable store |
| Chatbot LLM | **DeepSeek API** | Pay-as-you-go (~pennies) | ~$2 credit, barely used. Free alternative: Gemini Flash |
| Embeddings | **Gemini** `text-embedding-004` | Free tier | Optional; keyword fallback without it |
| Building detection | **Roboflow** hosted API | Free tier | Rotate the leaked keys before launch! |
| Keep-alive | **UptimeRobot** | Free, 5-min pings | Ping `/healthz` |

**Total: $0/month.**

### Why the old setup can't just be redeployed
- Railway discontinued its free tier; free hosted MySQL is nearly extinct →
  Postgres migration (Neon).
- The app wrote uploads to local disk — ephemeral on every free host → files
  now live in the DB.

## 2. Audit of the original codebase (what we inherited)

### The "RAG" was not RAG
v1 extracted up to 10k chars per PDF into `memos.content` and dumped the 5
latest memos wholesale into the DeepSeek prompt — no relevance ranking; the
keyword-search function was dead code; text matched by filename (duplicates
corrupted each other). Replaced in Phase 4 with chunking → embeddings →
cosine top-k (see rag_processor.py).

### Bugs & debt found and fixed
| # | Issue | Fix |
|---|---|---|
| D1 | Two Roboflow API keys hardcoded & public | Scrubbed → env var; rotate keys (guide Part B) |
| D2 | Admin passwords plaintext | Werkzeug hashes (legacy rows still verifiable) |
| D3 | `admin_login` duplicate queries, use-after-close, password logging | Rewritten |
| D4 | Lazy `CREATE TABLE memos` missing the `content` column it INSERTs into | Proper schema |
| D5 | `memos`/`admins` missing from schema files | Reconstructed in `schema_postgres.sql` |
| D6 | Dead PyTorch/SDK code, Firestore-era scripts | Removed / `legacy/` |
| D7 | No DB seeding | `seed.py` + `seed_data.sql` (repairs bad export data) |
| D8 | Desktop page: undefined handlers, wrong map container id, null crash | Fixed (page was fully unusable) |
| D9 | Geofence polygon self-intersecting — all 20 buildings read "outside" | Official bounding box, single source of truth (`geofence.py`/`.js`) |
| D10 | Pathway graph fragmented (only 5/20 buildings reachable) | Proximity stitching (355 connections ≤20 m) + virtual user node |

## 3. Options considered (2026)
Render+Neon ✅ chosen · Railway ❌ no free tier · Heroku ❌ dead · Fly.io ❌
card required · Glitch ❌ shut down · Replit ❌ no free hosting ·
Vercel/Netlify ❌ needs serverless rewrite · PythonAnywhere 🟡 plan B ·
Koyeb 🟡 · HF Spaces 🟡 · TiDB 🟡 (if we ever want MySQL-compat again) ·
Oracle Always Free ❌ ops burden.

## 4. Phases

### Phase 0 — repo hygiene ✅
Keys scrubbed, `.env.example`, hardened `.gitignore`, this plan.

### Phase 1 — Postgres migration ✅
`db.py` (psycopg3 pool), `schema_postgres.sql`, `seed.py` (repairs CEAT→"MLH"
mislabeled name, 15 missing names), admin/memo bug fixes, deps slimmed
(~100 MB less per deploy). Verified end-to-end on real Postgres 16.

### Phase 2 — deploy (⏸ deferred by choice)
Everything prepared: `seed_data.sql` (paste into Neon's SQL editor — zero
installs), `PHASE2_DEPLOY_GUIDE.md` with exact clicks. Blocked only on
owner's account signups (GitHub repo, Roboflow rotation, Neon, Render).

### Phase 3 — durable file storage ✅
Uploads (PDFs and images) stored as `BYTEA` in Postgres, served from the DB
with correct MIME types; zero disk writes.

### Phase 4 — real RAG ✅ (implemented without pgvector)
`embeddings.py` (Gemini free tier) + `rag_processor.py`: upload → extract →
chunk (~800/100) → embed → `memo_chunks` (arrays) → query → embed question →
cosine top-4 → DeepSeek prompt. Fallbacks: keyword scoring → latest memos.

### Phase 5 — security & student pilot polish (remaining)
- ~~Delete placeholder admin~~ ✅ done — no placeholder is seeded anymore
- Session tokens for admin (currently login is per-page, no cookie)
- Feedback capture ("was this helpful?"), usage analytics
- Model evaluation plan (below)

## 5. Risks & mitigations
| Risk | Mitigation |
|---|---|
| Render sleeps after 15 min | UptimeRobot pings `/healthz` every 5 min |
| Neon autosuspend | ~0.5 s first-query wake — fine |
| DeepSeek credit runs dry | Gemini Flash free tier as swap-in |
| Attachments/leaks | Keys rotated; only hashes in repo |

## 6. Model evaluation note (the "99.9% on 10k images" model)
That number is almost certainly optimistic — train/test leakage (near-duplicate
frames, one team's devices/angles/lighting) and aggregate accuracy hiding
per-building failures. Shipped guardrail: `ROBOFLOW_MIN_CONFIDENCE=0.40`
filters weak detections server-side. During the pilot: log predictions
(class, confidence), build a held-out eval set split by capture session,
report per-building top-1 at threshold + confusion pairs; retrain only if
the honest numbers demand it.

## 7. Publishing / seeding the new repo
The full history lives on this repo's working branch. Download
`lakan_dlsud-complete.zip` → `git remote add origin …/lakan_dlsud.git` →
`git push -u origin main` (guide Part A). Neon seeding: guide Part C.

## 8. Open decisions (owner's call)
1. Gate 3 sits ~50 m outside the official geofence box (west bound 120.9575
   vs Gate 3 at ~120.95697) — widen to 120.9567 or keep as-is?
2. ~~Delete placeholder admin~~ ✅ resolved — placeholder seeding removed
3. Keep Roboflow model `lakan-5ugrp/1` for the pilot? (confidence gate live)
