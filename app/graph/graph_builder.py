from __future__ import annotations

"""Helpers to construct the LangGraph workflow and LLM instance."""

from typing import Callable

from langchain_groq import ChatGroq
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import StateGraph, END

from app.config import AppConfig
from app.graph.state import PersonState
from app.graph.nodes import enrich_person_node, write_outputs_node


def create_llm(cfg: AppConfig) -> BaseChatModel:
    """Create a Groq-backed Qwen chat model from configuration."""

    return ChatGroq(
        groq_api_key=cfg.groq.api_key,
        model_name=cfg.groq.model_name,
        temperature=0.3,
    )


def build_graph(llm: BaseChatModel):
    """Build and compile the per-person LangGraph workflow.

    The graph has two nodes:
    - "enrich": call tools + LLM to build an EnrichedPerson
    - "write": write per-person JSON + Markdown via STDIO FS tools
    """

    graph = StateGraph(PersonState)

    def enrich(state: PersonState) -> PersonState:
        return enrich_person_node(llm, state)

    graph.add_node("enrich", enrich)
    graph.add_node("write", write_outputs_node)
    graph.set_entry_point("enrich")
    graph.add_edge("enrich", "write")
    graph.add_edge("write", END)
    return graph.compile()

