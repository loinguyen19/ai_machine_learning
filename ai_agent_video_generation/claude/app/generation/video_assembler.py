from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
from pathlib import Path
from typing import List

def assemble_video(slide_paths: List[Path], audio_paths: List[Path], output_path: Path) -> Path:
    clips = []
    for img_path, aud_path in zip(slide_paths, audio_paths):
        audio = AudioFileClip(str(aud_path))
        duration = audio.duration + 0.5  # small pause after each slide
        clip = ImageClip(str(img_path)).set_duration(duration).set_audio(audio)
        clips.append(clip)
    
    final = concatenate_videoclips(clips, method="compose")
    final.write_videofile(str(output_path), fps=24, codec="libx264",
                          audio_codec="aac", logger=None)
    return output_path