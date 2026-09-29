from __future__ import annotations

"""State definition for the per-person LangGraph workflow."""

from typing import List, TypedDict, Optional, Dict

from app.models import EnrichedPerson, PersonInput


class PersonState(TypedDict, total=False):
    """State carried through the LangGraph for a single person."""

    person: PersonInput
    enriched_person: EnrichedPerson
    errors: List[str]


def initial_state(person: PersonInput) -> PersonState:
    """Create the initial state for a person run."""

    return {"person": person, "errors": []}

