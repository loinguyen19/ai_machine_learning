import anthropic
import json
from tenacity import retry, stop_after_attempt, wait_exponential
from ollama import chat


ALLOWED_CONCEPTS = {
    "how does the ph scale work",
    "why do atoms form covalent bonds",
    "what is the difference between ionic and covalent bonding",
}

def validate_concept(concept: str) -> bool:
    return concept.strip().lower() in ALLOWED_CONCEPTS

prompt = """You are an educational video script writer for high school chemistry.

Generate a structured video script for the concept: "{concept}"

Return ONLY valid JSON in this exact format, no other text:
{{
  "title": "Short title for the video",
  "slides": [
    {{
      "slide_number": 1,
      "title": "Slide title",
      "narration": "What the narrator says (2-4 sentences, clear and engaging)",
      "visual_elements": ["bullet point or diagram description"],
      "duration_seconds": 8
    }}
  ],
  "total_slides": 5
}}

Requirements:
- Exactly 5 slides
- Slide 1: Hook/introduction
- Slides 2-4: Core explanation with progressively deeper detail
- Slide 5: Summary and real-world application
- Each narration 2-4 sentences
- Visual elements: 2-4 bullet points or a simple diagram description per slide
- Keep language accessible for a 16-year-old learner
"""

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def generate_script_with_ollama(concept: str) -> dict:
    user_prompt = prompt.format(concept=concept)

    response = chat(
        model="gemma3",
        messages=[{"role": "user", "content": user_prompt}],
        format="json",
        options={"num_predict": 1500},
    )

    raw = (response.message.content or "").strip()
    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    script = json.loads(raw)

    # Validate structure
    assert "slides" in script and len(script["slides"]) == 5
    for slide in script["slides"]:
        assert "narration" in slide and "visual_elements" in slide

    return script

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def generate_script(concept: str) -> dict:
    client = anthropic.Anthropic()
    user_prompt = prompt.format(concept=concept)

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw = response.content[0].text.strip()
    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    script = json.loads(raw)

    # Validate structure
    assert "slides" in script and len(script["slides"]) == 5
    for slide in script["slides"]:
        assert "narration" in slide and "visual_elements" in slide

    return script
