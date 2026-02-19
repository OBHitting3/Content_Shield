"""Application settings for Joshua 7."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

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


_SAFE_OVERRIDE_KEYS: frozenset[str] = frozenset(
    {
        "forbidden_phrases",
        "brand_voice_target_score",
        "brand_voice_keywords",
        "brand_voice_tone",
        "readability_min_score",
        "readability_max_score",
    }
)


class Settings(BaseSettings):
    """Global application settings, loadable from env vars or YAML."""

    model_config = SettingsConfigDict(env_prefix="J7_", env_nested_delimiter="__")

    app_name: str = "Joshua 7"
    debug: bool = False
    host: str = "127.0.0.1"
    port: int = 8000
    log_level: str = "info"

    max_text_length: int = 500_000
    max_findings_per_validator: int = 50

    forbidden_phrases: list[str] = Field(default_factory=lambda: list(_DEFAULT_FORBIDDEN_PHRASES))
    pii_patterns_enabled: list[str] = Field(
        default_factory=lambda: ["email", "phone", "ssn", "credit_card"]
    )

    brand_voice_target_score: float = 60.0
    brand_voice_keywords: list[str] = Field(default_factory=list)
    brand_voice_tone: str = "professional"

    readability_min_score: float = 30.0
    readability_max_score: float = 80.0

    api_key: str = ""

    cors_allowed_origins: list[str] = Field(
        default_factory=lambda: ["*"],
        description="Allowed CORS origins. Set to specific domains in production.",
    )
    rate_limit_rpm: int = Field(
        default=60,
        description="Max requests per minute per client IP (0 = disabled).",
    )
    rate_limit_burst: int = Field(
        default=10,
        description="Burst allowance above the sustained rate limit.",
    )
    max_request_body_bytes: int = Field(
        default=4 * 1024 * 1024,
        description="Hard cap on request body size in bytes (default 4 MB).",
    )
    trusted_hosts: list[str] = Field(
        default_factory=lambda: ["*"],
        description="Trusted hostnames for Host header validation. ['*'] = any.",
    )

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
    """Factory that returns a Settings instance.

    Always loads the default YAML config (if it exists) as a baseline, then
    applies env-var overrides on top.  Pass *config_path* to use a custom YAML
    file instead of the default.
    """
    return Settings.from_yaml(config_path)
