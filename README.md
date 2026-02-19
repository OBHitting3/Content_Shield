# Joshua 7 — Content Shield

Pre-publication AI content validation engine.

**Company:** Content Shield (Iron Forge Studios)
**Software:** Joshua 7 v0.2.0
**Mission:** Defend human creators from AI-generated content risks before they publish.

## Validators

| # | Validator | Purpose |
|---|-----------|---------|
| 1 | Forbidden Phrase Detector | Flag banned words/phrases (AI slop, corporate jargon) |
| 2 | PII Validator | Detect emails, phone numbers, SSNs, credit cards (values **never** returned — always redacted) |
| 3 | Brand Voice Scorer | Score content against a target brand-voice profile |
| 4 | Prompt Injection Detector | Catch hidden prompt-injection attempts (15 pattern families) |
| 5 | Readability Scorer | Flesch-Kincaid readability gate with grade-level reporting |
| 6 | Toxicity Detector | Flag threatening, harassing, discriminatory, or harmful content |

## RISK_TAXONOMY_v1

Every validation response includes a 6-axis composite risk score:

| Axis | Label | Weight |
|------|-------|--------|
| A | Synthetic Artifacts | 20% |
| B | Hallucination / Factual Integrity | 15% |
| C | Brand Safety / GARM | 15% |
| D | Regulatory Compliance / PII+Disclosure | 15% |
| E | Adversarial Robustness / Injection | 15% |
| F | Content Toxicity / Safety | 20% |

Risk levels: **GREEN** (0-19) | **YELLOW** (20-49) | **ORANGE** (50-79) | **RED** (80-100)

CRITICAL findings trigger escalation: 1 axis → +30, 2 axes → +60, 3+ axes → +100 (hard RED).

## Quick Start

```bash
# Install
pip install -e ".[dev]"

# Run CLI
joshua7 validate --text "Check this content for issues."
joshua7 validate --file article.txt
echo "piped content" | joshua7 validate --stdin

# JSON output
joshua7 validate --text "Hello world" --json

# List available validators
joshua7 list

# Run API server
joshua7 serve --port 8000

# Run tests
pytest
```

## API

```bash
# Health check
curl http://localhost:8000/health

# Validate content
curl -X POST http://localhost:8000/api/v1/validate \
  -H "Content-Type: application/json" \
  -d '{"text": "Contact me at john@example.com", "validators": ["all"]}'

# List validators
curl http://localhost:8000/api/v1/validators

# Pass a request ID for tracing
curl -X POST http://localhost:8000/api/v1/validate \
  -H "Content-Type: application/json" \
  -H "X-Request-ID: my-trace-id" \
  -d '{"text": "Some content to check"}'
```

Every response includes `request_id`, `timestamp`, `version`, `risk`, and `X-Response-Time-Ms` header.

## Configuration

Settings are loaded from (in priority order):
1. Environment variables with `J7_` prefix (e.g. `J7_MAX_TEXT_LENGTH=100000`)
2. YAML config file (pass `--config path/to/config.yaml` to CLI)
3. Built-in defaults

See `.env.example` for all available environment variables.

## Stack

Python · FastAPI · Typer CLI · Pydantic v2 · Cloud Run ready

## Project Structure

```
joshua7/
├── __init__.py
├── config.py          # Settings & configuration
├── models.py          # Pydantic data models
├── engine.py          # Orchestrates all validators + risk taxonomy
├── validators/
│   ├── base.py        # Abstract base validator
│   ├── forbidden_phrases.py
│   ├── pii.py
│   ├── brand_voice.py
│   ├── prompt_injection.py
│   ├── readability.py
│   └── toxicity.py
├── api/
│   ├── main.py        # FastAPI app factory
│   └── routes.py      # /validate endpoint
└── cli/
    └── main.py        # Typer CLI entry point
```

## Security

- PII values are **always redacted** in API responses — raw emails, SSNs, phone numbers, and credit card numbers are never echoed back.
- Input text is capped at a configurable maximum (default 500K chars) to prevent memory exhaustion.
- CORS middleware is enabled with `allow_credentials=False`.
- Request IDs are propagated for audit trails.
- Optional API key authentication via `X-API-Key` header (`J7_API_KEY` env var).
- Unhandled exceptions return a generic 500 — no tracebacks leaked.

## Docker

```bash
docker build -t joshua7 .
docker run -p 8000:8000 joshua7
```

## License

Proprietary — Content Shield (Iron Forge Studios)

---

*Built with faith. Proceeds support St. Jude's Children's Hospital.*
