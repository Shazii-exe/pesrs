# gemini_client.py
# Primary: Gemini API (with fallback pool)
# Optional local: Ollama (ONLY when explicitly selected)

import os
import time
import json
import re
import logging

# NOTE:
# - On Streamlit Cloud, do NOT rely on .env
# - app.py will inject st.secrets into os.environ
# - locally, you can still use dotenv if you want

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s [PEISR] %(message)s")
log = logging.getLogger("peisr")

# ── Provider selection ─────────────────────────────────────────
# Use MODEL_PROVIDER to control behavior:
#   MODEL_PROVIDER=gemini  -> Gemini ONLY (no Ollama fallback)
#   MODEL_PROVIDER=ollama  -> Ollama ONLY
#   unset                 -> Gemini if available, else error
MODEL_PROVIDER = (os.getenv("MODEL_PROVIDER") or "").strip().lower()

# ── Gemini setup ───────────────────────────────────────────────
_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
_gemini_available = False
client = None
types = None

if _API_KEY:
    try:
        from google import genai as _genai
        from google.genai import types as _types
        client = _genai.Client(api_key=_API_KEY)
        types = _types
        _gemini_available = True
        log.info("Gemini client initialized.")
    except Exception as e:
        _gemini_available = False
        log.warning(f"Gemini SDK init failed: {e}")

# ── Ollama setup (local-only) ──────────────────────────────────
import requests as _requests

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

# ── Tracks which model was used last (for logging/paper) ───────
LAST_MODEL_USED = "none"

# ── Gemini model pools ─────────────────────────────────────────
FAST_POOL = [
    "gemini-2.5-flash",
    "gemini-flash-latest",
    "gemini-2.0-flash",
    "gemini-2.0-flash-001",
    "gemini-2.5-flash-lite",
    "gemini-flash-lite-latest",
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash-lite-001",
]

QUALITY_POOL = [
    "gemini-2.5-pro",
    "gemini-pro-latest",
    "gemini-3-pro-preview",
    "gemini-exp-1206",
    "gemini-2.5-flash",
]

_seen = set()
_FULL_GEMINI_FALLBACK = []
for _m in FAST_POOL + QUALITY_POOL:
    if _m not in _seen:
        _FULL_GEMINI_FALLBACK.append(_m)
        _seen.add(_m)

_QUOTA_SIGNALS = (
    "429", "quota", "rate", "limit", "exhausted",
    "unavailable", "503", "403", "not found", "404",
    "timeout", "deadline", "overloaded",
)

def _is_quota_error(err: str) -> bool:
    e = (err or "").lower()
    return any(s in e for s in _QUOTA_SIGNALS)

# ── JSON parser ────────────────────────────────────────────────
def _parse_json(text: str) -> dict:
    try:
        return json.loads(text)
    except Exception:
        pass

    cleaned = re.sub(r"```(?:json)?|```", "", (text or "")).strip()
    try:
        return json.loads(cleaned)
    except Exception:
        pass

    m = re.search(r"\{[\s\S]+\}", text or "")
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass

    raise ValueError(f"Could not parse JSON:\n{(text or '')[:300]}")

# ── Ollama call ────────────────────────────────────────────────
def _call_ollama(system: str, user: str, temperature: float) -> str:
    global LAST_MODEL_USED
    prompt = f"{system}\n\n{user}"
    resp = _requests.post(
        OLLAMA_URL,
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        },
        timeout=120,
    )
    resp.raise_for_status()
    LAST_MODEL_USED = f"ollama/{OLLAMA_MODEL}"
    log.info(f"✓ Ollama ({OLLAMA_MODEL}) succeeded")
    return resp.json()["response"].strip()

# ── Gemini call with model fallback ────────────────────────────
def _call_gemini(
    system: str,
    user: str,
    temperature: float,
    response_mime_type: str = None,
    max_attempts: int = 6,
) -> str:
    global LAST_MODEL_USED

    if not (_gemini_available and _API_KEY and client and types):
        raise RuntimeError("Gemini not available. Check GEMINI_API_KEY and SDK install.")

    seen = set()
    candidates = []
    for m in _FULL_GEMINI_FALLBACK:
        m = m.replace("models/", "").strip()
        if m and m not in seen:
            candidates.append(m)
            seen.add(m)

    errors = {}
    attempts = 0

    for model_name in candidates:
        if attempts >= max_attempts:
            break
        attempts += 1
        try:
            log.info(f"Trying Gemini [{attempts}] {model_name}")
            cfg = dict(system_instruction=system, temperature=temperature)
            if response_mime_type:
                cfg["response_mime_type"] = response_mime_type

            resp = client.models.generate_content(
                model=model_name,
                contents=user,
                config=types.GenerateContentConfig(**cfg),
            )
            text = (resp.text or "").strip()
            LAST_MODEL_USED = f"gemini/{model_name}"
            log.info(f"✓ Gemini {model_name} succeeded")
            return text

        except Exception as e:
            err_str = str(e)
            errors[model_name] = err_str
            log.warning(f"✗ Gemini {model_name} — {err_str[:140]}")
            time.sleep(min(0.5 * attempts, 3.0))
            continue

    summary = "; ".join(f"{m}: {e[:60]}" for m, e in list(errors.items())[:4])
    raise RuntimeError(f"All Gemini models failed: {summary}")

# ── Master router ──────────────────────────────────────────────
def _call(
    system: str,
    user: str,
    temperature: float,
    response_mime_type: str = None,
) -> str:
    provider = (os.getenv("MODEL_PROVIDER") or "").strip().lower()

    # 1) Explicit Gemini only (Streamlit Cloud safe)
    if provider == "gemini":
        return _call_gemini(system, user, temperature, response_mime_type)

    # 2) Explicit Ollama only (local)
    if provider == "ollama":
        return _call_ollama(system, user, temperature)

    # 3) Default: Gemini if possible, else fail with clear message
    if _gemini_available and _API_KEY:
        return _call_gemini(system, user, temperature, response_mime_type)

    raise RuntimeError(
        "No provider available. Set MODEL_PROVIDER=gemini and provide GEMINI_API_KEY "
        "(recommended for Streamlit Cloud), or set MODEL_PROVIDER=ollama for local."
    )

# ── Public API ─────────────────────────────────────────────────
def generate_text(system: str, user: str, temperature: float = 0.2) -> str:
    return _call(system=system, user=user, temperature=temperature)

def generate_json(system: str, user: str, temperature: float = 0.0) -> dict:
    # Attempt 1: JSON mime type (Gemini)
    if (os.getenv("MODEL_PROVIDER") or "").strip().lower() != "ollama":
        try:
            text = _call_gemini(
                system=system,
                user=user,
                temperature=temperature,
                response_mime_type="application/json",
            )
            return _parse_json(text)
        except Exception as e:
            log.warning(f"JSON-mime attempt failed ({str(e)[:80]}), retrying...")

    # Attempt 2: plain text + reinforced prompt
    user2 = user + "\n\nReturn valid JSON only. No markdown. No explanation."
    text = _call(system=system, user=user2, temperature=temperature)
    return _parse_json(text)