"""LLM #2: Eligibility matcher - matches profile to schemes using rules + RAG + LLM."""
import json
import os
from typing import Dict, Any, List, Optional, Tuple

from backend.rules import check_rules
from backend.rag import search
from backend.llm import call_json
from backend.schemas import SchemeResult


def load_schemes() -> List[Dict[str, Any]]:
    """Load schemes from data/schemes.json."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    schemes_path = os.path.join(base_dir, "data", "schemes.json")
    with open(schemes_path, "r", encoding="utf-8") as f:
        return json.load(f)


def match_schemes(profile: Dict[str, Any], query_text: str) -> List[SchemeResult]:
    """
    Match user profile to schemes using rules + RAG + LLM.

    Args:
        profile: User profile dict (from extract_profile)
        query_text: Original user query for RAG search

    Returns:
        List of SchemeResult objects (without explanation - that's LLM #3)
        The LLM only provides source_quote; reason is set in Python.
    """
    # Load all schemes
    schemes = load_schemes()

    # Step 1: Run check_rules on all schemes
    scheme_verdicts = []
    for scheme in schemes:
        verdict, reasons, missing = check_rules(profile, scheme)
        scheme_verdicts.append({
            "scheme": scheme,
            "verdict": verdict,
            "python_reasons": reasons,
            "missing_fields": missing,
        })

    # Step 2: RAG search for context
    rag_results = search(query_text, k=8)

    # Build RAG score map: scheme_id -> max_score
    rag_scores = {}
    scheme_contexts = {}  # scheme_id -> list of context chunks
    for result in rag_results:
        # Handle both mock dict format and real chunk objects
        if isinstance(result, dict):
            scheme_id = result.get("scheme_id")
            score = result.get("score", 0.0)
            text = result.get("text", "")
        else:
            scheme_id = result.metadata.get("scheme_id")
            score = 1.0 - getattr(result, "distance", 0.0)
            text = result.text if hasattr(result, "text") else str(result)

        if scheme_id:
            if scheme_id not in rag_scores or score > rag_scores[scheme_id]:
                rag_scores[scheme_id] = score
            if scheme_id not in scheme_contexts:
                scheme_contexts[scheme_id] = []
            scheme_contexts[scheme_id].append(text)

    # Step 3: Rank schemes
    # Sort by: verdict priority (yes > maybe > no), then RAG score
    verdict_priority = {"yes": 0, "maybe": 1, "no": 2}

    for sv in scheme_verdicts:
        scheme_id = sv["scheme"]["id"]
        sv["rag_score"] = rag_scores.get(scheme_id, 0.0)

    scheme_verdicts.sort(key=lambda x: (verdict_priority[x["verdict"]], -x["rag_score"]))

    # Step 4: Select top 5
    # Priority: all "yes", then "maybe", then "no" only if high RAG score
    selected = []
    yes_count = sum(1 for sv in scheme_verdicts if sv["verdict"] == "yes")
    maybe_count = sum(1 for sv in scheme_verdicts if sv["verdict"] == "maybe")
    
    for sv in scheme_verdicts:
        if len(selected) >= 5:
            break
        verdict = sv["verdict"]
        if verdict == "yes":
            selected.append(sv)
        elif verdict == "maybe":
            selected.append(sv)
        elif verdict == "no" and sv["rag_score"] > 0.3:
            selected.append(sv)
    
    # Step 5: One LLM call for all selected schemes to get source_quotes ONLY
    if selected:
        selected = _enrich_with_llm(selected, profile, scheme_contexts)
    
    # Step 6: Build SchemeResult objects
    results = []
    for sv in selected:
        ...
    
    # NEW: Return ALL 10 schemes with verdicts, no top-5 cut
    # Step 4: One LLM call for ALL schemes to get source_quotes
    scheme_verdicts = _enrich_with_llm(scheme_verdicts, profile, scheme_contexts)
    
    # Step 5: Build SchemeResult objects for ALL 10 schemes
    results = []
    for sv in scheme_verdicts:
        scheme = sv["scheme"]
        verdict = sv["verdict"]
        # Reason is ALWAYS from Python (rules.py), never from LLM
        reason = sv["python_reasons"][0] if sv["python_reasons"] else "Rule check passed"
    
        # Add verification reasons from requires_verification
        verification_reasons = []
        for vr in scheme.get("requires_verification", []):
            verification_reasons.append(f"Needs verification: {vr.replace('_', ' ')}")
    
        if verification_reasons and verdict == "yes":
            verdict = "maybe"
        if verification_reasons:
            reason = verification_reasons[0]
    
        result = SchemeResult(
            scheme_id=scheme["id"],
            scheme=scheme["name"],
            eligible=verdict,
            reason=reason,
            benefit=scheme.get("benefit", ""),
            documents=scheme.get("documents", []),
            how_to_apply=scheme.get("how_to_apply", ""),
            official_link=scheme.get("official_link", ""),
            source_quote=sv.get("llm_source_quote", ""),
            explanation="",  # Will be filled by LLM #3
        )
        results.append(result)
    
    return results


def _enrich_with_llm(
    selected: List[Dict[str, Any]],
    profile: Dict[str, Any],
    scheme_contexts: Dict[str, List[str]]
) -> List[Dict[str, Any]]:
    """
    Single LLM call to generate source_quote for each selected scheme.
    The LLM must NOT provide reason - only source_quote.
    The verdict and reason come from Python (rules.py).
    """
    # Build context for LLM
    context_parts = []
    for sv in selected:
        scheme = sv["scheme"]
        scheme_id = scheme["id"]
        context_chunks = scheme_contexts.get(scheme_id, [])
        context_text = "\n---\n".join(context_chunks[:3])  # Limit context

        context_parts.append(
            f"SCHEME: {scheme['name']} ({scheme_id})\n"
            f"VERDICT: {sv['verdict']} (from rules, do not change)\n"
            f"PYTHON REASONS: {sv['python_reasons']}\n"
            f"MISSING FIELDS: {sv['missing_fields']}\n"
            f"CONTEXT:\n{context_text}\n"
        )

    full_context = "\n\n".join(context_parts)

    system_prompt = """You are an eligibility matcher for government schemes.
Given a user profile, scheme context, and Python rule-based verdicts, your task is to provide a SOURCE_QUOTE for each scheme.

Rules:
- NEVER change the verdict (yes/no/maybe). The verdict comes from deterministic rules.
- DO NOT provide reasons - those come from Python rules.
- For each scheme, return a SOURCE_QUOTE copied verbatim from the context that supports the verdict.
- If no relevant quote exists, return empty string.
- Return ONLY valid JSON with this structure:
{
  "results": [
    {"scheme_id": "...", "source_quote": "..."},
    ...
  ]
}"""

    user_prompt = f"""User Profile: {json.dumps(profile, ensure_ascii=False)}

{full_context}

Return JSON with source_quote for each scheme above."""

    try:
        llm_result = call_json(system_prompt, user_prompt, max_tokens=1500, temperature=0.0)
        llm_results = llm_result.get("results", [])

        # Map LLM results back to selected schemes
        llm_map = {r["scheme_id"]: r for r in llm_results}
        for sv in selected:
            scheme_id = sv["scheme"]["id"]
            if scheme_id in llm_map:
                sv["llm_source_quote"] = llm_map[scheme_id].get("source_quote", "")
    except Exception as e:
        # If LLM fails, continue without source quotes
        pass

    return selected