from __future__ import annotations

"""Central configuration for the Celebrity Wiki Agent.

This module centralises configuration like API keys, model names, and default
paths. It avoids hard-coding secrets in code; instead, we read from
environment variables where needed.
"""

from dataclasses import dataclass, field
import os
from pathlib import Path

# Load environment variables from a .env file if python-dotenv is installed.
try:  # pragma: no cover - optional convenience
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # ImportError or other issues are non-fatal
    pass


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
STRUCTURED_DIR = OUTPUTS_DIR / "structured"
REPORTS_DIR = OUTPUTS_DIR / "reports"
LOGS_DIR = PROJECT_ROOT / "logs"


@dataclass
class GroqConfig:
    api_key: str
    model_name: str = "qwen/qwen3-32b"  # Qwen3-32B model


@dataclass
class HttpConfig:
    remote_mcp_base_url: str = "http://localhost:8000"  # FastAPI remote MCP


@dataclass
class WeatherConfig:
    # Open-Meteo is free and does not require an API key, but config is kept
    # here in case we later swap to a different provider.
    base_geocoding_url: str = "https://geocoding-api.open-meteo.com/v1/search"
    base_weather_url: str = "https://api.open-meteo.com/v1/forecast"


@dataclass
class AppConfig:
    groq: GroqConfig
    http: HttpConfig = field(default_factory=HttpConfig)
    weather: WeatherConfig = field(default_factory=WeatherConfig)

    def ensure_directories(self) -> None:
        """Ensure base runtime directories exist (best-effort).

        The assignment requires final artifacts to be written via a local
        STDIO tool, but creating these directories eagerly is convenient for
        logs and temporary files. It is safe if they already exist.
        """

        for path in [DATA_DIR, OUTPUTS_DIR, STRUCTURED_DIR, REPORTS_DIR, LOGS_DIR]:
            path.mkdir(parents=True, exist_ok=True)


def load_config() -> AppConfig:
    """Load configuration from environment variables.

    The only required secret is GROQ_API_KEY; others have reasonable defaults.
    """

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY environment variable is not set.")

    groq = GroqConfig(api_key=api_key)
    cfg = AppConfig(groq=groq)
    cfg.ensure_directories()
    return cfg

