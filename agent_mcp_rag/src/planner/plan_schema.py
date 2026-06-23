from __future__ import annotations
from pydantic import BaseModel, Field


class SceneSpec(BaseModel):
    title: str
    caption: str
    location: str
    image_search_query: str
    day_number: int | None = None


class DayAgenda(BaseModel):
    day: int
    title: str
    morning: str
    afternoon: str
    evening: str
    meals: list[str] = Field(default_factory=list)
    estimated_cost_usd: float | None = None


class TripPlan(BaseModel):
    plan_id: str
    client_id: str
    destination: str
    season: str
    budget_summary: str
    highlights: list[str] = Field(default_factory=list)
    agenda: list[DayAgenda] = Field(default_factory=list)
    food_recommendations: list[str] = Field(default_factory=list)
    packing_tips: list[str] = Field(default_factory=list)
    scenes: list[SceneSpec] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)


def trip_plan_to_markdown(plan: TripPlan) -> str:
    lines = [
        f"# Holiday Plan: {plan.destination}",
        "",
        f"**Client:** {plan.client_id}  ",
        f"**Season:** {plan.season}  ",
        f"**Budget:** {plan.budget_summary}",
        "",
        "## Highlights",
    ]
    for item in plan.highlights:
        lines.append(f"- {item}")

    lines.extend(["", "## Day-by-Day Agenda"])
    for day in plan.agenda:
        lines.extend(
            [
                "",
                f"### Day {day.day}: {day.title}",
                f"- **Morning:** {day.morning}",
                f"- **Afternoon:** {day.afternoon}",
                f"- **Evening:** {day.evening}",
            ]
        )
        if day.meals:
            lines.append(f"- **Meals:** {', '.join(day.meals)}")
        if day.estimated_cost_usd is not None:
            lines.append(f"- **Est. daily cost:** ${day.estimated_cost_usd:.0f}")

    if plan.food_recommendations:
        lines.extend(["", "## Food Recommendations"])
        for food in plan.food_recommendations:
            lines.append(f"- {food}")

    if plan.packing_tips:
        lines.extend(["", "## Packing Tips"])
        for tip in plan.packing_tips:
            lines.append(f"- {tip}")

    if plan.scenes:
        lines.extend(["", "## Destination Scenes"])
        for scene in plan.scenes:
            day = f" (Day {scene.day_number})" if scene.day_number else ""
            lines.append(f"- **{scene.title}**{day} — {scene.location}: {scene.caption}")

    if plan.sources:
        lines.extend(["", "## Sources"])
        for src in plan.sources:
            lines.append(f"- {src}")

    return "\n".join(lines) + "\n"
