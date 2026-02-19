"""Application settings for Joshua 7."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "default.yaml"

_DEFAULT_FORBIDDEN_PHRASES: list[str] = [
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

    model_config = SettingsConfigDict(env_prefix="J7_", env_nested_delimiter="__")

    app_name: str = "Joshua 7"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"

    max_text_length: int = 500_000

    forbidden_phrases: list[str] = Field(default_factory=lambda: list(_DEFAULT_FORBIDDEN_PHRASES))
    pii_patterns_enabled: list[str] = Field(
        default_factory=lambda: ["email", "phone", "ssn", "credit_card"]
    )

    brand_voice_target_score: float = 60.0
    brand_voice_keywords: list[str] = Field(default_factory=list)
    brand_voice_tone: str = "professional"

    readability_min_score: float = 30.0
    readability_max_score: float = 80.0

    toxicity_threshold: float = 0.5
    toxicity_categories_enabled: list[str] = Field(
        default_factory=lambda: [
            "threat",
            "harassment",
            "profanity",
            "discrimination",
            "self_harm",
        ]
    )

    api_key: str = ""

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, v: str) -> str:
        return v.lower()

    @field_validator("max_text_length")
    @classmethod
    def max_text_length_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("max_text_length must be at least 1")
        return v

    @classmethod
    def from_yaml(cls, path: Path | str | None = None) -> Settings:
        config_path = Path(path) if path else _DEFAULT_CONFIG_PATH
        overrides: dict[str, Any] = {}
        if config_path.exists():
            with open(config_path) as f:
                raw = yaml.safe_load(f) or {}
            if not isinstance(raw, dict):
                logger.warning("YAML config at %s is not a mapping — ignoring", config_path)
                raw = {}
            overrides = raw
        else:
            logger.debug("Config file not found at %s — using defaults", config_path)
        return cls(**overrides)


def get_settings(config_path: Path | str | None = None) -> Settings:
    """Factory that returns a Settings instance."""
    if config_path:
        return Settings.from_yaml(config_path)
    return Settings()
