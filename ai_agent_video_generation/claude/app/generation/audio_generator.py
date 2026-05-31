from gtts import gTTS
from pathlib import Path

def generate_narration(text: str, output_path: Path) -> Path:
    tts = gTTS(text=text, lang="en", slow=False)
    tts.save(str(output_path))
    return output_path