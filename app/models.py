from __future__ import annotations

"""Core data models for the Celebrity Wiki Agent.

These models are intentionally lightweight and framework-agnostic so they can
be used both inside LangGraph state and for structured JSON outputs.
"""

from dataclasses import dataclass, asdict
from typing import List, Dict, Optional


@dataclass
class PersonInput:
    """Represents a row from the input CSV."""

    name: str
    domain: str


@dataclass
class Citation:
    """A single citation/source for factual claims.

    The `id` is local to a single person and used to reference URLs from
    LLM-generated sections.
    """

    id: str
    url: str
    description: Optional[str] = None


@dataclass
class SectionText:
    """Text plus references to citation IDs.

    `citation_ids` should correspond to keys in a dict[str, Citation].
    """

    text: str
    citation_ids: List[str]


@dataclass
class EnrichedPerson:
    """Final enriched representation for a single person."""

    name: str
    domain: str
    birthplace: SectionText
    introduction: SectionText
    achievements: List[SectionText]
    weather_summary: SectionText
    sightseeing: List[SectionText]
    citations: Dict[str, Citation]

    def to_serialisable_dict(self) -> Dict:
        """Return a JSON-serialisable representation of the person."""

        def citation_to_dict(c: Citation) -> Dict:
            return {"id": c.id, "url": c.url, "description": c.description}

        data = asdict(self)
        data["citations"] = {
            key: citation_to_dict(value) for key, value in self.citations.items()
        }
        return data

