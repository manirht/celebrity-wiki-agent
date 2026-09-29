from __future__ import annotations

"""CLI entrypoint for the Celebrity Wiki Agent.

This script:
- Loads configuration and the input CSV of people
- Builds the LangGraph workflow using Groq Qwen as the LLM
- Runs the enrichment for each person
- Relies on the local STDIO FS tool and remote MCP FastAPI server for I/O
"""

import csv
from pathlib import Path
from typing import List

from .config import DATA_DIR, load_config
from .models import PersonInput
from .graph.state import initial_state
from .graph.graph_builder import create_llm, build_graph
from .logging_config import setup_logging, get_logger


def read_people_from_csv(path: Path) -> List[PersonInput]:
    """Read the input CSV of people.

    The CSV is expected to have headers: name,domain
    """

    people: List[PersonInput] = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (row.get("name") or "").strip()
            domain = (row.get("domain") or "").strip()
            if not name:
                continue
            people.append(PersonInput(name=name, domain=domain))
    return people


def main() -> None:
    """Run the full enrichment pipeline for all people in the CSV."""

    # Initialize logging
    setup_logging()
    logger = get_logger("main")

    cfg = load_config()
    csv_path = DATA_DIR / "celebrities.csv"
    people = read_people_from_csv(csv_path)

    logger.info(f"Loaded configuration for model: {cfg.groq.model_name}")
    logger.info(f"Found {len(people)} people in CSV")
    
    print("Loaded configuration for model:", cfg.groq.model_name)
    print("Found", len(people), "people in CSV.")
    if not people:
        logger.warning("No people found in CSV, exiting")
        return

    llm = create_llm(cfg)
    graph = build_graph(llm)

    for i, p in enumerate(people, 1):
        logger.info(f"[{i}/{len(people)}] Processing {p.name} ({p.domain})")
        print(f"Processing {p.name} ({p.domain}) ...")
        try:
            graph.invoke(initial_state(p))
            logger.info(f"[{i}/{len(people)}] Completed {p.name}")
            print("  -> done")
        except Exception as exc:  # pragma: no cover - runtime error path
            logger.error(f"[{i}/{len(people)}] Error processing {p.name}: {exc}", exc_info=True)
            print(f"  -> ERROR: {exc}")
            import traceback
            traceback.print_exc()

    logger.info("Pipeline completed")


if __name__ == "__main__":  # pragma: no cover
    main()

