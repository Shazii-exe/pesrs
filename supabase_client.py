# supabase_client.py
# Supabase (Postgres) backend — drop-in replacement for SQLite db.py
# Falls back to SQLite if Supabase credentials are missing.

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

# ── Supabase credentials ──────────────────────────────────────
# Set these in .env locally or in Streamlit Cloud secrets:
#   SUPABASE_URL = "https://xxxx.supabase.co"
#   SUPABASE_KEY = "your-anon-or-service-role-key"

try:
    from supabase import create_client, Client
    _SUPABASE_AVAILABLE = True
except ImportError:
    _SUPABASE_AVAILABLE = False

from dotenv import load_dotenv
load_dotenv()

_SUPABASE_URL = os.getenv("SUPABASE_URL", "")
_SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

DB_PATH = "peisr_runs.db"  # kept for SQLite fallback

def _get_supabase() -> Optional[Any]:
    if _SUPABASE_AVAILABLE and _SUPABASE_URL and _SUPABASE_KEY:
        return create_client(_SUPABASE_URL, _SUPABASE_KEY)
    return None


# ── SQLite fallback init ──────────────────────────────────────
def init_db():
    """Create SQLite tables if Supabase not configured."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS comparisons (
        comparison_id TEXT PRIMARY KEY,
        run_id TEXT, ts TEXT, session_id TEXT,
        human_rater TEXT, user_tag TEXT,
        variant TEXT, temp_mode TEXT, threshold_mode TEXT, model_mode TEXT,
        user_input TEXT, route_predicted TEXT,
        temperature_used REAL, rewrite_threshold_used INTEGER,
        rewritten INTEGER, model_used TEXT,
        original_prompt TEXT, original_response TEXT,
        original_prompt_critique_json TEXT, original_prompt_heuristic_json TEXT,
        enhanced_prompt TEXT, enhanced_response TEXT,
        enhanced_prompt_critique_json TEXT, enhanced_prompt_heuristic_json TEXT,
        response_llm_judge_json TEXT, response_heuristic_judge_json TEXT,
        human_score_original INTEGER, human_score_enhanced INTEGER,
        human_pick TEXT, human_notes TEXT,
        inline_stars INTEGER, inline_pick TEXT, inline_notes TEXT
    );
    CREATE TABLE IF NOT EXISTS inline_ratings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        comparison_id TEXT, run_id TEXT, ts TEXT,
        session_id TEXT, human_rater TEXT,
        stars INTEGER, pick TEXT, notes TEXT
    );
    """)
    conn.commit()
    conn.close()


# ── Save full comparison ──────────────────────────────────────
def save_comparison(
    *,
    comparison_id: str,
    run_id: str,
    session_id: str,
    human_rater: str,
    user_tag: str,
    variant: str,
    temp_mode: str,
    threshold_mode: str,
    model_mode: str,
    user_input: str,
    route_predicted: str,
    temperature_used: float,
    rewrite_threshold_used: int,
    rewritten: bool,
    original_prompt: str,
    original_response: str,
    original_prompt_critique: Dict[str, Any],
    original_prompt_heuristic: Dict[str, Any],
    enhanced_prompt: str,
    enhanced_response: str,
    enhanced_prompt_critique: Dict[str, Any],
    enhanced_prompt_heuristic: Dict[str, Any],
    response_llm_judge: Dict[str, Any],
    response_heuristic_judge: Dict[str, Any],
    human_score_original: int,
    human_score_enhanced: int,
    human_pick: str,
    human_notes: str,
    model_used: str = "",
):
    ts   = datetime.now().isoformat(timespec="seconds")
    row  = {
        "comparison_id":                  comparison_id,
        "run_id":                         run_id,
        "ts":                             ts,
        "session_id":                     session_id,
        "human_rater":                    human_rater,
        "user_tag":                       user_tag,
        "variant":                        variant,
        "temp_mode":                      temp_mode,
        "threshold_mode":                 threshold_mode,
        "model_mode":                     model_mode,
        "user_input":                     user_input,
        "route_predicted":                route_predicted,
        "temperature_used":               float(temperature_used),
        "rewrite_threshold_used":         int(rewrite_threshold_used or 0),
        "rewritten":                      bool(rewritten),
        "model_used":                     model_used,
        "original_prompt":                original_prompt,
        "original_response":              original_response or "",
        "original_prompt_critique_json":  json.dumps(original_prompt_critique),
        "original_prompt_heuristic_json": json.dumps(original_prompt_heuristic),
        "enhanced_prompt":                enhanced_prompt,
        "enhanced_response":              enhanced_response or "",
        "enhanced_prompt_critique_json":  json.dumps(enhanced_prompt_critique),
        "enhanced_prompt_heuristic_json": json.dumps(enhanced_prompt_heuristic),
        "response_llm_judge_json":        json.dumps(response_llm_judge),
        "response_heuristic_judge_json":  json.dumps(response_heuristic_judge),
        "human_score_original":           int(human_score_original),
        "human_score_enhanced":           int(human_score_enhanced),
        "human_pick":                     human_pick,
        "human_notes":                    human_notes,
    }

    sb = _get_supabase()
    if sb:
        sb.table("comparisons").upsert(row).execute()
    else:
        _sqlite_upsert_comparison(row)


def _sqlite_upsert_comparison(row: dict):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cols = ", ".join(row.keys())
    placeholders = ", ".join(["?"] * len(row))
    conn.execute(
        f"INSERT OR REPLACE INTO comparisons ({cols}) VALUES ({placeholders})",
        list(row.values())
    )
    conn.commit()
    conn.close()


# ── Save inline rating (quick stars below chat message) ───────
def save_inline_rating(
    *,
    comparison_id: str,
    run_id: str,
    session_id: str,
    human_rater: str,
    stars: int,
    pick: str,
    notes: str = "",
):
    ts  = datetime.now().isoformat(timespec="seconds")
    row = {
        "comparison_id": comparison_id,
        "run_id":        run_id,
        "ts":            ts,
        "session_id":    session_id,
        "human_rater":   human_rater,
        "stars":         int(stars),
        "pick":          pick,
        "notes":         notes,
    }

    sb = _get_supabase()
    if sb:
        # Upsert by comparison_id so re-rating updates rather than duplicates
        sb.table("inline_ratings").upsert(row, on_conflict="comparison_id").execute()
    else:
        init_db()
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
            INSERT OR REPLACE INTO inline_ratings
            (comparison_id, run_id, ts, session_id, human_rater, stars, pick, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [row[k] for k in ["comparison_id","run_id","ts","session_id","human_rater","stars","pick","notes"]])
        conn.commit()
        conn.close()


# ── Fetch recent comparisons (for sidebar preview) ────────────
def fetch_comparisons(limit: int = 8) -> List[tuple]:
    sb = _get_supabase()
    if sb:
        res = (sb.table("comparisons")
               .select("comparison_id,ts,human_rater,route_predicted,temperature_used,rewrite_threshold_used,rewritten,human_score_original,human_score_enhanced,human_pick,user_input")
               .order("ts", desc=True)
               .limit(limit)
               .execute())
        return [tuple(r.values()) for r in (res.data or [])]
    else:
        init_db()
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute(
            """SELECT comparison_id, ts, human_rater, route_predicted,
                      temperature_used, rewrite_threshold_used, rewritten,
                      human_score_original, human_score_enhanced, human_pick, user_input
               FROM comparisons ORDER BY ts DESC LIMIT ?""", (limit,)
        ).fetchall()
        conn.close()
        return rows


def is_supabase_connected() -> bool:
    return _get_supabase() is not None
