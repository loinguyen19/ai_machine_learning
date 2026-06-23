from __future__ import annotations
from pathlib import Path
from fpdf import FPDF
from planner.plan_schema import TripPlan, trip_plan_to_markdown


def _safe_text(text: str) -> str:
    """FPDF core fonts are Latin-1; replace unsupported chars."""
    return text.encode("latin-1", errors="replace").decode("latin-1")


class PlanPDF(FPDF):
    def footer(self) -> None:
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 10, _safe_text(f"Page {self.page_no()}"), align="C")


def build_plan_pdf(plan: TripPlan, scene_dir: Path, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    pdf = PlanPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    width = pdf.epw

    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(width, 12, _safe_text(f"Holiday Plan: {plan.destination}"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(width, 8, _safe_text(f"Client: {plan.client_id}  |  Season: {plan.season}"), new_x="LMARGIN", new_y="NEXT")
    pdf.multi_cell(width, 6, _safe_text(f"Budget: {plan.budget_summary}"))
    pdf.ln(4)

    if plan.highlights:
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(width, 8, "Highlights", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        for item in plan.highlights:
            pdf.multi_cell(width, 5, _safe_text(f"- {item}"))
        pdf.ln(2)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(width, 8, "Day-by-Day Agenda", new_x="LMARGIN", new_y="NEXT")
    for day in plan.agenda:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(width, 7, _safe_text(f"Day {day.day}: {day.title}"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(width, 5, _safe_text(f"Morning: {day.morning}"))
        pdf.multi_cell(width, 5, _safe_text(f"Afternoon: {day.afternoon}"))
        pdf.multi_cell(width, 5, _safe_text(f"Evening: {day.evening}"))
        if day.meals:
            pdf.multi_cell(width, 5, _safe_text(f"Meals: {', '.join(day.meals)}"))
        pdf.ln(2)

    if plan.food_recommendations:
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(width, 8, "Food Recommendations", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        for food in plan.food_recommendations:
            pdf.multi_cell(width, 5, _safe_text(f"- {food}"))
        pdf.ln(2)

    if plan.packing_tips:
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(width, 8, "Packing Tips", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        for tip in plan.packing_tips:
            pdf.multi_cell(width, 5, _safe_text(f"- {tip}"))
        pdf.ln(2)

    scene_images = sorted(scene_dir.glob("scene_*.png"))
    if scene_images:
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(width, 10, "Destination Scenes", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

        for idx, image_path in enumerate(scene_images):
            scene_meta = plan.scenes[idx] if idx < len(plan.scenes) else None
            if scene_meta:
                pdf.set_font("Helvetica", "B", 11)
                pdf.multi_cell(width, 6, _safe_text(scene_meta.title))
                pdf.set_font("Helvetica", "", 9)
                pdf.multi_cell(width, 5, _safe_text(f"{scene_meta.location} — {scene_meta.caption}"))
                pdf.ln(1)

            img_width = width
            img_height = img_width * 9 / 16
            if pdf.get_y() + img_height > pdf.h - 20:
                pdf.add_page()
            pdf.image(str(image_path), w=img_width)
            pdf.ln(4)

    pdf.output(str(output_path))
    return output_path
