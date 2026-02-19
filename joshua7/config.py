"""Application settings for Joshua 7 — layered config from env, YAML, and defaults."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "default.yaml"

DEFAULT_FORBIDDEN_PHRASES: tuple[str, ...] = (
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
)


class Settings(BaseSettings):
    """Global settings, loadable from J7_-prefixed env vars or a YAML file."""

    model_config = SettingsConfigDict(env_prefix="J7_", env_nested_delimiter="__")

    app_name: str = "Joshua 7"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"

    max_text_length: int = Field(default=500_000, ge=1)

    forbidden_phrases: list[str] = Field(
        default_factory=lambda: list(DEFAULT_FORBIDDEN_PHRASES),
    )
    pii_patterns_enabled: list[str] = Field(
        default_factory=lambda: ["email", "phone", "ssn"],
    )

    brand_voice_target_score: float = Field(default=60.0, ge=0.0, le=100.0)
    brand_voice_keywords: list[str] = Field(default_factory=list)
    brand_voice_tone: str = "professional"

    readability_min_score: float = Field(default=30.0)
    readability_max_score: float = Field(default=80.0)

    api_key: str = ""

    @field_validator("log_level")
    @classmethod
    def _normalise_log_level(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in ("debug", "info", "warning", "error", "critical"):
            raise ValueError(f"Invalid log_level: {v!r}")
        return v

    @classmethod
    def from_yaml(cls, path: Path | str | None = None) -> Settings:
        config_path = Path(path) if path else _DEFAULT_CONFIG_PATH
        overrides: dict[str, Any] = {}
        if config_path.exists():
            with open(config_path) as fh:
                raw = yaml.safe_load(fh) or {}
            if not isinstance(raw, dict):
                logger.warning("YAML config at %s is not a mapping — ignoring", config_path)
                raw = {}
            overrides = raw
        else:
            logger.debug("Config file not found at %s — using defaults", config_path)
        return cls(**overrides)


def get_settings(config_path: Path | str | None = None) -> Settings:
    """Factory: returns a Settings instance (from YAML if path given, else env+defaults)."""
    if config_path:
        return Settings.from_yaml(config_path)
    return Settings()
