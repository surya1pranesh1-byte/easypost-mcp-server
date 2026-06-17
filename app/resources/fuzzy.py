from __future__ import annotations

import re
from typing import Any


def normalize_candidate(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").strip().lower())


def levenshtein(a: str, b: str) -> int:
    left = normalize_candidate(a)
    right = normalize_candidate(b)
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)

    previous = list(range(len(right) + 1))
    current = [0] * (len(right) + 1)

    for i in range(1, len(left) + 1):
        current[0] = i
        for j in range(1, len(right) + 1):
            cost = 0 if left[i - 1] == right[j - 1] else 1
            current[j] = min(current[j - 1] + 1, previous[j] + 1, previous[j - 1] + cost)
        previous = current[:]

    return previous[len(right)]


def similarity(a: str, b: str) -> float:
    left = normalize_candidate(a)
    right = normalize_candidate(b)
    max_len = max(len(left), len(right))
    if not max_len:
        return 1.0
    return 1.0 - levenshtein(left, right) / max_len


def fuzzy_suggest(
    input_str: str,
    candidates: list[dict[str, Any]],
    *,
    threshold: float = 0.72,
    limit: int = 5,
) -> list[dict[str, Any]]:
    normalized_input = normalize_candidate(input_str)
    if not normalized_input:
        return []

    scored = []
    for candidate in candidates:
        labels = [candidate.get("code"), candidate.get("name"), *(candidate.get("aliases") or [])]
        labels = [lb for lb in labels if lb]
        score = max((similarity(normalized_input, label) for label in labels), default=0.0)
        if score >= threshold:
            scored.append({**candidate, "score": round(score, 3)})

    scored.sort(key=lambda c: (-c["score"], str(c.get("code", ""))))
    return scored[:limit]
