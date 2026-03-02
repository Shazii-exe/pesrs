from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

log = logging.getLogger("peisr")

from gemini_client import generate_text


def _detect_tone(text: str) -> str:
    """Returns 'casual' or 'formal' based on user's writing style."""
    casual_indicators = [
        "bro", "lol", "lmao", "omg", "idk", "tbh", "ngl", "wtf", "bruh",
        "u ", " ur ", "gonna", "wanna", "gotta", "kinda", "sorta", "dunno",
        "ok ", "okay", "yea", "yeah", "nah", "coz", "cus", "cause",
        "btw", "rn", "fr", "imo", "smh", "yk", "istg", "pls", "plz",
    ]
    text_lower = text.lower()
    casual_count = sum(1 for word in casual_indicators if word in text_lower)
    # Also check for lack of punctuation, very short sentences
    has_caps = any(c.isupper() for c in text[1:])
    ends_with_punct = text.strip()[-1] in ".?!" if text.strip() else False
    if casual_count >= 1 or (not ends_with_punct and len(text.split()) <= 8):
        return "casual"
    return "formal"


def _tone_instruction(tone: str) -> str:
    if tone == "casual":
        return (
            "\n\nIMPORTANT: The user is talking casually and informally. "
            "Match their energy — respond in a conversational, friendly tone. "
            "Avoid bullet points and formal structure. Write like you're texting a friend. "
            "Use simple language, keep it natural and warm."
        )
    return ""  # formal = default system prompt is fine
from intent_classifier import IntentResult, classify_intent, choose_temperature
from prompts import ANSWER_SYSTEM_BY_ROUTE
from rewriter import critique_prompt, self_refine_rewrite


@dataclass
class PipelineOutput:
    route: str
    enhance_mode: str           # NONE | LIGHT | FULL
    temperature_used: float
    original_prompt: str
    enhanced_prompt: str
    answer: str
    rewrite_threshold_used: Optional[int] = None
    critique_original: Optional[Dict[str, Any]] = None
    critique_final: Optional[Dict[str, Any]] = None
    trace: Optional[List[Dict[str, Any]]] = None
    # NEW — tells the UI whether rewrite was skipped because prompt was good
    prompt_passed_gate: bool = False


def _answer(prompt: str, route: str, temperature: float, history=None):
    base_system = ANSWER_SYSTEM_BY_ROUTE.get(route, "")

    # Detect tone from current prompt + recent history
    tone_context = prompt
    if history:
        recent_user = [t.get("content","") for t in history[-4:] if t.get("role")=="user"]
        tone_context = " ".join(recent_user) + " " + prompt
    tone = _detect_tone(tone_context)
    system = base_system + _tone_instruction(tone)

    # Build proper alternating USER/ASSISTANT conversation
    if history:
        conversation = ""
        for turn in history:
            role = turn.get("role", "user")
            turn_content = turn.get("content", "")
            if role == "user":
                conversation += f"USER: {turn_content}\n"
            else:
                conversation += f"ASSISTANT: {turn_content}\n"
        conversation += f"USER: {prompt}"
    else:
        conversation = f"USER: {prompt}"

    return generate_text(
        system=system,
        user=conversation,
        temperature=temperature,
    )


