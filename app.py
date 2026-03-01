"""
app.py — PEISR Chat UI with Black Box Panel
GPT-style continuous conversation + toggle-able backend inspector.
All existing pipeline files (answerer, rewriter, judge, db, etc.) are untouched.
"""

import uuid
import time
import hashlib
import os
import json

import streamlit as st
import pandas as pd

from answerer import run_pipeline
from judge import judge_pair, heuristic_judge_pair, heuristic_prompt_critique
from supabase_client import init_db, save_comparison, save_inline_rating, fetch_comparisons, is_supabase_connected, DB_PATH
from intent_classifier import classify_intent, choose_temperature

# ─────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="PEISR — Chat",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>

/* Chat input container */
[data-testid="stChatInput"] {
    max-width: 100%;
}

/* Send button styling */
[data-testid="stChatInput"] button {
    background-color: #f3f3f7 !important;
    color: #111 !important;
    border-radius: 12px !important;
    border: 1px solid #2e2e3e !important;
    padding: 6px 12px !important;
}

/* Remove ugly flat edge */
[data-testid="stChatInput"] button:hover {
    background-color: #ffffff !important;
}

</style>
""", unsafe_allow_html=True)

init_db()

# ─────────────────────────────────────────────────────────────
# SESSION STATE INIT
# ─────────────────────────────────────────────────────────────
defaults = {
    "session_id": str(uuid.uuid4()),
    "saved_ids": set(),
    "last_submit_ts": 0.0,
    "messages": [],          # [{role, content, run_data}]
    # "show_black_box": False,
    "active_run": None,
    "last_run_data": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Global */
html, body, [data-testid="stAppViewContainer"] { background: #0f0f13 !important; color: #e8e8f0 !important; }
[data-testid="stAppViewContainer"] > .main { padding-top: 0 !important; }
header[data-testid="stHeader"] { background: transparent !important; }
section[data-testid="stSidebar"] { background: #18181f !important; border-right: 1px solid #2e2e3e; }
[data-testid="stTextArea"] textarea {
    background: #18181f !important; color: #e8e8f0 !important;
    border: 1px solid #2e2e3e !important; border-radius: 12px !important;
}
[data-testid="stTextArea"] textarea:focus { border-color: #7c6af7 !important; }
.stButton > button { border-radius: 10px !important; font-weight: 600 !important; }
/* Dividers */
hr { border-color: #2e2e3e !important; }

/* Top bar */
.topbar {
    background: #18181f; border-bottom: 1px solid #2e2e3e;
    padding: 12px 24px; display: flex; align-items: center;
    justify-content: space-between; margin-bottom: 4px;
}
.topbar-title {
    font-size: 20px; font-weight: 800;
    background: linear-gradient(135deg, #7c6af7, #a78bfa);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.topbar-sub { font-size: 12px; color: #9090a8; margin-top: 2px; }

/* Chat bubbles */
.msg-row { display: flex; gap: 10px; margin-bottom: 18px; align-items: flex-start; }
.msg-row.user { flex-direction: row-reverse; }
.avatar {
    width: 34px; height: 34px; border-radius: 50%; flex-shrink: 0;
    display: flex; align-items: center; justify-content: center;
    font-size: 13px; font-weight: 700;
}
.avatar.user { background: #5b4fcf; color: #fff; }
.avatar.assistant { background: #1a2a1a; color: #22c55e; border: 1px solid #2e4a2e; font-size: 16px; }
.bubble {
    padding: 12px 16px; border-radius: 16px;
    max-width: 700px; line-height: 1.7; font-size: 14px; word-break: break-word;
}
.bubble.user { background: #5b4fcf; color: #fff; border-bottom-right-radius: 4px; }
.bubble.assistant { background: #18181f; color: #e8e8f0; border: 1px solid #2e2e3e; border-bottom-left-radius: 4px; }
.meta-row { font-size: 11px; color: #9090a8; margin-top: 5px; display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.badge { font-size: 10px; padding: 2px 7px; border-radius: 4px; font-weight: 700; letter-spacing: .4px; }
.badge-rewrite { background: #2d1f6e; color: #a78bfa; border: 1px solid #5b4fcf; }
.badge-direct  { background: #1a2e1a; color: #22c55e; border: 1px solid #2e4a2e; }
.badge-route   { background: #1e2030; color: #7c6af7; border: 1px solid #3a3060; }

/* Black Box Panel */
.bb-header {
    padding: 14px 16px 10px; border-bottom: 1px solid #2e2e3e;
    font-size: 11px; font-weight: 800; color: #9090a8; letter-spacing: .6px;
    background: #18181f; position: sticky; top: 0; z-index: 10;
}
.bb-header span { color: #7c6af7; }
.bb-section { padding: 12px 4px 12px; border-bottom: 1px solid #22222c; margin-bottom: 4px; }
.bb-section-title { font-size: 10px; font-weight: 800; letter-spacing: 1px; text-transform: uppercase; color: #607090; margin-bottom: 8px; }
.bb-kv { display: flex; gap: 8px; margin: 4px 0; font-size: 12px; }
.bb-k { color: #9090a8; min-width: 110px; }
.bb-v { color: #e8e8f0; font-weight: 500; }
.bb-box {
    background: #0f0f13; border: 1px solid #2e2e3e; border-radius: 8px;
    padding: 10px 12px; font-size: 12px; line-height: 1.6;
    white-space: pre-wrap; word-break: break-word; color: #c8c8e0; margin-top: 6px;
}
.bb-box.a { border-left: 3px solid #60a5fa; }
.bb-box.b { border-left: 3px solid #a78bfa; }
.bb-box.winner { border-left: 3px solid #22c55e; }
.score-bar-outer { flex: 1; height: 7px; background: #22222c; border-radius: 4px; overflow: hidden; }
.score-bar-inner { height: 100%; border-radius: 4px; }
.winner-tag {
    display: inline-flex; align-items: center; gap: 5px;
    background: #1a2e1a; color: #22c55e; border: 1px solid #2e4a2e;
    padding: 3px 9px; border-radius: 5px; font-size: 11px; font-weight: 700;
}
.trace-iter { background: #0f0f13; border: 1px solid #2e2e3e; border-radius: 8px; padding: 10px 12px; margin-bottom: 8px; }
.trace-label { font-size: 10px; font-weight: 700; letter-spacing: .5px; color: #7c6af7; margin-bottom: 5px; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    rater_name = st.text_input("Your name (for logging)", value="", placeholder="e.g., Mahek", key="rater_name")
    user_tag   = st.text_input("User tag (optional)", value="", placeholder="e.g., Tuba-UK", key="user_tag")

    admin_secret = os.getenv("ADMIN_KEY", "")
    admin_key    = st.text_input("Admin key", value="", type="password", key="admin_key")
    is_admin     = (admin_secret == "") or (admin_key == admin_secret)
    show_judge   = False
    if is_admin:
        show_judge = st.toggle("Show judge JSON (admin)", value=False, key="show_judge_json")
        st.caption("✅ Admin mode")
    else:
        st.caption("Judge JSON hidden (public)")

    auto_temp = st.toggle("Auto temperature", value=True, key="auto_temp")
    temperature = st.slider("Temperature (if auto OFF)", 0.0, 1.0, 0.4, 0.05, disabled=auto_temp)

    auto_threshold = st.toggle("Auto threshold (LLM-decided)", value=True, key="auto_threshold")
    if auto_threshold:
        st.caption("🤖 Threshold set dynamically per prompt by the LLM")
    else:
        st.caption("⚠️ Manual override — disables adaptive threshold")
    rewrite_threshold = st.slider("Threshold override", 4, 20, 15, disabled=auto_threshold)

    st.divider()
    if is_supabase_connected():
        st.caption("🟢 Supabase connected")
    else:
        st.caption(f"🟡 SQLite fallback: `{DB_PATH}`")
    if os.path.exists(DB_PATH):
        with open(DB_PATH, "rb") as f:
            st.download_button("⬇ Download DB", data=f.read(), file_name=DB_PATH, mime="application/x-sqlite3", use_container_width=True)

    # ── Download results as Excel ──────────────────────────────
    if st.button("📊 Export Results Excel", use_container_width=True):
        try:
            import subprocess, glob, os
            result = subprocess.run(
                ["python", "analyze_results.py"],
                capture_output=True, text=True, timeout=60
            )
            files = sorted(glob.glob("peisr_results_*.xlsx"), reverse=True)
            if files:
                with open(files[0], "rb") as f:
                    st.download_button(
                        "⬇ Download Excel",
                        data=f.read(),
                        file_name=os.path.basename(files[0]),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                    )
            else:
                st.error(f"Export failed: {result.stderr[:200]}")
        except Exception as e:
            st.error(f"Export error: {e}")
    try:
        rows = fetch_comparisons(limit=8)
        if rows:
            st.caption("Recent ratings")
            df = pd.DataFrame(rows, columns=["id","ts","rater","route","temp","thr","rewritten","sA","sB","pick","input"])
            st.dataframe(df[["ts","rater","route","pick","input"]], use_container_width=True, height=180)
    except Exception:
        pass

    st.divider()
    if st.button("🗑 Clear chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.last_run_data = None
        st.rerun()

    # ── Session summary stats ──────────────────────────────────
    runs = [m["run_data"] for m in st.session_state.get("messages", [])
            if m.get("role") == "assistant" and m.get("run_data")]
    if runs:
        st.divider()
        st.markdown("### 📊 Session Stats")
        total   = len(runs)
        rewritten = sum(1 for r in runs if r.get("rewritten"))
        direct    = total - rewritten
        avg_lift  = sum((r.get("critique_final", {}).get("total", 0) or 0) -
                        (r.get("critique_original", {}).get("total", 0) or 0)
                        for r in runs) / total
        y_wins    = sum(1 for r in runs if r.get("winner_label") == "Y")
        routes    = {}
        for r in runs:
            routes[r.get("route", "?")] = routes.get(r.get("route", "?"), 0) + 1

        st.markdown(f"""
        <div style='font-size:12px;line-height:1.8;color:#c8c8d8'>
        🔢 <b>Prompts:</b> {total}<br/>
        ✨ <b>Rewritten:</b> {rewritten} ({rewritten/total:.0%})<br/>
        ✅ <b>Direct:</b> {direct} ({direct/total:.0%})<br/>
        📈 <b>Avg score lift:</b> {avg_lift:+.1f}/20<br/>
        🏆 <b>Enhanced won:</b> {y_wins}/{rewritten if rewritten else 1} rewritten<br/>
        🗺️ <b>Routes:</b> {", ".join(f"{k}×{v}" for k,v in routes.items())}
        </div>""", unsafe_allow_html=True)

    # ── Session summary stats ──────────────────────────────
    assistant_runs = [
        m["run_data"] for m in st.session_state.messages
        if m["role"] == "assistant" and m.get("run_data")
    ]
    if assistant_runs:
        st.divider()
        st.markdown("### 📊 Session Stats")
        n_total    = len(assistant_runs)
        n_rewrite  = sum(1 for r in assistant_runs if r.get("rewritten"))
        n_direct   = n_total - n_rewrite
        lifts      = [
            (r.get("critique_final", {}).get("total", 0) or 0) -
            (r.get("critique_original", {}).get("total", 0) or 0)
            for r in assistant_runs if r.get("rewritten")
        ]
        avg_lift   = sum(lifts) / len(lifts) if lifts else 0
        avg_lat    = sum(r.get("latency", 0) or 0 for r in assistant_runs) / n_total
        routes     = {}
        for r in assistant_runs:
            rt = r.get("route", "?")
            routes[rt] = routes.get(rt, 0) + 1

        st.markdown(f"""
        <div style='font-size:12px;line-height:1.8'>
        <div>💬 <b>Prompts:</b> {n_total}</div>
        <div>✨ <b>Rewritten:</b> {n_rewrite} ({n_rewrite/n_total:.0%})</div>
        <div>✅ <b>Direct:</b> {n_direct} ({n_direct/n_total:.0%})</div>
        <div>📈 <b>Avg score lift:</b> {avg_lift:+.1f} / 20</div>
        <div>⚡ <b>Avg latency:</b> {avg_lat:.1f}s</div>
        </div>
        """, unsafe_allow_html=True)

        route_str = "  ".join(f"`{k}:{v}`" for k, v in sorted(routes.items()))
        st.caption(f"Routes: {route_str}")


# ─────────────────────────────────────────────────────────────
# PIPELINE RUNNER
# ─────────────────────────────────────────────────────────────
def run_peisr(query: str) -> dict:
    """
    Gated pipeline:
      1. Score prompt quality
      2a. Score >= threshold  → DIRECT answer (1 Gemini call, no A/B, no judge)
      2b. Score <  threshold  → Rewrite → generate BASELINE + ENHANCED → judge → best
    """
    q        = query.strip()
    auto_t   = st.session_state.get("auto_temp", True)
    # auto_thr = st.session_state.get("auto_threshold", True)
    # thr_slider = int(st.session_state.get("rewrite_threshold", 15))

    t0 = time.time()

    # Build prompt-only memory (last 6 prompts)
    prompt_history = []

    for m in st.session_state.messages:
        if m["role"] == "assistant" and m.get("run_data"):
            rd = m["run_data"]

            if rd.get("rewritten"):
                prompt_history.append(rd.get("enhanced_prompt"))
            else:
                prompt_history.append(rd.get("original_prompt"))

    # Keep last 6 prompts only
    prompt_history = prompt_history[-6:]

    # Run the gated pipeline (critique happens inside, branches on score)

    # Resolve short confirmations like "yes"
    LOW_WORD_THRESHOLD = 2
    CONFIRM_WORDS = {"yes", "yeah", "yep", "sure", "ok", "okay"}

    if (
        len(q.split()) <= LOW_WORD_THRESHOLD
        and q.lower() in CONFIRM_WORDS
    ):
        # Find last assistant message
        last_assistant = None
        for m in reversed(st.session_state.messages[:-1]):
            if m["role"] == "assistant":
                last_assistant = m["content"]
                break

        if last_assistant and last_assistant.strip().endswith("?"):
            # Convert confirmation into explicit instruction
            q = last_assistant

    enhanced = run_pipeline(
        q, history=prompt_history, variant="ABC",
        temp_mode="auto" if auto_t else "fixed",
        temperature=float(st.session_state.get("temperature", 0.4)),
        rewrite_threshold=int(st.session_state.get("rewrite_threshold", 15)),
        max_rounds=2,
    )

    rewritten       = not enhanced.prompt_passed_gate
    intent_result   = classify_intent(q, allow_llm=False)

    # ── DIRECT PATH: prompt was good enough ──────────────────────────────
    if not rewritten:
        heur_orig  = heuristic_prompt_critique(q)
        run_id_src = "|".join([q, enhanced.route, f"{enhanced.temperature_used:.3f}", enhanced.answer])
        run_id     = hashlib.sha256(run_id_src.encode()).hexdigest()

        return {
            "run_id": run_id,
            "comparison_id": str(uuid.uuid4()),
            "session_id": st.session_state.session_id,
            "user_tag": (st.session_state.get("user_tag", "") or "").strip(),
            "route": enhanced.route,
            "intent_reason": intent_result.reason,
            "temperature_used": enhanced.temperature_used,
            "threshold_used": enhanced.rewrite_threshold_used,
            "rewritten": False,
            "prompt_passed_gate": True,
            "original_prompt": q,
            "enhanced_prompt": q,
            "original_response": enhanced.answer,
            "enhanced_response": None,
            "best_output": enhanced.answer,
            "shown_as": "Direct (prompt passed quality gate)",
            "winner_label": "—",
            "critique_original": enhanced.critique_original or {},
            "critique_final":    enhanced.critique_original or {},
            "heur_original": heur_orig,
            "heur_enhanced": None,
            "llm_judge": None,
            "heur_judge": None,
            "trace": [],
            "model_used": getattr(__import__("gemini_client"), "LAST_MODEL_USED", "unknown"),
            "latency": round(time.time() - t0, 2),
        }

    # ── REWRITE PATH: prompt needed enhancement ───────────────────────────
    # Also generate a BASELINE answer (original prompt) for A/B comparison

    # Resolve short confirmations like "yes"
    LOW_WORD_THRESHOLD = 2
    CONFIRM_WORDS = {"yes", "yeah", "yep", "sure", "ok", "okay"}

    if (
        len(q.split()) <= LOW_WORD_THRESHOLD
        and q.lower() in CONFIRM_WORDS
    ):
        # Find last assistant message
        last_assistant = None
        for m in reversed(st.session_state.messages[:-1]):
            if m["role"] == "assistant":
                last_assistant = m["content"]
                break

        if last_assistant and last_assistant.strip().endswith("?"):
            # Convert confirmation into explicit instruction
            q = last_assistant

    base = run_pipeline(q, history=prompt_history, variant="BASELINE",
                        temp_mode="fixed", temperature=enhanced.temperature_used)

    heur_orig = heuristic_prompt_critique(q)
    heur_enh  = heuristic_prompt_critique(enhanced.enhanced_prompt)

    try:
        llm_j     = judge_pair(q, base.answer, enhanced.answer)
        llm_judge = {"X": llm_j.X, "Y": llm_j.Y, "winner": llm_j.winner,
                     "reason": llm_j.reason, "judge_type": "llm"}
    except Exception as e:
        llm_judge = {"error": str(e), "judge_type": "llm", "winner": "tie"}

    heur_judge = heuristic_judge_pair(q, base.answer, enhanced.answer)

    winner = llm_judge.get("winner", "tie")
    if winner in ("Y", "tie"):
        best_output = enhanced.answer
        shown_as    = "Enhanced (Y) — winner"
    else:
        best_output = base.answer
        shown_as    = "Original (X) — winner"

    run_id_src = "|".join([q, enhanced.route, f"{enhanced.temperature_used:.3f}",
                            str(enhanced.rewrite_threshold_used),
                            enhanced.enhanced_prompt, base.answer, enhanced.answer])
    run_id = hashlib.sha256(run_id_src.encode()).hexdigest()

    return {
        "run_id": run_id,
        "comparison_id": str(uuid.uuid4()),
        "session_id": st.session_state.session_id,
        "user_tag": (st.session_state.get("user_tag", "") or "").strip(),
        "route": enhanced.route,
        "intent_reason": intent_result.reason,
        "temperature_used": enhanced.temperature_used,
        "threshold_used": enhanced.rewrite_threshold_used,
        "rewritten": True,
        "prompt_passed_gate": False,
        "original_prompt": q,
        "enhanced_prompt": enhanced.enhanced_prompt,
        "original_response": base.answer,
        "enhanced_response": enhanced.answer,
        "best_output": best_output,
        "shown_as": shown_as,
        "winner_label": winner,
        "critique_original": enhanced.critique_original or {},
        "critique_final":    enhanced.critique_final or {},
        "heur_original": heur_orig,
        "heur_enhanced": heur_enh,
        "llm_judge": llm_judge,
        "heur_judge": heur_judge,
        "trace": enhanced.trace or [],
        "model_used": getattr(__import__("gemini_client"), "LAST_MODEL_USED", "unknown"),
        "latency": round(time.time() - t0, 2),
    }


# ─────────────────────────────────────────────────────────────
# BLACK BOX PANEL RENDERER
# ─────────────────────────────────────────────────────────────
def render_black_box(d: dict):
    if not d:
        st.markdown("""
        <div style='text-align:center;padding:60px 20px;color:#5a5a7a'>
          <div style='font-size:36px;margin-bottom:12px'>🔭</div>
          <div style='font-size:13px;line-height:1.6'>Send a message to<br/>inspect the backend here.</div>
        </div>""", unsafe_allow_html=True)
        return

    run_short = d["run_id"][:10]
    st.markdown(f"<div class='bb-header'>🔭 BLACK BOX &nbsp;<span>#{run_short}…</span></div>", unsafe_allow_html=True)

    tabs = st.tabs(["📊 Decision", "📝 Prompts", "⚔️ Compare", "⚖️ Judge", "🔄 Trace", "📋 Logs"])

    # ── DECISION ──
    with tabs[0]:
        crit   = d.get("critique_original", {})
        scores = crit.get("scores", {})
        total  = crit.get("total", sum(scores.values()) if scores else 0)
        max_t  = 20
        pct    = round(total / max_t * 100) if max_t else 0
        sc_col = "#22c55e" if pct >= 70 else "#f59e0b" if pct >= 45 else "#ef4444"
        thr_v  = d.get("threshold_used", "?")

        st.markdown(f"""
        <div class='bb-section'>
          <div class='bb-section-title'>Prompt Quality Gate</div>
          <div style='display:flex;align-items:center;gap:10px;margin:8px 0'>
            <div class='score-bar-outer'>
              <div class='score-bar-inner' style='width:{pct}%;background:{sc_col}'></div>
            </div>
            <span style='font-size:13px;font-weight:700;color:{sc_col};min-width:44px;text-align:right'>{total}/{max_t}</span>
          </div>
          <div class='bb-kv'><span class='bb-k'>Threshold</span><span class='bb-v'>{thr_v} — rewrite triggers if below</span></div>
          <div class='bb-kv'><span class='bb-k'>Gate result</span><span class='bb-v'>{"✅ PASSED — answered directly" if d.get("prompt_passed_gate") else "❌ FAILED — rewrite triggered"}</span></div>
          <div class='bb-kv'><span class='bb-k'>Route</span><span class='bb-v'><span class='badge badge-route'>{d["route"]}</span></span></div>
          <div class='bb-kv'><span class='bb-k'>Rewritten</span><span class='bb-v'>{"⬜ No — prompt was good enough" if not d["rewritten"] else "✅ Yes"}</span></div>
          <div class='bb-kv'><span class='bb-k'>Winner</span><span class='bb-v'>{d["winner_label"].upper()}</span></div>
          <div class='bb-kv'><span class='bb-k'>Shown as</span><span class='bb-v'>{d["shown_as"]}</span></div>
          <div class='bb-kv'><span class='bb-k'>Temp used</span><span class='bb-v'>{d["temperature_used"]:.2f}</span></div>
          <div class='bb-kv'><span class='bb-k'>Latency</span><span class='bb-v'>{d["latency"]}s</span></div>
        </div>""", unsafe_allow_html=True)

        if scores:
            st.markdown("<div class='bb-section'><div class='bb-section-title'>Rubric Breakdown (Original Prompt)</div>", unsafe_allow_html=True)
            for k, v in scores.items():
                bw  = int(v / 5 * 100)
                col = "#22c55e" if v >= 4 else "#f59e0b" if v >= 2 else "#ef4444"
                st.markdown(f"""
                <div style='display:flex;align-items:center;gap:8px;margin:5px 0;font-size:12px'>
                  <span style='min-width:64px;color:#9090a8'>{k}</span>
                  <div class='score-bar-outer'><div class='score-bar-inner' style='width:{bw}%;background:{col}'></div></div>
                  <span style='color:{col};font-weight:700;min-width:18px'>{v}</span>
                </div>""", unsafe_allow_html=True)
            weakest = crit.get("weakest", "")
            edit    = crit.get("edit", "")
            if weakest:
                st.markdown(f"<div style='font-size:11px;color:#9090a8;margin-top:8px'>Weakest: <b style='color:#f59e0b'>{weakest}</b></div>", unsafe_allow_html=True)
            if edit:
                st.markdown(f"<div style='font-size:11px;color:#c8c8e0;margin-top:4px'>💡 {edit}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

    # ── PROMPTS ──
    with tabs[1]:
        st.markdown(f"""
        <div class='bb-section'>
          <div class='bb-section-title'>Original Prompt</div>
          <div class='bb-box'>{d["original_prompt"]}</div>
        </div>""", unsafe_allow_html=True)

        if d["rewritten"]:
            c_final = d.get("critique_final", {})
            f_scores = c_final.get("scores", {})
            f_total  = c_final.get("total", sum(f_scores.values()) if f_scores else 0)
            f_pct    = round(f_total / 20 * 100) if f_total else 0
            f_col    = "#22c55e" if f_pct >= 70 else "#f59e0b" if f_pct >= 45 else "#ef4444"

            st.markdown(f"""
            <div class='bb-section'>
              <div class='bb-section-title'>✨ Enhanced Prompt</div>
              <div class='bb-box b'>{d["enhanced_prompt"]}</div>
            </div>
            <div class='bb-section'>
              <div class='bb-section-title'>Quality After Rewrite</div>
              <div style='display:flex;align-items:center;gap:10px;margin:6px 0'>
                <div class='score-bar-outer'><div class='score-bar-inner' style='width:{f_pct}%;background:{f_col}'></div></div>
                <span style='color:{f_col};font-weight:700'>{f_total}/20</span>
              </div>
            </div>""", unsafe_allow_html=True)
        else:
            st.info("No rewrite — prompt quality was sufficient.")

    # ── COMPARE ──
    with tabs[2]:
        if d["rewritten"]:
            st.markdown(f"""
            <div class='bb-section'>
              <div class='bb-section-title'><span style='color:#60a5fa'>▐ Response X</span> &nbsp;— Original prompt</div>
              <div class='bb-box a'>{d["original_response"]}</div>
            </div>
            <div class='bb-section'>
              <div class='bb-section-title'><span style='color:#a78bfa'>▐ Response Y</span> &nbsp;— Enhanced prompt</div>
              <div class='bb-box b'>{d["enhanced_response"]}</div>
            </div>
            <div class='bb-section'>
              <div class='bb-section-title'><span style='color:#22c55e'>▐ Best Output</span> &nbsp;— Shown to user</div>
              <div class='winner-tag' style='margin-bottom:8px'>✓ Winner: {d["winner_label"].upper()} · {d["shown_as"]}</div>
              <div class='bb-box winner'>{d["best_output"]}</div>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class='bb-section'>
              <div class='bb-section-title'><span style='color:#22c55e'>▐ Direct Response</span> &nbsp;— No A/B needed</div>
              <div style='margin-bottom:8px;font-size:12px;color:#9090a8'>
                ✅ Prompt passed the quality gate — answered directly with a single Gemini call.
                No baseline comparison or judging was needed.
              </div>
              <div class='bb-box winner'>{d["best_output"]}</div>
            </div>""", unsafe_allow_html=True)

    # ── JUDGE ──
    with tabs[3]:
        llm_j  = d.get("llm_judge") or {}
        heur_j = d.get("heur_judge") or {}

        if not d.get("rewritten"):
            st.markdown("""
            <div class='bb-section' style='color:#9090a8;font-size:12px'>
              ✅ No judging needed — prompt passed the quality gate and was answered directly.<br/>
              A/B comparison only runs when a rewrite is triggered.
            </div>""", unsafe_allow_html=True)
        elif not (show_judge or is_admin):
            st.info("🔒 Judge details visible in admin mode only.")
        else:
            w = llm_j.get("winner", "?")
            r = llm_j.get("reason", "")
            st.markdown(f"<div class='winner-tag' style='margin-bottom:12px'>LLM Judge Winner: {w.upper()} — {r}</div>", unsafe_allow_html=True)

            c1, c2 = st.columns(2)
            for col_ui, key, label, bar_col in [(c1,"X","Response X","#60a5fa"),(c2,"Y","Response Y","#a78bfa")]:
                with col_ui:
                    block = llm_j.get(key, {})
                    sc_sum = sum(int(v) for k, v in block.items() if k not in ("notes",))
                    st.markdown(f"**{label}** — {sc_sum}/20")
                    for k, v in block.items():
                        if k == "notes":
                            continue
                        bw = int(int(v)/5*100)
                        st.markdown(f"<div style='font-size:11px;display:flex;gap:6px;margin:3px 0'><span style='min-width:55px;color:#9090a8'>{k}</span><div class='score-bar-outer'><div class='score-bar-inner' style='width:{bw}%;background:{bar_col}'></div></div><span style='color:{bar_col}'>{v}</span></div>", unsafe_allow_html=True)
                    st.caption(block.get("notes", ""))

            with st.expander("Raw LLM Judge JSON"):
                st.json(llm_j)
            with st.expander("Heuristic Judge JSON"):
                st.json(heur_j)
            with st.expander("Heuristic Prompt Critiques"):
                cc1, cc2 = st.columns(2)
                with cc1:
                    st.caption("Original")
                    st.json(d.get("heur_original", {}))
                with cc2:
                    st.caption("Enhanced")
                    st.json(d.get("heur_enhanced", {}))

    # ── TRACE ──
    with tabs[4]:
        trace = d.get("trace") or []
        if trace:
            for t in trace:
                rnd    = t.get("round", "?")
                t_sc   = t.get("total", "?")
                t_thr  = d.get("threshold_used", "?")
                verdict = "✅ passed" if (isinstance(t_sc,(int,float)) and isinstance(t_thr,(int,float)) and t_sc >= t_thr) else "🔄 rewrite triggered"
                st.markdown(f"""
                <div class='trace-iter'>
                  <div class='trace-label'>Round {rnd} &nbsp;|&nbsp; Score {t_sc} / Threshold {t_thr} &nbsp;{verdict}</div>
                  <div class='bb-kv'><span class='bb-k'>Weakest</span><span class='bb-v' style='color:#f59e0b'>{t.get("weakest","—")}</span></div>
                  <div class='bb-kv'><span class='bb-k'>Suggested edit</span><span class='bb-v'>{t.get("edit","—")}</span></div>
                  <div style='font-size:10px;color:#9090a8;margin-top:6px'>Prompt at this round:</div>
                  <div class='bb-box' style='margin-top:4px;font-size:11px'>{t.get("prompt","—")}</div>
                </div>""", unsafe_allow_html=True)
        else:
            st.info("No refinement trace (prompt passed on first check or was SOCIAL route).")

    # ── LOGS ──
    with tabs[5]:
        st.markdown(f"""
        <div class='bb-section'>
          <div class='bb-section-title'>Run Metadata</div>
          <div class='bb-kv'><span class='bb-k'>run_id</span><span class='bb-v' style='font-size:10px;font-family:monospace'>{d["run_id"]}</span></div>
          <div class='bb-kv'><span class='bb-k'>session_id</span><span class='bb-v' style='font-size:10px;font-family:monospace'>{d["session_id"][:20]}…</span></div>
          <div class='bb-kv'><span class='bb-k'>route</span><span class='bb-v'>{d["route"]}</span></div>
          <div class='bb-kv'><span class='bb-k'>intent reason</span><span class='bb-v'>{d["intent_reason"]}</span></div>
          <div class='bb-kv'><span class='bb-k'>rewritten</span><span class='bb-v'>{d["rewritten"]}</span></div>
          <div class='bb-kv'><span class='bb-k'>winner</span><span class='bb-v'>{d["winner_label"]}</span></div>
          <div class='bb-kv'><span class='bb-k'>latency</span><span class='bb-v'>{d["latency"]}s</span></div>
        </div>""", unsafe_allow_html=True)

        st.markdown("<div class='bb-section'><div class='bb-section-title'>Human Rating → Database</div>", unsafe_allow_html=True)
        rc1, rc2 = st.columns(2)
        with rc1:
            s_orig = st.radio("Score: Original", [1,2,3,4,5], index=2, horizontal=True, key=f"so_{d['run_id'][:8]}")
        with rc2:
            s_enh  = st.radio("Score: Enhanced", [1,2,3,4,5], index=2, horizontal=True, key=f"se_{d['run_id'][:8]}")
        pick  = st.radio("Which is better?", ["ORIGINAL","ENHANCED","TIE"], horizontal=True, key=f"pk_{d['run_id'][:8]}")
        notes = st.text_area("Notes", height=68, key=f"nt_{d['run_id'][:8]}")

        if st.button("💾 Save rating to DB", key=f"save_{d['run_id'][:8]}", use_container_width=True):
            now = time.time()
            if now - float(st.session_state.last_submit_ts) < 3.0:
                st.warning("Wait a moment before re-submitting.")
            elif d["comparison_id"] in st.session_state.saved_ids:
                st.info("Already saved.")
            else:
                try:
                    save_comparison(
                        comparison_id=d["comparison_id"], run_id=d["run_id"],
                        session_id=d["session_id"],
                        human_rater=(st.session_state.get("rater_name","") or "anonymous"),
                        user_tag=d.get("user_tag",""),
                        variant="ABC", temp_mode="auto", threshold_mode="auto", model_mode="gemini",
                        user_input=d["original_prompt"], route_predicted=d["route"],
                        temperature_used=d["temperature_used"],
                        rewrite_threshold_used=d["threshold_used"],
                        rewritten=bool(d["rewritten"]),
                        original_prompt=d["original_prompt"],
                        original_response=d["original_response"],
                        original_prompt_critique=d.get("critique_original",{}),
                        original_prompt_heuristic=d.get("heur_original",{}),
                        enhanced_prompt=d["enhanced_prompt"],
                        enhanced_response=d["enhanced_response"],
                        enhanced_prompt_critique=d.get("critique_final",{}),
                        enhanced_prompt_heuristic=d.get("heur_enhanced",{}),
                        response_llm_judge=d.get("llm_judge",{}),
                        response_heuristic_judge=d.get("heur_judge",{}),
                        human_score_original=int(s_orig),
                        human_score_enhanced=int(s_enh),
                        human_pick=pick, human_notes=notes,
                        model_used=d.get("model_used",""),
                    )
                    st.session_state.last_submit_ts = now
                    st.session_state.saved_ids.add(d["comparison_id"])
                    st.success("✅ Saved!")
                except Exception as e:
                    st.error(f"DB error: {e}")
        st.markdown("</div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# MAIN UI LAYOUT
# ─────────────────────────────────────────────────────────────
st.markdown("""
<div class='topbar'>
  <div>
    <div class='topbar-title'>⚡ PEISR Chat</div>
    <div class='topbar-sub'>Prompt Enhancement via Iterative Self-Refinement</div>
  </div>
