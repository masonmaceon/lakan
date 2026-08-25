# Changelog — Lakán DLSU-D (`lakan_dlsud`)

Forked from the original Railway/MySQL deployment (`masonmaceon/lakan`,
last commit `bda878f`). Everything below happened during the free-hosting
revival. Dates are 2026-08-19.

## ✅ Current state (as of `a06fbb9`)

**Working, tested in the live preview:**
- Map (Leaflet) with 20 locations + 15 pathways from PostgreSQL
- Routing engine: **20/20 buildings reachable** (was 5/20 in the original)
- Routes start from the **user's actual location** (GPS or admin map-pin),
  connected to the 3 nearest pathway nodes via a virtual user node
- **Geofence** using the team's official bounding box
  (N 14.3290 · S 14.3195 · E 120.9650 · W 120.9575): routing AND building
  reveals require a verified inside-campus location; enforced in the
  frontend and authoritatively in the chat API
- Welcome modal (desktop + mobile): LAKAN logo, quick guide, **GPS toggle as
  step 1**, inline **admin email/password login**, Start Navigating disabled
  until inside campus (admins can enter) — woody-glassmorphism styling,
  scrollable/fit-to-screen
- Admin flow: login → modal closes → chat visible → 🔧 **Admin Mode** button
  (click map to set a demo location) → ⬆ upload button → `/admin`
- Memo/announcement uploads: **PDFs and images**, stored **in the database**
  (survives host restarts), served with correct content types
- **Real RAG**: PDF → text → chunks (~800 chars) → Gemini embeddings →
  `memo_chunks` → cosine top-4 into the DeepSeek prompt; graceful fallbacks
  (keyword scoring → latest memos) when no `GEMINI_API_KEY`
- Admin accounts with hashed passwords (owner: `aaf4837@dlsud.edu.ph`);
  `/api/admin/create` protected (bootstrap-only or `X-Setup-Token`)
- `/healthz` endpoint for uptime pings

**Pending / needs keys or accounts:**
- Camera building detection → needs fresh `ROBOFLOW_API_KEY` (old ones leaked
  in the public repo — rotate!)
- Vector memo search → optional free `GEMINI_API_KEY` (keyword fallback active)
- Public deployment → Parts A–D of `PHASE2_DEPLOY_GUIDE.md` (GitHub push,
  Neon, Render) — deliberately deferred while iterating
- Gate 3 sits ~50 m outside the official geofence box — awaiting owner's call

## Changes by commit

| Commit | What |
|---|---|
| `33d404a` | **Phase 0** — repo hygiene: scrubbed 2 leaked Roboflow keys, `.env.example`, hardened `.gitignore`, rehosting plan |
| `ca1f90c` | **Phase 1** — PostgreSQL migration: `db.py` (psycopg3 pool), `schema_postgres.sql` (incl. previously-missing `memos`/`admins`), `seed.py` (+ repairs bad export data: CEAT mislabeled "MLH", 15 unnamed buildings), fixed `admin_login`/`upload_memo` bugs, dead code removed, deps slimmed ~100 MB |
| `ee8d650` | **Phase 2 prep** — `seed_data.sql` (zero-install seeding via Neon SQL editor), `seed.py --sql`, step-by-step deploy guide |
| `bfcf1af` | Desktop page fixed (missing `closeWelcome`/`toggleChat` handlers made it unusable); `main_mobile.js` works on both pages' element ids; **Phase 3**: PDFs stored as `BYTEA` (no disk writes) |
| `f1bc8e2` | Map container fix (`#map-container` vs `#map`) + cache-busting |
| `4763b0b` | **Phase 4 RAG** (chunking, Gemini embeddings, array-cosine — no pgvector needed, keyword fallback); image announcements; geofence enforced (replaced broken self-intersecting polygon that classified *all* buildings as outside); welcome modal: admin login + GPS check |
| `e4df8c1` | Geofence also blocks building reveals; woody-glass modal styling; prominent Admin Login buttons |
| `8ec836d` | Welcome modal rebuilt to the original design: logo, inline login fields, quick guide, GPS toggle first, Start Navigating hard-disabled until inside campus |
| `a78caae` | **Official geofence**: team's bounding box (from `admin_mode.js`) becomes single source of truth in `geofence.py`/`geofence.js`; strict reveals (no-location requests blocked too); removed admin auto location-pin |
| `fcd2ec0` | Owner admin account added (hash only); welcome-modal logins reveal the 🔧 Admin Mode button |
| `1dfe44e` | Admin login closes the modal; chatbot textfield visible immediately after entry (desktop auto-expands) |
| `7304fcb` | **Routing fixed**: proximity stitching (355 cross-pathway connections ≤20 m — graph was fragmented islands, 5/20 reachable → 20/20); virtual user node ("connect my location to nearest pathway point"); modals fit the screen (scrollable) |
| `85b1e9a` | Fixed false "error showing the route" (unguarded `chatbotContainer` access on desktop) |
| `a06fbb9` | **Rebrand**: `lakan-v2` → `lakan_dlsud` everywhere |

## Known issues / notes
- `legacy/` holds Firestore-era scripts (not used at runtime)
- Placeholder admin `admin@lakan.local` / `lakan-admin` should be removed
  before the student pilot
- Free-tier reminders: Render sleeps after ~15 min idle (UptimeRobot fixes),
  filesystems are ephemeral (why files live in the DB)
