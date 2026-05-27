from __future__ import annotations

from app.domain.exceptions import ValidationError

REQUIRED_QUERIES = {
    "How does the pH scale work?": ["pH", "acid", "base"],
    "Why do atoms form covalent bonds?": ["covalent", "electrons", "share"],
    "What is the difference between ionic and covalent bonding?": [
        "ionic",
        "covalent",
        "electrons",
    ],
}


def validate_query(query: str) -> None:
    if query not in REQUIRED_QUERIES:
        raise ValidationError("Only the three required chemistry queries are supported.")


def validate_script(query: str, script: dict) -> None:
    scenes = script.get("scenes", [])
    if not scenes:
        raise ValidationError("Script has no scenes.")
    narration_blob = " ".join(scene.get("narration", "") for scene in scenes).lower()
    required_terms = REQUIRED_QUERIES[query]
    for term in required_terms:
        if term.lower() not in narration_blob:
            raise ValidationError(f"Script relevance check failed: missing term '{term}'.")
