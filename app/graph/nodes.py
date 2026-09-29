from __future__ import annotations

"""LangGraph nodes for per-person enrichment and file writing."""

import json
import re
from typing import Dict, List

from langchain_core.language_models.chat_models import BaseChatModel

from app.graph.state import PersonState
from app.logging_config import get_logger

logger = get_logger("graph")
from app.models import Citation, EnrichedPerson, PersonInput, SectionText
from app.tools.remote_search_client import fetch_page, web_search
from app.tools.weather_tool import get_current_weather
from app.tools.local_fs_client import fs_mkdir, fs_write_file


def _slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return s or "person"


def _collect_sources(person: PersonInput) -> List[Dict]:
    q = f"{person.name} biography {person.domain}"
    logger.info(f"Searching web for: {q}")
    results = web_search.invoke({"query": q, "num_results": 5})
    logger.debug(f"Got {len(results)} search results")
    pages: List[Dict] = []
    for item in results[:3]:
        url = item.get("url")
        if not url:
            continue
        logger.debug(f"Fetching page: {url}")
        page = fetch_page.invoke({"url": url})
        # Skip pages that have errors (e.g., 403 Forbidden)
        if page.get("error"):
            logger.warning(f"Page fetch error for {url}: {page.get('error')}")
            continue
        pages.append(page)
    logger.info(f"Collected {len(pages)} source pages")
    return pages


def _resp_text(resp) -> str:
    content = getattr(resp, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list) and content and isinstance(content[0], dict):
        return content[0].get("text", "")
    return str(content)


def _extract_json_from_response(response_text: str) -> str:
    """Extract JSON from LLM response, handling thinking tags and code blocks."""
    
    # Strip Qwen3-style <think>...</think> tags first
    if "<think>" in response_text:
        # Find end of thinking block and take content after it
        think_end = response_text.find("</think>")
        if think_end != -1:
            response_text = response_text[think_end + 8:].strip()
    
    # Try to extract JSON from markdown code blocks if present
    if "```json" in response_text:
        start = response_text.find("```json") + 7
        end = response_text.find("```", start)
        if end != -1:
            response_text = response_text[start:end].strip()
    elif "```" in response_text:
        start = response_text.find("```") + 3
        newline_pos = response_text.find("\n", start)
        if newline_pos != -1 and newline_pos < start + 20:
            start = newline_pos + 1
        end = response_text.find("```", start)
        if end != -1:
            response_text = response_text[start:end].strip()
    
    # Try to find JSON object directly (starts with { and ends with })
    if not response_text.startswith("{"):
        start = response_text.find("{")
        end = response_text.rfind("}")
        if start != -1 and end != -1 and end > start:
            response_text = response_text[start:end+1]
    
    return response_text.strip()


def _llm_extract_facts(llm: BaseChatModel, person: PersonInput, pages: List[Dict]) -> Dict:
    parts = []
    for i, p in enumerate(pages, 1):
        parts.append(
            f"Source {i}: {p.get('url')}\nTitle: {p.get('title','')}\nExcerpt: {p.get('content','')[:1500]}"
        )
    joined = "\n\n".join(parts)
    system = "You are a JSON extraction assistant. Output ONLY valid JSON with no explanation, no thinking, and no markdown formatting. Do not wrap in code blocks."
    user = (
        f"Name: {person.name}\nDomain: {person.domain}\n\nSources:\n{joined}\n\n"
        "IMPORTANT: Extract the person's birth city and birth country. This is critical for weather lookup.\n"
        "Look for phrases like 'born in', 'birthplace', 'native of', 'hails from', etc.\n\n"
        "Return ONLY a JSON object with these exact keys:\n"
        "- birth_city: string - the city where the person was born (e.g., 'Mumbai', 'New York', 'Hyderabad')\n"
        "- birth_country: string - the country where the person was born (e.g., 'India', 'United States')\n"
        "- birthplace_sources: array of URL strings that mention the birthplace\n"
        "- intro_facts: array of objects with 'text' and 'sources' keys\n"
        "- achievement_facts: array of objects with 'text' and 'sources' keys\n\n"
        "Use only URLs from the provided sources. Use empty strings ONLY if birth info is truly not found.\n"
        "Output ONLY the JSON object, nothing else."
    )
    logger.info(f"LLM call: Extracting facts for {person.name}")
    msg = llm.invoke(
        [{"role": "system", "content": system}, {"role": "user", "content": user}]
    )
    response_text = _resp_text(msg)
    logger.debug(f"LLM raw response length: {len(response_text)} chars")
    response_text = _extract_json_from_response(response_text)

    try:
        facts = json.loads(response_text)
        logger.info(f"Extracted facts - birth_city: {facts.get('birth_city', '')}, birth_country: {facts.get('birth_country', '')}")
        return facts
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        logger.debug(f"Response was: {response_text[:500]}")
        # Return a default empty structure instead of crashing
        return {
            "birth_city": "",
            "birth_country": "",
            "birthplace_sources": [],
            "intro_facts": [],
            "achievement_facts": []
        }


