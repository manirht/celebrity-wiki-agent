from __future__ import annotations

"""Markdown formatting utilities for per-person reports."""

from typing import List

from app.models import EnrichedPerson, SectionText, Citation


def _format_citations(section: SectionText, all_citations: dict[str, Citation]) -> str:
    if not section.citation_ids:
        return ""
    parts: List[str] = []
    for cid in section.citation_ids:
        c = all_citations.get(cid)
        if not c:
            continue
        label = c.description or c.url
        parts.append(f"[{cid}]({c.url})")
    if not parts:
        return ""
    return "Sources: " + " ".join(parts)


def render_person_markdown(person: EnrichedPerson) -> str:
    """Render a single person's enriched data as Markdown text."""

    lines: List[str] = []
    lines.append(f"# {person.name}")
    lines.append("")

    # Introduction
    lines.append("## Introduction")
    lines.append(person.introduction.text)
    intro_src = _format_citations(person.introduction, person.citations)
    if intro_src:
        lines.append("")
        lines.append(intro_src)
    lines.append("")

    # Achievements
    lines.append("## Key Achievements")
    for idx, ach in enumerate(person.achievements, start=1):
        lines.append(f"- {ach.text}")
        ach_src = _format_citations(ach, person.citations)
        if ach_src:
            lines.append(f"  - {ach_src}")
    lines.append("")

    # Birthplace
    lines.append("## Birthplace")
    lines.append(person.birthplace.text)
    birth_src = _format_citations(person.birthplace, person.citations)
    if birth_src:
        lines.append("")
        lines.append(birth_src)
    lines.append("")

    # Weather
    lines.append("## Weather in Birth City")
    lines.append(person.weather_summary.text)
    weather_src = _format_citations(person.weather_summary, person.citations)
    if weather_src:
        lines.append("")
        lines.append(weather_src)
    lines.append("")

    # Sightseeing
    lines.append("## Sightseeing Recommendations")
    for sight in person.sightseeing:
        lines.append(f"- {sight.text}")
        sight_src = _format_citations(sight, person.citations)
        if sight_src:
            lines.append(f"  - {sight_src}")

    lines.append("")
    return "\n".join(lines)

