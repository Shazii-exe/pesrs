from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

from gemini_client import generate_text, generate_json
from prompts import CRITIQUE_SYSTEM, REVISE_SYSTEM, REWRITE_SYSTEM_FULL, REWRITE_SYSTEM_LIGHT
from intent_classifier import classify_intent


@dataclass
class CritiqueResult:
    scores: Dict[str, int]
    weakest: str
    edit: str
    reason: str
    threshold: int         # LLM-decided, prompt-specific
    threshold_reason: str  # why this threshold was chosen


def critique_prompt(prompt: str) -> CritiqueResult:
    user = f"Original prompt:\n{prompt}\n"

    data = generate_json(
        system=CRITIQUE_SYSTEM,
        user=user,
        temperature=0.0,
    )

    # Clamp threshold to valid range in case model goes out of bounds
    raw_threshold = data.get("threshold", 13)
    threshold = int(max(4, min(20, raw_threshold)))

    return CritiqueResult(
        scores=data["scores"],
        weakest=data["weakest"],
        edit=data["edit"],
        reason=data["reason"],
        threshold=threshold,
        threshold_reason=data.get("threshold_reason", ""),
    )


def rewrite_once(original_prompt: str, critique: CritiqueResult) -> str:
    # Safety guard
    if "json" in critique.edit.lower():
        edit = "Make the prompt clearer and better structured while preserving intent."
    else:
        edit = critique.edit

    user = (
        f"Original prompt:\n{original_prompt}\n\n"
        f"Critic suggestion:\n{edit}\n"
    )

    return generate_text(
        system=REVISE_SYSTEM,
        user=user,
        temperature=0.2,
    )


def rewrite_prompt(original_prompt: str, mode: str = "full") -> str:
    """Option B (conditional editor prompt): rewrite with explicit SOCIAL passthrough."""
    route = classify_intent(original_prompt, allow_llm=False).route
    if route == "SOCIAL":
        return original_prompt.strip()

    system = REWRITE_SYSTEM_FULL if mode == "full" else REWRITE_SYSTEM_LIGHT
    return generate_text(system=system, user=original_prompt, temperature=0.2).strip()


def self_refine_rewrite(
    original_prompt: str,
    *,
    rewrite_threshold: int = 15,
    max_rounds: int = 1,   # ignored now
    mode: str = "full",
):
    trace = []

    current = original_prompt.strip()

    # Step 1: critique once
    crit = critique_prompt(current)
    total = sum(crit.scores.values())

    trace.append({
        "round": 1,
        "prompt": current,
        "scores": crit.scores,
        "total": total,
        "weakest": crit.weakest,
        "edit": crit.edit,
        "reason": crit.reason
    })

    # Step 2: revise only if below threshold
    if total < rewrite_threshold:
        revised = rewrite_once(current, crit).strip()
        return revised, trace

    return current, trace