def run_pipeline(
    query: str,
    history: list | None = None,
    *,
    variant: str = "ABC",
    temperature: Optional[float] = None,
    temp_mode: str = "auto",
    rewrite_threshold: Optional[int] = None,
    max_rounds: int = 1,
) -> PipelineOutput:
    """
    PEISR gated pipeline:

    1. Classify intent → route + temperature
    2. Critique original prompt → score
    3. If score >= threshold  → DIRECT answer (no rewrite, no A/B, no judge)
    4. If score <  threshold  → Rewrite → generate both answers → return both
       (judging + winner selection happens in app.py)

    variant="BASELINE" bypasses all of this (used for comparison answer).
    """
    q = (query or "").strip()

    # ── BASELINE: raw answer, no routing, no critique ──────────────────────
    if variant.upper() == "BASELINE":
        intent = classify_intent(q, allow_llm=False)
        route  = intent.route
        temp   = float(temperature) if temperature is not None else choose_temperature(route)

        ans = _answer(
            q,
            route,
            temp,
            history=history
        )
        return PipelineOutput(
            route=route, enhance_mode="NONE",
            temperature_used=temp,
            rewrite_threshold_used=None,
            original_prompt=q, enhanced_prompt=q,
            answer=ans, prompt_passed_gate=True,
        )

    # ── Step 1: Intent classification ──────────────────────────────────────
    intent: IntentResult = classify_intent(q, allow_llm=True)
    route = intent.route

    if temp_mode == "auto":
        temperature_used = choose_temperature(route)
    else:
        temperature_used = float(temperature if temperature is not None else 0.4)

    # threshold_used is decided by the LLM inside critique_prompt() below

    # ── Step 2: Critique the original prompt ───────────────────────────────
    # Build context-aware critique input — only use previous USER prompts for context
    if history:
        context_block = ""
        for turn in history[-6:]:
            if turn.get("role") == "user":
                context_block += f"USER: {turn.get('content', '')}\n"

        critique_input = f"""Conversation so far:
{context_block}
Current user message:
{q}"""
    else:
        critique_input = q

    critique_orig = critique_prompt(critique_input)
    orig_total    = sum(critique_orig.scores.values())
    # Use LLM-decided threshold (dynamic, prompt-specific) or manual override
    if rewrite_threshold is None:
        threshold_used = critique_orig.threshold
    else:
        threshold_used = int(rewrite_threshold)

    critique_orig_dict = {
        "scores":           critique_orig.scores,
        "total":            orig_total,
        "weakest":          critique_orig.weakest,
        "edit":             critique_orig.edit,
        "reason":           critique_orig.reason,
        "threshold":        threshold_used,
        "threshold_reason": critique_orig.threshold_reason,
    }

    # ── Step 3: GATE — is the prompt good enough? ──────────────────────────
    # All routes go through the gate equally — no exceptions
    prompt_is_good = (orig_total >= threshold_used)

    if prompt_is_good:
        # ── DIRECT PATH: just answer, no rewrite, no A/B ──────────────────
        ans = _answer(q, route, temperature_used, history=history)
        return PipelineOutput(
            route=route,
            enhance_mode="NONE",
            temperature_used=temperature_used,
            rewrite_threshold_used=threshold_used,
            original_prompt=q,
            enhanced_prompt=q,          # same as original
            answer=ans,
            critique_original=critique_orig_dict,
            critique_final=critique_orig_dict,  # same, no rewrite
            trace=None,
            prompt_passed_gate=True,
        )

    # ── Step 4: REWRITE PATH ───────────────────────────────────────────────
    # Decide rewrite aggressiveness
    if route == "QA":
        enhance_mode = "LIGHT"
    else:
        enhance_mode = "FULL"

    mode = "light" if enhance_mode == "LIGHT" else "full"

    # Rewrite ONLY the current message — not the full conversation history
    final_prompt, trace = self_refine_rewrite(
        q,
        rewrite_threshold=threshold_used,
        max_rounds=max_rounds,
        mode=mode,
    )

    critique_final_obj  = critique_prompt(final_prompt)
    final_total         = sum(critique_final_obj.scores.values())

    # ── Rewrite quality guard ──────────────────────────────────────────────
    # If the rewrite made the prompt WORSE, fall back to the original
    if final_total < orig_total:
        log.warning(f"Rewrite quality guard triggered: score dropped {orig_total}→{final_total}, using original prompt")
        final_prompt = q
        critique_final_obj = critique_orig  # reuse original critique

    critique_final_dict = {
        "scores":           critique_final_obj.scores,
        "total":            sum(critique_final_obj.scores.values()),
        "weakest":          critique_final_obj.weakest,
        "edit":             critique_final_obj.edit,
        "reason":           critique_final_obj.reason,
        "threshold":        threshold_used,
        "threshold_reason": critique_final_obj.threshold_reason,
    }

    # Generate answer from the enhanced prompt
    # Extract only rewritten user message (last part)
    clean_final_prompt = final_prompt.split("Current user message:")[-1].strip()

    ans = _answer(clean_final_prompt, route, temperature_used, history=history)

    return PipelineOutput(
        route=route,
        enhance_mode=enhance_mode,
        temperature_used=temperature_used,
        rewrite_threshold_used=threshold_used,
        original_prompt=q,
        enhanced_prompt=clean_final_prompt,
        answer=ans,
        critique_original=critique_orig_dict,
        critique_final=critique_final_dict,
        trace=trace,
        prompt_passed_gate=False,
    )


# ── Backward-compatible helpers (used by interactive_ab scripts) ────────────

def refined_answer(
    query: str,
    *,
    task_tag: str = "auto",
    max_rounds: int = 2,
    rewrite_threshold: Optional[int] = None,
) -> Tuple[str, str, List[Dict[str, Any]]]:
    out = run_pipeline(
        query, variant="ABC", temp_mode="auto",
        rewrite_threshold=rewrite_threshold, max_rounds=max_rounds,
    )
    return out.enhanced_prompt, out.answer, (out.trace or [])


def baseline_answer(query: str, *, temperature: float = 0.4) -> str:
    out = run_pipeline(query, variant="BASELINE", temp_mode="fixed", temperature=temperature)
    return out.answer


def gated_answer(messy_query: str, temperature: float = 0.4, rewrite_threshold: Optional[int] = None):
    base     = run_pipeline(messy_query, variant="BASELINE", temp_mode="fixed", temperature=temperature)
    enhanced = run_pipeline(
        messy_query, variant="ABC", temp_mode="fixed", temperature=temperature,
        rewrite_threshold=rewrite_threshold, max_rounds=2,
    )
    rewritten  = enhanced.enhanced_prompt.strip() != messy_query.strip()
    orig_scores = (enhanced.critique_original or {}).get("scores", {})
    rew_scores  = (enhanced.critique_final or {}).get("scores", {})
    return (
        base.answer if rewritten else None,
        enhanced.answer, orig_scores,
        rew_scores if rewritten else None,
        rewritten,
        enhanced.enhanced_prompt if rewritten else None,
        type("Crit", (), {
            "scores": orig_scores,
            "weakest": (enhanced.critique_original or {}).get("weakest", ""),
            "edit":    (enhanced.critique_original or {}).get("edit", ""),
            "reason":  (enhanced.critique_original or {}).get("reason", ""),
        })(),
        type("Crit", (), {
            "scores": rew_scores,
            "weakest": (enhanced.critique_final or {}).get("weakest", ""),
            "edit":    (enhanced.critique_final or {}).get("edit", ""),
            "reason":  (enhanced.critique_final or {}).get("reason", ""),
        })() if rewritten else None,
    )