</div>""", unsafe_allow_html=True)

chat_col, panel_col = st.columns([4, 2], gap="medium")

# ── CHAT ──────────────────────────────────────────────────────
messages = st.session_state.messages

# Welcome message on first load
if not messages:
    st.markdown("""
    <div class='msg-row assistant'>
        <div class='avatar assistant'>P</div>
        <div>
        <div class='bubble assistant'>
            👋 Welcome to <b>PEISR Chat</b>.<br/><br/>
            Type any prompt below — clear or messy. I'll automatically score it,
            decide if a rewrite will help, generate both versions if so, judge them,
            and show you the best answer.<br/><br/>
        </div>
        </div>
    </div>""", unsafe_allow_html=True)

# Render history
for i, msg in enumerate(messages):
    role = msg["role"]
    content = msg["content"]
    run_d = msg.get("run_data")

    row_chat, row_panel = st.columns([4, 2], gap="medium")

    # ───────────────── USER MESSAGE ─────────────────
    if role == "user":
        with row_chat:
            original = content
            rewritten = None

            if i + 1 < len(messages):
                next_msg = messages[i + 1]
                rd = next_msg.get("run_data")
                if rd and rd.get("rewritten"):
                    rewritten = rd.get("enhanced_prompt")

            if rewritten:
                show_key = f"show_orig_{i}"
                if show_key not in st.session_state:
                    st.session_state[show_key] = False

                # Right-aligned small toggle ABOVE prompt
                toggle_left, toggle_right = st.columns([6, 1])
                with toggle_right:
                    if st.button("See original", key=f"toggle_{i}"):
                        st.session_state[show_key] = not st.session_state[show_key]

                if st.session_state[show_key]:
                    st.markdown(f"""
                    <div class='msg-row user'>
                    <div class='avatar user' style="opacity:0;"></div>
                    <div>
                        <div class='bubble user' style="opacity:0.45;">
                        {original}
                        </div>
                    </div>
                    </div>
                    """, unsafe_allow_html=True)

                # Rewritten bubble
                st.markdown(f"""
                <div class='msg-row user'>
                <div class='avatar user'>U</div>
                <div><div class='bubble user'>{rewritten}</div></div>
                </div>
                """, unsafe_allow_html=True)

            else:
                st.markdown(f"""
                <div class='msg-row user'>
                  <div class='avatar user'>U</div>
                  <div><div class='bubble user'>{original}</div></div>
                </div>
                """, unsafe_allow_html=True)

    # ───────────────── ASSISTANT MESSAGE ─────────────────
    else:
        with row_chat:
            route = run_d.get("route", "") if run_d else ""
            lat   = run_d.get("latency", "") if run_d else ""

            if run_d:
                best = run_d.get("best_output")
                enhanced_out = run_d.get("enhanced_response")
                original_out = run_d.get("original_response")

                if best == enhanced_out:
                    b_txt = "Enhanced"
                    b_cls = "badge-rewrite"
                else:
                    b_txt = "Original"
                    b_cls = "badge-direct"
            else:
                b_txt = ""
                b_cls = ""

            st.markdown(f"""
            <div class='msg-row assistant'>
              <div class='avatar assistant'>P</div>
              <div>
                <div class='bubble assistant'>{content}</div>
                <div class='meta-row'>
                  <span class='badge {b_cls}'>{b_txt}</span>
                  <span class='badge badge-route'>{route}</span>
                  <span>{lat}s</span>
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            if run_d:
                if st.button("🔭 Inspect", key=f"inspect_{i}"):
                    if st.session_state.get("active_run") == i:
                        st.session_state.active_run = None
                    else:
                        st.session_state.active_run = i

            # ── Inline quick rating ────────────────────────────────
            if run_d:
                cid = run_d.get("comparison_id", "")
                already_rated = cid in st.session_state.get("inline_rated_ids", set())

                if already_rated:
                    st.markdown("<div style='font-size:11px;color:#22c55e;margin-top:4px'>✅ Rated</div>", unsafe_allow_html=True)
                else:
                    with st.expander("⭐ Rate this response", expanded=False):
                        r_col1, r_col2 = st.columns([1, 1])
                        with r_col1:
                            stars = st.radio(
                                "Quality", [1, 2, 3, 4, 5],
                                index=2, horizontal=True,
                                key=f"inline_stars_{i}",
                            )
                        with r_col2:
                            options = ["ENHANCED", "ORIGINAL", "TIE"] if run_d.get("rewritten") else ["GOOD", "NEUTRAL", "POOR"]
                            pick = st.radio(
                                "Which was better?" if run_d.get("rewritten") else "Response quality",
                                options, horizontal=True,
                                key=f"inline_pick_{i}",
                            )
                        inline_notes = st.text_input("Notes (optional)", key=f"inline_notes_{i}", placeholder="Any comments...")
                        if st.button("Submit rating", key=f"inline_submit_{i}", use_container_width=True):
                            try:
                                save_inline_rating(
                                    comparison_id=cid,
                                    run_id=run_d.get("run_id", ""),
                                    session_id=run_d.get("session_id", ""),
                                    human_rater=(st.session_state.get("rater_name", "") or "anonymous"),
                                    stars=int(stars),
                                    pick=pick,
                                    notes=inline_notes,
                                )
                                if "inline_rated_ids" not in st.session_state:
                                    st.session_state.inline_rated_ids = set()
                                st.session_state.inline_rated_ids.add(cid)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Rating error: {e}")

        # Black box aligned with assistant message
        if st.session_state.get("active_run") == i:
            with row_panel:
                render_black_box(run_d)

st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

# ── Input bar ──

# Ensure pending_query exists
if "pending_query" not in st.session_state:
    st.session_state.pending_query = None

# Align chat input width with message column
input_left, input_right = st.columns([4, 2], gap="medium")

with input_left:
    user_input = st.chat_input("Type a prompt…")

if user_input:
    q = user_input.strip()

    st.session_state.pending_query = q
    st.session_state.messages.append({
        "role": "user",
        "content": q,
        "run_data": None
    })
    st.rerun()

# Process pending query
if st.session_state.pending_query:
    q = st.session_state.pending_query
    st.session_state.pending_query = None

    with st.spinner("🧠 Scoring → enhancing → generating → judging…"):
        run_data = run_peisr(q)

    st.session_state.messages.append({
        "role": "assistant",
        "content": run_data["best_output"],
        "run_data": run_data,
    })

    st.session_state.last_run_data = run_data
    st.rerun()
