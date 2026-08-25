# 🚀 Lakán DLSU-D — Deploy Guide (exact clicks, in order)

Do parts A → E in order. Total time: ~45 minutes. Everything is free.

> Project name: `lakan_dlsud` (GitHub allows underscores; **Render does not** —
> name the Render service `lakan-dlsud`).

---

## PART A — Create the new GitHub repo and push the code (do this first)

### A1. Get the code
Download **`lakan_dlsud-complete.zip`** from the Arena session's file panel.
Unzip it anywhere, e.g. `C:\Users\Adam\dev\lakan_dlsud`. (It contains the full
git history on branch `main`.)

### A2. Create the empty repo on GitHub
1. Go to **github.com** → log in as **masonmaceon**.
2. Click **+** (top-right) → **New repository**.
3. Repository name: **`lakan_dlsud`** · Visibility: **Private** ✔
4. ⚠️ **Do NOT tick** "Add a README", ".gitignore", or "license" — it must be
   completely **empty**.
5. Click **Create repository**.

### A3. Push
Open a terminal in the unzipped folder (type `cmd` in the folder's address
bar in File Explorer):

```bash
cd C:\Users\Adam\dev\lakan_dlsud     # wherever you unzipped it
git remote add origin https://github.com/masonmaceon/lakan_dlsud.git
git push -u origin main
```

- A browser window may pop up for GitHub login → approve (Git Credential
  Manager, normal on Windows). No git? Install from https://git-scm.com/download/win
- **Prefer clicking?** GitHub Desktop: File → **Add local repository** →
  select the folder → **Publish repository** → name `lakan_dlsud`.

✅ **Check:** the repo page on GitHub shows all files (`app.py`, `db.py`,
`schema_postgres.sql`, `seed_data.sql`, …).

---

## PART B — Roboflow: delete both leaked keys, create ONE new key

Both old keys are burned (public in the old repo). Keys don't hold credits or
models — deleting them can't touch your plan or the trained `lakan-5ugrp`
model.

1. **app.roboflow.com** → **Settings** (gear) → **API Keys**
   (or https://app.roboflow.com/settings/api-keys).
2. Delete the two old keys (start with `usYcCG…` and `a7egLG…`).
3. **Create new secret key** (name it `lakan_dlsud`) → copy for Part D.

---

## PART C — Neon (free Postgres)

1. **neon.com** → **Sign up** → **Continue with GitHub**.
2. Create project:
   - Project name: **`lakan`**
   - **Postgres version: leave the DEFAULT** (latest stable — anything 16+ works)
   - Region: **Singapore (AP-Southeast-1)**
3. Copy the **pooled** connection string (host contains `-pooler`) → this is
   `DATABASE_URL` for Part D.
4. Tables + seed with **zero installs** — open **SQL Editor** in Neon's left
   menu and paste+run, one file at a time:
   1. `schema_postgres.sql` (from the repo) → Run
   2. `schema_rag.sql` → Run
   3. `seed_data.sql` → Run (~190 inserts)
5. Sanity check:
   ```sql
   SELECT count(*) FROM locations;   -- expect 20
   SELECT count(*) FROM pathways;    -- expect 15
   ```

---

## PART D — Render (free web service)

1. **render.com** → **Get Started** → **Sign up with GitHub** (grant access to
   the `lakan_dlsud` repo if asked).
2. Dashboard → **New +** → **Web Service** → select **`lakan_dlsud`** → Connect.
3. Fill in:
   - **Name:** `lakan-dlsud` (no underscores on Render)
   - **Region:** **Singapore**
   - **Branch:** `main`
   - **Runtime:** Python 3 (auto-detected)
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app --bind 0.0.0.0:$PORT`
   - **Instance Type:** **Free**
4. **Environment variables:**

   | Key | Value |
   |---|---|
   | `DATABASE_URL` | Neon pooled connection string (C3) |
   | `DEEPSEEK_API_KEY` | your DeepSeek key (~$2 credit) |
   | `ROBOFLOW_API_KEY` | the NEW key from Part B |
   | `GEMINI_API_KEY` | *(recommended, free)* from https://aistudio.google.com/apikey — enables vector memo search; keyword fallback without it |

5. **Create Web Service** → first build ~2–3 min → open the
   `https://lakan-dlsud-xxxx.onrender.com` URL.

---

## PART E — Test it + keep it awake

### E1. Smoke test
| Test | Expected |
|---|---|
| Open the Render URL | Map loads with DLSU-D markers |
| Welcome modal → GPS on (on campus) | "✅ inside DLSU-D" → Start unlocks |
| GPS off-campus (e.g. at home) | "⛔ outside campus" → Start stays locked |
| Ask `where is the library?` without GPS | Asks to turn on GPS |
| Login `aaf4837@dlsud.edu.ph` | Modal closes, 🔧 + upload appear |
| 🔧 → click inside campus on map → `how do I get to JFH?` | Green route from your pin |
| `/admin` → upload a PDF → ask about it | Chatbot answers from the memo |
| `/healthz` | `{"status":"ok",...}` |

### E2. Keep-alive (stops cold starts during pilot weeks)
**uptimerobot.com** → free account → **Add New Monitor** → HTTP(s) → your
Render **`/healthz`** URL → every **5 minutes**.

---

## Changing the admin password later
Seeded account: `aaf4837@dlsud.edu.ph` (owner — password shared out-of-band,
never stored in the repo). No placeholder admin exists anymore.

To create/change an admin on the live app:
1. In Render → Environment, temporarily add `ADMIN_SETUP_TOKEN` = any long
   random string → save (redeploys).
2. ```bash
   curl -X POST https://lakan-dlsud-xxxx.onrender.com/api/admin/create \
     -H "Content-Type: application/json" \
     -H "X-Setup-Token: YOUR-TOKEN" \
     -d '{"email":"you@dlsud.edu.ph","password":"a-long-password","name":"You"}'
   ```
3. Remove the env var after.

## Troubleshooting
| Problem | Fix |
|---|---|
| `git push` auth failed | Install Git / use GitHub Desktop Publish |
| Render build fails on psycopg | Add env `PYTHON_VERSION=3.11.9`, redeploy |
| First load slow (~1 min) | Normal free cold start — E2 fixes |
| Map empty | Check `DATABASE_URL` in Render env (typo?) |
| Chat "not available" | `DEEPSEEK_API_KEY` missing/typo |
| Memo answers keyword-only | Add `GEMINI_API_KEY` |
