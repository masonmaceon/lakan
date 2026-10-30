# LAKÁN — AI-Powered Campus Navigation

An AI-powered campus navigation system for **De La Salle University–Dasmariñas (DLSU-D)**.

Combines an interactive pedestrian map, graph-based routing, an assistant that answers
questions about campus buildings and official memos, and (planned) camera-based building
recognition.

> **Status:** early prototype. The map and routing work once the database is seeded.
> Camera detection is **not functional yet** — see [Camera detection](#-camera-detection-not-functional-yet).

---

## Feature status

| Feature | Status | What it needs |
|---|---|---|
| Interactive campus map (Leaflet.js) | ✅ Working | Seeded database |
| Pedestrian routing (Dijkstra over pathway graph) | ✅ Working | Seeded database |
| GPS location + route visualisation | ✅ Working | Browser geolocation permission |
| Chatbot — campus directions & building info | ✅ Working | Nothing (built-in rule engine) |
| Chatbot — free-form Q&A | ⚠️ Needs key | `DEEPSEEK_API_KEY` |
| Memo / announcement RAG (PDF upload → Q&A) | ⚠️ Needs DB | `memos` table (auto-created) + `DEEPSEEK_API_KEY` |
| Admin panel | ⚠️ Needs seeding | `admins` table + one admin row (see [Admin access](#admin-access)) |
| **Camera / building detection** | ❌ **Not functional yet** | **`ROBOFLOW_API_KEY`** — see below |

---

## 📷 Camera detection (not functional yet)

**This is a known setup requirement, not a bug.**

The `/camera` page and the `/detect-building` endpoint call the hosted Roboflow model
`lakan-5ugrp/1`. They need a valid Roboflow API key supplied through the environment:

```env
ROBOFLOW_API_KEY=your_roboflow_key_here
```

Get a key from <https://docs.roboflow.com/api-reference/authentication>.

**Behaviour without a key (expected):**

- The server starts normally and prints:
  `⚠️  ROBOFLOW_API_KEY is not set — camera building detection is DISABLED`
- The startup banner shows `ML Detection: ⚠️  Disabled (no ROBOFLOW_API_KEY)`.
- `POST /detect-building` returns **HTTP 503** with
  `{"success": false, "not_configured": true, "error": "..."}` instead of failing obscurely.
- Everything else (map, routing, chatbot, admin) works normally.

> There is deliberately **no fallback or placeholder key** committed in this repository.
> If you see a 503 from `/detect-building`, you have not set the key — that is the only cause.

---

## Setup

### 1. Prerequisites

- **Python 3.11** (see `.python-version`)
- **MySQL 8** or **MariaDB**, running locally

### 2. Install

```bash
git clone https://github.com/masonmaceon/lakan_dlsud.git
cd lakan_dlsud

python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

Only want to (re)train the classifier? Install the extra training dependencies:

```bash
pip install -r requirements-ml.txt
```

### 3. Configure environment

```bash
cp .env.example .env
```

Then edit `.env` and fill in what you have. **Every variable is optional in the sense
that the app still boots without it** — see [Environment variables](#environment-variables).

### 4. Set up the database

```bash
# create the database
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS lakan_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# create the tables
mysql -u root -p lakan_db < MARIADB_SCHEMA_USE_THIS.sql
```

> ⚠️ The schema file begins with `DROP TABLE IF EXISTS ...` — it **wipes existing data**
> for `locations`, `pathways`, `pathway_points` and `pathway_connections`. Only re-run it
> when you intend to reset.
>
> There are two schema files, `MARIADB_SCHEMA_USE_THIS.sql` and
> `lakan_schema_DOWNLOAD_THIS.sql`. They are near-identical; **use only one**.
> The MariaDB one is the safer default. Consolidating them is on the TODO list.

**Seed the campus data** (20 locations, 15 pathways, auto-detected pathway connections):

```bash
python migrate_to_mysql.py
```

This reads `firestore_locations_fixed.json` and `firestore_pathways_fixed.json`.

### 5. Run

```bash
python app.py
```

```
============================================================
  🗺️  LAKÁN - CAMPUS NAVIGATION SYSTEM
============================================================
  Chatbot: ✅ Ready
  Database: ✅ Connected
  ML Detection: ⚠️  Disabled (no ROBOFLOW_API_KEY)
============================================================
```

Open <http://localhost:5000>.

| Route | Page |
|---|---|
| `/` | Desktop map |
| `/mobile` | Mobile-optimised app |
| `/camera` | Camera building detection (needs key) |
| `/admin` | Memo upload + admin login |
| `/pathway-collector` | Draw and save new pathways |

Production:

```bash
gunicorn app:app --bind 0.0.0.0:$PORT
```

### Admin access

The `admins` table is created automatically on the first memo upload, but it starts
**empty**. Insert an admin row manually:

```sql
INSERT INTO admins (email, password, name) VALUES ('admin@dlsud.edu.ph', 'change-me', 'Admin');
```

> ⚠️ Passwords are currently compared in **plaintext** (no hashing) and there is no session
> management. Fine for local development; must be fixed before any real deployment.

---

## Environment variables

| Variable | Required | Used by | If missing |
|---|---|---|---|
| `MYSQL_HOST` | for DB | map, routing, admin, memos | defaults to `localhost` |
| `MYSQL_PORT` | for DB | " | defaults to `3306` |
| `MYSQL_USER` | for DB | " | defaults to `root` |
| `MYSQL_PASSWORD` | for DB | " | defaults to empty |
| `MYSQL_DATABASE` | for DB | " | defaults to `lakan_db` |
| `DEEPSEEK_API_KEY` | no | chatbot free-form Q&A, memo RAG | chatbot falls back to rule-based answers |
| `ROBOFLOW_API_KEY` | no | camera building detection | **camera detection disabled** (see above) |
| `FLASK_ENV`, `FLASK_DEBUG` | no | Flask | defaults to development |

No secret is ever hardcoded in the source. Anything sensitive is read from the
environment and gitignored via `.env`.

---

## Project structure

```
lakan_dlsud/
├── app.py                        Flask app: config, DB pool, all routes
├── chatbot.py                    CampusChatbot: rule engine + DeepSeek client
├── rag_processor.py              PDF → text → memos.content → RAG context
├── migrate_to_mysql.py           Seeds the DB from the JSON files
├── train_roboflow.py             PyTorch/ResNet50 building classifier (optional)
├── mysql_flask_endpoints.py      ⚠️ orphan snippet — not importable
├── save_location_endpoint.py     ⚠️ orphan snippet — duplicates a route in app.py
│
├── templates/                    Jinja2 pages
│   ├── index.html                desktop map
│   ├── mobile_app.html           mobile app
│   ├── camera.html               camera detection
│   ├── admin_upload.html         admin panel
│   └── pathway_collector.html    pathway drawing tool
│
├── static/
│   ├── js/                       campus_navigation, map_controller, main_mobile,
│   │                             explore_mode, admin_mode, camera_detector
│   ├── css/
│   └── images/
│
├── data seeds
│   ├── firestore_locations_fixed.json     20 campus locations
│   └── firestore_pathways_fixed.json      15 pathways (point sequences)
│
├── schema
│   ├── MARIADB_SCHEMA_USE_THIS.sql        ← use this one
│   └── lakan_schema_DOWNLOAD_THIS.sql     near-duplicate, pending consolidation
│
├── TEST_PROD/                    scratch experiments, not part of the app
├── requirements.txt              runtime dependencies
└── requirements-ml.txt           training-only dependencies
```

### Data model

```
locations             id, name, location_type, latitude, longitude, description
pathways              id, name, pathway_type, surface, width, is_shaded, is_accessible
pathway_points        pathway_id → pathway, point_index, latitude, longitude
pathway_connections   pathway1_id/point_index ↔ pathway2_id/point_index, connection_type
memos                 id, title, filename, content, uploaded_at     (auto-created)
admins                id, email, password, name                     (auto-created)
```

`pathway_connections` is what turns the pathway polylines into a routable graph — it is
generated automatically by `migrate_to_mysql.py`.

---

## Known issues

These are inherited from the prototype and tracked for cleanup:

- **Two near-duplicate schema files** — pick one; consolidate.
- **Orphan modules**: `mysql_flask_endpoints.py` and `save_location_endpoint.py` reference
  `@app.route` without ever defining `app`. They are copy-paste snippets, not importable
  modules, and `save_location_endpoint.py` duplicates a route already in `app.py`.
- **`app.py` references `torch`** in the legacy local-model path
  (`load_building_recognition_model`) but never imports it. Dead code — the Roboflow
  hosted model replaced it.
- **Plaintext admin passwords**, no sessions, no CSRF protection.
- **`app.run(debug=True)`** with the Werkzeug debugger bound to `0.0.0.0` — never enable
  this in production.
- **Schema lives partly in route code** (`CREATE TABLE IF NOT EXISTS` inside handlers)
  instead of in migrations.
- **Routing runs client-side**, so the whole pathway graph is shipped to every browser on
  every page load. Moving Dijkstra server-side would cut payload and make it testable.
- **No tests, no CI, no LICENSE.**

---

## Next steps (rough priority)

1. **Consolidate the schema** into a single versioned migration; move table creation out
   of route handlers.
2. **Restructure `app.py`** into a `create_app()` factory plus Blueprints — this is what
   removes the orphan-module class of bug.
3. **Camera detection** — supply a `ROBOFLOW_API_KEY` and verify the model ID
   `lakan-5ugrp/1` still resolves against the account that owns it.
4. **Tests** for routing, seeding and the RAG pipeline.
