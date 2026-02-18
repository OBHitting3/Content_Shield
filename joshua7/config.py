"""Application settings for Joshua 7."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings

_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "default.yaml"

_DEFAULT_FORBIDDEN_PHRASES = [
    "as an ai",
    "as a language model",
    "i cannot and will not",
    "i'm just an ai",
    "delve",
    "leverage",
    "synergy",
    "game-changer",
    "circle back",
    "deep dive",
    "unpack",
    "at the end of the day",
]


class Settings(BaseSettings):
    """Global application settings, loadable from env vars or YAML."""

    app_name: str = "Joshua 7"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"

    api_key: str | None = Field(
        default=None,
        description=(
            "Optional API key for FastAPI endpoints. If set, requests to /api/v1/* must "
            "include matching X-API-Key header."
        ),
    )

    forbidden_phrases: list[str] = Field(default_factory=lambda: list(_DEFAULT_FORBIDDEN_PHRASES))
    pii_patterns_enabled: list[str] = Field(default_factory=lambda: ["email", "phone", "ssn"])

    brand_voice_target_score: float = 60.0
    brand_voice_keywords: list[str] = Field(default_factory=list)
    brand_voice_tone: str = "professional"

    prompt_injection_threshold: float = 0.6
    readability_min_score: float = 30.0
    readability_max_score: float = 80.0

    model_config = {"env_prefix": "J7_"}

    @classmethod
    def from_yaml(cls, path: Path | str | None = None) -> Settings:
        config_path = Path(path) if path else _DEFAULT_CONFIG_PATH
        overrides: dict[str, Any] = {}
        if config_path.exists():
            with open(config_path) as f:
                raw = yaml.safe_load(f) or {}
            overrides = raw
        return cls(**overrides)


def get_settings(config_path: Path | str | None = None) -> Settings:
    """Factory that returns a Settings instance."""
    if config_path:
        return Settings.from_yaml(config_path)
    return Settings()
