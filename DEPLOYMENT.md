# PEISR Deployment Guide
## Supabase (Database) + Streamlit Cloud (Hosting)

---

## Step 1 — Set up Supabase (free)

1. Go to https://supabase.com and create a free account
2. Click "New Project" — give it a name like `peisr`
3. Once created, go to **Settings → API**
4. Copy:
   - **Project URL** → this is your `SUPABASE_URL`
   - **anon/public key** → this is your `SUPABASE_KEY`

5. Go to **SQL Editor** and run this to create the tables:

```sql
-- Comparisons table (full pipeline runs + ratings)
CREATE TABLE IF NOT EXISTS comparisons (
    comparison_id TEXT PRIMARY KEY,
    run_id TEXT,
    ts TEXT,
    session_id TEXT,
    human_rater TEXT,
    user_tag TEXT,
    variant TEXT,
    temp_mode TEXT,
    threshold_mode TEXT,
    model_mode TEXT,
    user_input TEXT,
    route_predicted TEXT,
    temperature_used FLOAT,
    rewrite_threshold_used INTEGER,
    rewritten BOOLEAN,
    model_used TEXT,
    original_prompt TEXT,
    original_response TEXT,
    original_prompt_critique_json TEXT,
    original_prompt_heuristic_json TEXT,
    enhanced_prompt TEXT,
    enhanced_response TEXT,
    enhanced_prompt_critique_json TEXT,
    enhanced_prompt_heuristic_json TEXT,
    response_llm_judge_json TEXT,
    response_heuristic_judge_json TEXT,
    human_score_original INTEGER,
    human_score_enhanced INTEGER,
    human_pick TEXT,
    human_notes TEXT,
    inline_stars INTEGER,
    inline_pick TEXT,
    inline_notes TEXT
);

-- Inline ratings table (quick star ratings below chat)
CREATE TABLE IF NOT EXISTS inline_ratings (
    id SERIAL PRIMARY KEY,
    comparison_id TEXT,
    run_id TEXT,
    ts TEXT,
    session_id TEXT,
    human_rater TEXT,
    stars INTEGER,
    pick TEXT,
    notes TEXT,
    UNIQUE(comparison_id)
);
```

---

## Step 2 — Update your .env (for local testing)

Add these two lines to your `.env` file:

```
GEMINI_API_KEY=your_gemini_key
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_KEY=your_supabase_anon_key
```

Test locally first:
```powershell
pip install -r requirements.txt
streamlit run app.py
```

The sidebar should show **🟢 Supabase connected** if it worked.

---

## Step 3 — Push to GitHub

1. Create a new GitHub repo (can be private)
2. Upload all files EXCEPT `.env` and `peisr_runs.db`
3. Make sure your repo has:
   - `app.py`
   - `requirements.txt`
   - All `.py` files
   - Do NOT commit `.env` (add it to `.gitignore`)

`.gitignore` file:
```
.env
peisr_runs.db
__pycache__/
*.pyc
*.xlsx
```

---

## Step 4 — Deploy on Streamlit Cloud (free)

1. Go to https://share.streamlit.io
2. Sign in with GitHub
3. Click **"New app"**
4. Select your repo, branch (`main`), and main file (`app.py`)
5. Click **"Advanced settings"** → **Secrets**
6. Add your secrets in TOML format:

```toml
GEMINI_API_KEY = "your_gemini_key"
SUPABASE_URL = "https://xxxx.supabase.co"
SUPABASE_KEY = "your_supabase_anon_key"
```

7. Click **Deploy** — takes about 2 minutes

Your app will be live at:
`https://your-app-name.streamlit.app`

---

## Step 5 — Share publicly

Send the Streamlit URL to anyone — they can use the chat, rate responses,
and all data goes to your Supabase database automatically.

To view all ratings collected:
- Go to Supabase → Table Editor → `inline_ratings`
- Or run: `SELECT * FROM inline_ratings ORDER BY ts DESC;`

---

## Notes

- **Ollama won't work on Streamlit Cloud** (no local GPU). The app will use Gemini only when deployed. Ollama fallback only works when running locally.
- **Free Supabase** gives you 500MB storage and 2GB bandwidth — more than enough for a research paper.
- **Free Streamlit Cloud** gives you 1 app, unlimited traffic.
- If you want to keep SQLite as backup: the app automatically falls back to SQLite if `SUPABASE_URL` is not set.
