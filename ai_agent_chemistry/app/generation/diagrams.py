from __future__ import annotations

from typing import Callable

from PIL import ImageDraw


def draw_visual(draw: ImageDraw.ImageDraw, visual: str, box: tuple[int, int, int, int]) -> None:
    """Render a topic-specific educational diagram into the given bounding box."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    cx, cy = x0 + w // 2, y0 + h // 2

    painters: dict[str, Callable[..., None]] = {
        "ph_intro": _ph_intro,
        "ph_scale": _ph_scale,
        "ph_ions": _ph_ions,
        "ph_examples": _ph_examples,
        "covalent_shells": _covalent_shells,
        "covalent_sharing": _covalent_sharing,
        "covalent_energy": _covalent_energy,
        "covalent_examples": _covalent_examples,
        "bonding_overview": _bonding_overview,
        "ionic_transfer": _ionic_transfer,
        "covalent_diagram": _covalent_diagram,
        "bonding_examples": _bonding_examples,
    }
    painter = painters.get(visual, _generic_beaker)
    painter(draw, x0, y0, x1, y1, cx, cy, w, h)


def _panel_bg(draw: ImageDraw.ImageDraw, x0: int, y0: int, x1: int, y1: int) -> None:
    draw.rounded_rectangle([x0, y0, x1, y1], radius=16, fill=(12, 24, 48), outline=(80, 140, 220), width=2)


def _label(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, fill: tuple[int, int, int] = (220, 230, 255)) -> None:
    draw.text((x, y), text, fill=fill)


def _atom(
    draw: ImageDraw.ImageDraw,
    cx: int,
    cy: int,
    r: int,
    symbol: str,
    shell_electrons: list[tuple[float, float]] | None = None,
    color: tuple[int, int, int] = (255, 120, 80),
) -> None:
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color, outline=(255, 255, 255), width=2)
    draw.text((cx - 8, cy - 8), symbol, fill=(255, 255, 255))
    if shell_electrons:
        orbit_r = r + 22
        draw.ellipse([cx - orbit_r, cy - orbit_r, cx + orbit_r, cy + orbit_r], outline=(180, 200, 255), width=1)
        for ex, ey in shell_electrons:
            px = cx + int(orbit_r * ex)
            py = cy + int(orbit_r * ey)
            draw.ellipse([px - 5, py - 5, px + 5, py + 5], fill=(100, 200, 255))


def _ph_intro(draw: ImageDraw.ImageDraw, x0: int, y0: int, x1: int, y1: int, cx: int, cy: int, w: int, h: int) -> None:
    _panel_bg(draw, x0 + 10, y0 + 10, x1 - 10, y1 - 10)
    bx, by = cx - 55, cy + 40
    draw.polygon([(bx, by), (bx + 110, by), (bx + 90, by - 130), (bx + 20, by - 130)], fill=(60, 100, 180), outline=(200, 220, 255), width=2)
    draw.rectangle([bx + 15, by - 100, bx + 95, by - 20], fill=(100, 180, 255, 180))
    for i, (lx, ly, sym, col) in enumerate([(cx - 70, cy - 30, "H+", (255, 100, 100)), (cx + 40, cy - 10, "OH-", (100, 180, 255))]):
        draw.ellipse([lx - 18, ly - 18, lx + 18, ly + 18], fill=col, outline=(255, 255, 255))
        _label(draw, lx - 14, ly - 8, sym, fill=(255, 255, 255))
    _label(draw, x0 + 30, y0 + 24, "Solutions contain H+ and OH- ions", fill=(180, 210, 255))


def _ph_scale(draw: ImageDraw.ImageDraw, x0: int, y0: int, x1: int, y1: int, cx: int, cy: int, w: int, h: int) -> None:
    _panel_bg(draw, x0 + 10, y0 + 10, x1 - 10, y1 - 10)
    bar_x, bar_y, bar_w, bar_h = x0 + 40, cy - 20, w - 80, 40
    steps = 15
    colors = _ph_gradient(steps)
    step_w = bar_w // steps
    for i, col in enumerate(colors):
        draw.rectangle([bar_x + i * step_w, bar_y, bar_x + (i + 1) * step_w, bar_y + bar_h], fill=col)
    draw.rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + bar_h], outline=(255, 255, 255), width=2)
    for val, label in [(0, "0"), (7, "7"), (14, "14")]:
        px = bar_x + int(bar_w * val / 14)
        draw.line([(px, bar_y + bar_h + 4), (px, bar_y + bar_h + 14)], fill=(255, 255, 255), width=2)
        _label(draw, px - 6, bar_y + bar_h + 18, label)
    _label(draw, bar_x, bar_y - 36, "ACIDIC", fill=(255, 120, 120))
    _label(draw, cx - 30, bar_y - 36, "NEUTRAL", fill=(200, 255, 200))
    _label(draw, bar_x + bar_w - 70, bar_y - 36, "BASIC", fill=(140, 180, 255))
    _label(draw, x0 + 30, y0 + 24, "pH 0-14 scale", fill=(180, 210, 255))
    examples = [(1, "Stomach acid"), (7, "Pure water"), (13, "Bleach")]
    for val, name in examples:
        px = bar_x + int(bar_w * val / 14)
        draw.ellipse([px - 6, bar_y + bar_h + 40, px + 6, bar_y + bar_h + 52], fill=(255, 255, 255))
        _label(draw, px - 40, bar_y + bar_h + 58, name, fill=(200, 210, 230))


def _ph_ions(draw: ImageDraw.ImageDraw, x0: int, y0: int, x1: int, y1: int, cx: int, cy: int, w: int, h: int) -> None:
    _panel_bg(draw, x0 + 10, y0 + 10, x1 - 10, y1 - 10)
    mid = cx
    draw.line([(mid, y0 + 50), (mid, y1 - 30)], fill=(100, 120, 160), width=2)
    _label(draw, x0 + 40, y0 + 28, "ACID  (pH < 7)", fill=(255, 140, 140))
    _label(draw, mid + 20, y0 + 28, "BASE  (pH > 7)", fill=(140, 180, 255))
    for i in range(6):
        lx = x0 + 60 + (i % 3) * 50
        ly = cy - 30 + (i // 3) * 45
        draw.ellipse([lx - 14, ly - 14, lx + 14, ly + 14], fill=(255, 90, 90))
        _label(draw, lx - 10, ly - 7, "H+", fill=(255, 255, 255))
    for i in range(3):
        lx = mid + 40 + i * 55
        ly = cy - 10 + (i % 2) * 40
        draw.ellipse([lx - 16, ly - 16, lx + 16, ly + 16], fill=(80, 140, 255))
        _label(draw, lx - 16, ly - 7, "OH-", fill=(255, 255, 255))
    _label(draw, x0 + 40, y1 - 50, "More H+  =  more acidic", fill=(255, 180, 180))
    _label(draw, mid + 20, y1 - 50, "More OH-  =  more basic", fill=(180, 200, 255))


def _ph_examples(draw: ImageDraw.ImageDraw, x0: int, y0: int, x1: int, y1: int, cx: int, cy: int, w: int, h: int) -> None:
    _panel_bg(draw, x0 + 10, y0 + 10, x1 - 10, y1 - 10)
    items = [
        (x0 + 80, cy, "Lemon\npH ~2", (255, 220, 60), "ellipse"),
        (cx, cy, "Water\npH 7", (100, 180, 255), "drop"),
        (x1 - 80, cy, "Soap\npH ~10", (180, 140, 255), "rect"),
    ]
    for px, py, label, color, shape in items:
        if shape == "ellipse":
            draw.ellipse([px - 40, py - 35, px + 40, py + 35], fill=color, outline=(255, 255, 255), width=2)
        elif shape == "drop":
            draw.ellipse([px - 30, py - 40, px + 30, py + 20], fill=color, outline=(255, 255, 255), width=2)
            draw.polygon([(px - 20, py - 20), (px + 20, py - 20), (px, py - 55)], fill=color, outline=(255, 255, 255))
        else:
            draw.rounded_rectangle([px - 35, py - 30, px + 35, py + 30], radius=8, fill=color, outline=(255, 255, 255), width=2)
        for i, line in enumerate(label.split("\n")):
            _label(draw, px - 28, py + 45 + i * 18, line, fill=(220, 230, 255))


def _covalent_shells(draw: ImageDraw.ImageDraw, x0: int, y0: int, x1: int, y1: int, cx: int, cy: int, w: int, h: int) -> None:
    _panel_bg(draw, x0 + 10, y0 + 10, x1 - 10, y1 - 10)
    _atom(draw, cx, cy, 28, "C", shell_electrons=[(1, 0), (0.7, 0.7), (-0.7, 0.7), (0, -1)], color=(80, 80, 90))
    _label(draw, x0 + 30, y0 + 24, "Atom wants a full outer shell (octet rule)", fill=(180, 210, 255))
    _label(draw, cx - 90, cy + 70, "Incomplete outer shell", fill=(255, 200, 120))
    draw.polygon([(cx + 50, cy - 60), (cx + 70, cy - 80), (cx + 90, cy - 60)], fill=(255, 200, 80))


def _covalent_sharing(draw: ImageDraw.ImageDraw, x0: int, y0: int, x1: int, y1: int, cx: int, cy: int, w: int, h: int) -> None:
    _panel_bg(draw, x0 + 10, y0 + 10, x1 - 10, y1 - 10)
    _atom(draw, cx - 80, cy, 30, "H", shell_electrons=[(1, 0)], color=(255, 100, 100))
    _atom(draw, cx + 80, cy, 30, "H", shell_electrons=[(-1, 0)], color=(255, 100, 100))
    draw.ellipse([cx - 35, cy - 35, cx + 35, cy + 35], outline=(255, 255, 100), width=2)
    draw.ellipse([cx - 8, cy - 8, cx + 8, cy + 8], fill=(255, 255, 100))
    draw.ellipse([cx - 28, cy - 8, cx - 12, cy + 8], fill=(255, 255, 100))
    draw.ellipse([cx + 12, cy - 8, cx + 28, cy + 8], fill=(255, 255, 100))
    _label(draw, cx - 55, cy + 55, "Shared electron pair", fill=(255, 255, 150))
    _label(draw, x0 + 30, y0 + 24, "Covalent bond = sharing electrons", fill=(180, 210, 255))


def _covalent_energy(draw: ImageDraw.ImageDraw, x0: int, y0: int, x1: int, y1: int, cx: int, cy: int, w: int, h: int) -> None:
    _panel_bg(draw, x0 + 10, y0 + 10, x1 - 10, y1 - 10)
    ax_x, ax_y = x0 + 60, y1 - 50
    ax_end = x1 - 40
    draw.line([(ax_x, ax_y), (ax_end, ax_y)], fill=(200, 200, 200), width=2)
    draw.line([(ax_x, ax_y), (ax_x, y0 + 60)], fill=(200, 200, 200), width=2)
    _label(draw, ax_x - 10, y0 + 45, "Energy", fill=(200, 210, 230))
    _label(draw, ax_end - 50, ax_y + 8, "Bond distance", fill=(200, 210, 230))
    points = []
    for i in range(20):
        t = i / 19
        x = ax_x + int((ax_end - ax_x) * t)
        y = ax_y - int(80 * (1 - 4 * (t - 0.5) ** 2))
        points.append((x, y))
    if len(points) > 1:
        draw.line(points, fill=(100, 220, 180), width=3)
    draw.ellipse([cx - 8, ax_y - 88, cx + 8, ax_y - 72], fill=(255, 200, 80))
    _label(draw, cx - 70, ax_y - 110, "Lower energy = stable bond", fill=(150, 255, 200))


def _covalent_examples(draw: ImageDraw.ImageDraw, x0: int, y0: int, x1: int, y1: int, cx: int, cy: int, w: int, h: int) -> None:
    _panel_bg(draw, x0 + 10, y0 + 10, x1 - 10, y1 - 10)
    _label(draw, x0 + 50, y0 + 30, "H2", fill=(255, 200, 120))
    _atom(draw, x0 + 120, cy - 20, 22, "H", color=(255, 100, 100))
    _atom(draw, x0 + 180, cy - 20, 22, "H", color=(255, 100, 100))
    draw.line([(x0 + 142, cy - 20), (x0 + 158, cy - 20)], fill=(255, 255, 100), width=4)
    _label(draw, x1 - 180, y0 + 30, "H2O", fill=(255, 200, 120))
    ox, oy = x1 - 120, cy + 10
    draw.ellipse([ox - 25, oy - 25, ox + 25, oy + 25], fill=(255, 80, 80))
    _label(draw, ox - 8, oy - 8, "O", fill=(255, 255, 255))
    for hx, hy in [(ox - 45, oy + 30), (ox + 45, oy + 30)]:
        draw.ellipse([hx - 18, hy - 18, hx + 18, hy + 18], fill=(240, 240, 240))
        _label(draw, hx - 6, hy - 7, "H", fill=(60, 60, 60))
        draw.line([(ox, oy + 15), (hx, hy - 10)], fill=(255, 255, 255), width=2)


def _bonding_overview(draw: ImageDraw.ImageDraw, x0: int, y0: int, x1: int, y1: int, cx: int, cy: int, w: int, h: int) -> None:
    _panel_bg(draw, x0 + 10, y0 + 10, x1 - 10, y1 - 10)
    draw.rounded_rectangle([x0 + 30, cy - 60, cx - 20, cy + 60], radius=12, fill=(40, 60, 100), outline=(255, 140, 140), width=2)
    draw.rounded_rectangle([cx + 20, cy - 60, x1 - 30, cy + 60], radius=12, fill=(40, 60, 100), outline=(140, 200, 255), width=2)
    _label(draw, x0 + 55, cy - 40, "IONIC", fill=(255, 160, 160))
    _label(draw, x0 + 45, cy - 10, "Transfer e-", fill=(220, 220, 220))
    _atom(draw, x0 + 90, cy + 30, 20, "Na", color=(255, 180, 80))
    draw.line([(x0 + 130, cy + 30), (x0 + 170, cy + 30)], fill=(255, 255, 100), width=2)
    draw.polygon([(x0 + 170, cy + 30), (x0 + 160, cy + 24), (x0 + 160, cy + 36)], fill=(255, 255, 100))
    _atom(draw, x0 + 200, cy + 30, 20, "Cl", color=(80, 200, 120))
    _label(draw, cx + 45, cy - 40, "COVALENT", fill=(160, 200, 255))
    _label(draw, cx + 40, cy - 10, "Share e-", fill=(220, 220, 220))
    _atom(draw, cx + 80, cy + 30, 20, "H", color=(255, 100, 100))
    _atom(draw, cx + 150, cy + 30, 20, "H", color=(255, 100, 100))
    draw.line([(cx + 102, cy + 30), (cx + 128, cy + 30)], fill=(255, 255, 100), width=3)


def _ionic_transfer(draw: ImageDraw.ImageDraw, x0: int, y0: int, x1: int, y1: int, cx: int, cy: int, w: int, h: int) -> None:
    _panel_bg(draw, x0 + 10, y0 + 10, x1 - 10, y1 - 10)
    _label(draw, x0 + 30, y0 + 24, "Sodium gives electron to Chlorine", fill=(180, 210, 255))
    _atom(draw, cx - 100, cy, 32, "Na", color=(255, 180, 80))
    _atom(draw, cx + 100, cy, 32, "Cl", color=(80, 200, 120))
    draw.ellipse([cx - 30, cy - 40, cx - 10, cy - 20], fill=(255, 255, 100))
    draw.line([(cx - 20, cy - 30), (cx + 60, cy - 10)], fill=(255, 255, 100), width=2)
    draw.polygon([(cx + 60, cy - 10), (cx + 52, cy - 16), (cx + 52, cy - 4)], fill=(255, 255, 100))
    _label(draw, cx - 40, cy + 55, "Na+", fill=(255, 200, 120))
    _label(draw, cx + 80, cy + 55, "Cl-", fill=(140, 230, 180))
    for i in range(3):
        ix = cx - 60 + i * 25
        draw.rectangle([ix, cy + 80, ix + 15, cy + 95], fill=(200, 200, 220))
    _label(draw, cx - 50, cy + 100, "NaCl crystal lattice", fill=(200, 210, 230))


def _covalent_diagram(draw: ImageDraw.ImageDraw, x0: int, y0: int, x1: int, y1: int, cx: int, cy: int, w: int, h: int) -> None:
    _panel_bg(draw, x0 + 10, y0 + 10, x1 - 10, y1 - 10)
    _label(draw, x0 + 30, y0 + 24, "Electrons shared between atoms", fill=(180, 210, 255))
    ox, oy = cx, cy + 10
    draw.ellipse([ox - 30, oy - 30, ox + 30, oy + 30], fill=(255, 80, 80))
    _label(draw, ox - 8, oy - 8, "O", fill=(255, 255, 255))
    for angle, hx, hy in [(0, ox + 55, oy), (-1, ox - 28, oy + 48), (1, ox + 28, oy + 48)]:
        draw.ellipse([hx - 20, hy - 20, hx + 20, hy + 20], fill=(240, 240, 240))
        _label(draw, hx - 6, hy - 7, "H", fill=(40, 40, 40))
        draw.line([(ox, oy + 20), (hx, hy - 12)], fill=(255, 255, 255), width=2)
    draw.ellipse([ox - 5, oy - 50, ox + 5, oy - 40], fill=(255, 255, 100))
    draw.ellipse([ox + 20, oy + 35, ox + 30, oy + 45], fill=(255, 255, 100))
    _label(draw, cx - 80, cy - 60, "Shared pairs", fill=(255, 255, 150))


def _bonding_examples(draw: ImageDraw.ImageDraw, x0: int, y0: int, x1: int, y1: int, cx: int, cy: int, w: int, h: int) -> None:
    _panel_bg(draw, x0 + 10, y0 + 10, x1 - 10, y1 - 10)
    _label(draw, x0 + 50, y0 + 30, "Salt (ionic)", fill=(255, 180, 140))
    for row in range(3):
        for col in range(4):
            px = x0 + 50 + col * 28
            py = cy - 30 + row * 28
            color = (255, 200, 120) if (row + col) % 2 == 0 else (100, 200, 140)
            draw.rectangle([px, py, px + 22, py + 22], fill=color, outline=(255, 255, 255))
    _label(draw, x1 - 200, y0 + 30, "Water (covalent)", fill=(140, 180, 255))
    ox = x1 - 120
    oy = cy + 10
    draw.ellipse([ox - 28, oy - 28, ox + 28, oy + 28], fill=(80, 160, 255))
    _label(draw, ox - 8, oy - 8, "O", fill=(255, 255, 255))
    for hx, hy in [(ox - 50, oy + 35), (ox + 50, oy + 35)]:
        draw.ellipse([hx - 16, hy - 16, hx + 16, hy + 16], fill=(240, 240, 240))
        _label(draw, hx - 6, hy - 7, "H", fill=(40, 40, 40))
        draw.line([(ox, oy + 18), (hx, hy - 10)], fill=(255, 255, 255), width=2)


def _generic_beaker(draw: ImageDraw.ImageDraw, x0: int, y0: int, x1: int, y1: int, cx: int, cy: int, w: int, h: int) -> None:
    _panel_bg(draw, x0 + 10, y0 + 10, x1 - 10, y1 - 10)
    bx, by = cx - 50, cy + 30
    draw.polygon([(bx, by), (bx + 100, by), (bx + 85, by - 100), (bx + 15, by - 100)], fill=(60, 100, 180), outline=(200, 220, 255), width=2)
    draw.rectangle([bx + 20, by - 80, bx + 80, by - 30], fill=(100, 180, 255))


def _ph_gradient(steps: int) -> list[tuple[int, int, int]]:
    anchors = [(255, 60, 60), (255, 180, 60), (100, 220, 100), (80, 160, 255), (140, 80, 200)]
    colors: list[tuple[int, int, int]] = []
    for i in range(steps):
        t = i / max(steps - 1, 1) * (len(anchors) - 1)
        idx = int(t)
        frac = t - idx
        if idx >= len(anchors) - 1:
            colors.append(anchors[-1])
        else:
            a, b = anchors[idx], anchors[idx + 1]
            colors.append(tuple(int(a[j] + (b[j] - a[j]) * frac) for j in range(3)))
    return colors