def _llm_synth_sections(
    llm: BaseChatModel,
    person: PersonInput,
    facts: Dict,
    weather: Dict,
    sightseeing: List[Dict],
) -> Dict:
    system = "You are a JSON content assistant. Output ONLY valid JSON with no explanation, no thinking, and no markdown formatting. Do not wrap in code blocks."
    user = (
        f"Person: {person.name} ({person.domain})\n\n"
        f"Facts JSON:\n{json.dumps(facts, ensure_ascii=False)}\n\n"
        f"Weather JSON:\n{json.dumps(weather, ensure_ascii=False)}\n\n"
        f"Sightseeing JSON:\n{json.dumps(sightseeing, ensure_ascii=False)}\n\n"
        "Write content sections and return ONLY a JSON object with these exact keys: "
        "introduction (object with 'text' and 'sources' keys), "
        "birthplace (object with 'text' and 'sources' keys), "
        "achievements (array of objects with 'text' and 'sources' keys), "
        "weather_summary (object with 'text' and 'sources' keys), "
        "sightseeing (array of objects with 'text' and 'sources' keys). "
        "Each 'sources' should be an array of URLs. Include the weather API URL in weather_summary.sources. "
        "Output ONLY the JSON object, nothing else."
    )
    msg = llm.invoke(
        [{"role": "system", "content": system}, {"role": "user", "content": user}]
    )
    response_text = _extract_json_from_response(_resp_text(msg))
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        return {
            "introduction": {"text": "", "sources": []},
            "birthplace": {"text": "", "sources": []},
            "achievements": [],
            "weather_summary": {"text": "", "sources": []},
            "sightseeing": []
        }


def _build_citations(sections: Dict) -> Dict[str, Citation]:
    by_url: Dict[str, Citation] = {}

    def add(entries):
        for entry in entries or []:
            for url in entry.get("sources", []) or []:
                if url and url not in by_url:
                    cid = f"src{len(by_url)+1}"
                    by_url[url] = Citation(id=cid, url=url)

    for key in ["introduction", "birthplace", "weather_summary"]:
        sec = sections.get(key) or {}
        add([sec])
    add(sections.get("achievements"))
    add(sections.get("sightseeing"))
    return {c.id: c for c in by_url.values()}


def _sec_from_dict(d: Dict, citations: Dict[str, Citation]) -> SectionText:
    ids: List[str] = []
    for url in d.get("sources", []) or []:
        for c in citations.values():
            if c.url == url:
                ids.append(c.id)
                break
    return SectionText(text=d.get("text", ""), citation_ids=ids)


def enrich_person_node(llm: BaseChatModel, state: PersonState) -> PersonState:
    person = state["person"]
    logger.info(f"=== Enriching: {person.name} ({person.domain}) ===")
    
    pages = _collect_sources(person)
    facts = _llm_extract_facts(llm, person, pages)
    city = facts.get("birth_city") or ""
    country = facts.get("birth_country") or ""
    
    logger.info(f"Fetching weather for: {city}, {country}")
    weather = get_current_weather.invoke({"city": city, "country": country})
    if weather.get("error"):
        logger.warning(f"Weather fetch failed: {weather.get('error')}")
    else:
        logger.info(f"Weather: {weather.get('temperature_c')}°C")
    src_url = weather.get("source_url")
    if src_url:
        weather["sources"] = [src_url]
    query = f"{city} top tourist attractions" if city else f"{person.name} birthplace sightseeing"
    s_results = web_search.invoke({"query": query, "num_results": 5})
    sightseeing_items = [
        {
            "name": r.get("title"),
            "url": r.get("url"),
            "snippet": r.get("snippet"),
            "sources": [r.get("url")] if r.get("url") else [],
        }
        for r in s_results
        if r.get("url")
    ]
    sections = _llm_synth_sections(llm, person, facts, weather, sightseeing_items)
    citations = _build_citations(sections)
    intro = _sec_from_dict(sections.get("introduction", {}), citations)
    birthplace = _sec_from_dict(sections.get("birthplace", {}), citations)
    weather_sec = _sec_from_dict(sections.get("weather_summary", {}), citations)
    achievements = [
        _sec_from_dict(x, citations) for x in sections.get("achievements", []) or []
    ]
    sightseeing_secs = [
        _sec_from_dict(x, citations) for x in sections.get("sightseeing", []) or []
    ]
    enriched = EnrichedPerson(
        name=person.name,
        domain=person.domain,
        birthplace=birthplace,
        introduction=intro,
        achievements=achievements,
        weather_summary=weather_sec,
        sightseeing=sightseeing_secs,
        citations=citations,
    )
    state["enriched_person"] = enriched
    return state


def write_outputs_node(state: PersonState) -> PersonState:
    person = state["person"]
    enriched = state["enriched_person"]
    slug = _slugify(person.name)
    
    logger.info(f"Writing outputs for: {person.name}")
    
    json_text = json.dumps(
        enriched.to_serialisable_dict(), ensure_ascii=False, indent=2
    )
    from app.formatting.markdown import render_person_markdown

    md_text = render_person_markdown(enriched)
    fs_mkdir.invoke({"path": "outputs/structured"})
    fs_mkdir.invoke({"path": "outputs/reports"})
    
    json_path = f"outputs/structured/{slug}.json"
    md_path = f"outputs/reports/{slug}.md"
    
    fs_write_file.invoke({"path": json_path, "content": json_text})
    logger.debug(f"Wrote JSON: {json_path}")
    
    fs_write_file.invoke({"path": md_path, "content": md_text})
    logger.debug(f"Wrote Markdown: {md_path}")
    
    logger.info(f"Outputs written: {json_path}, {md_path}")
    return state
