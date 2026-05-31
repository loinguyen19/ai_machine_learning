import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path

BRAND_BG = "#0F1B2D"
BRAND_ACCENT = "#4FC3F7"
TEXT_COLOR = "#FFFFFF"
SUBTITLE_COLOR = "#B0BEC5"

def render_slide(slide: dict, output_path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(12.8, 7.2), dpi=100)
    fig.patch.set_facecolor(BRAND_BG)
    ax.set_facecolor(BRAND_BG)
    ax.axis("off")
    
    # Accent bar at top
    ax.add_patch(patches.Rectangle((0, 0.92), 1, 0.08,
                                    transform=ax.transAxes,
                                    color=BRAND_ACCENT, zorder=2))
    
    # Slide number
    ax.text(0.97, 0.955, f"{slide['slide_number']}/5",
            transform=ax.transAxes, color=BRAND_BG,
            fontsize=11, ha="right", va="center", fontweight="bold")
    
    # Title
    ax.text(0.5, 0.82, slide["title"],
            transform=ax.transAxes, color=BRAND_ACCENT,
            fontsize=22, ha="center", va="top", fontweight="bold")
    
    # Visual elements (bullet points)
    y_pos = 0.68
    for element in slide["visual_elements"]:
        ax.text(0.1, y_pos, f"• {element}",
                transform=ax.transAxes, color=TEXT_COLOR,
                fontsize=14, ha="left", va="top", wrap=True,
                multialignment="left")
        y_pos -= 0.13
    
    plt.tight_layout(pad=0)
    fig.savefig(output_path, bbox_inches="tight", facecolor=BRAND_BG)
    plt.close(fig)
    return output_path