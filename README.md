# Joshua 7 — Content Shield

Pre-publication AI content validation engine.

**Company:** Content Shield (Iron Forge Studios)
**Software:** Joshua 7
**Mission:** Defend human creators from AI-generated content risks before they publish.

## Validators (MVP)

| # | Validator | Purpose |
|---|-----------|---------|
| 1 | Forbidden Phrase Detector | Flag banned words/phrases in content |
| 2 | PII Validator | Detect emails, phone numbers, SSNs, credit cards (values are **never** returned — always redacted) |
| 3 | Brand Voice Scorer | Score content against a target brand-voice profile |
| 4 | Prompt Injection Detector | Catch hidden prompt-injection attempts (16 pattern families) |
| 5 | Readability Scorer | Flesch-Kincaid readability gate with grade-level reporting |

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

Every response includes `request_id`, `timestamp`, `version`, and `X-Response-Time-Ms` header.

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
├── engine.py          # Orchestrates all validators
├── regex_guard.py     # ReDoS-safe regex execution
├── sanitize.py        # Input sanitization (null bytes, homoglyphs, NFC)
├── validators/
│   ├── base.py        # Abstract base validator
│   ├── forbidden_phrases.py
│   ├── pii.py
│   ├── brand_voice.py
│   ├── prompt_injection.py
│   └── readability.py
├── api/
│   ├── main.py        # FastAPI app factory
│   ├── routes.py      # /validate endpoint
│   └── security.py    # Security middleware (headers, rate limit, body limit)
└── cli/
    └── main.py        # Typer CLI entry point
```

## Security

Joshua 7 ships with defense-in-depth security hardening:

| Layer | Control | Config |
|-------|---------|--------|
| **Auth** | Optional API key via `X-API-Key` header (timing-safe comparison) | `J7_API_KEY` |
| **Rate Limiting** | Sliding-window per-IP rate limiter | `J7_RATE_LIMIT_RPM`, `J7_RATE_LIMIT_BURST` |
| **Body Size** | Rejects request bodies exceeding the configured limit | `J7_MAX_REQUEST_BODY_BYTES` (default 4 MB) |
| **Security Headers** | `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `CSP`, `Referrer-Policy`, `Permissions-Policy`, `Cache-Control: no-store` | Always on |
| **CORS** | Configurable allowed origins (`allow_credentials=False`) | `J7_CORS_ALLOWED_ORIGINS` |
| **Trusted Hosts** | Host header validation | `J7_TRUSTED_HOSTS` |
| **Input Sanitization** | Null bytes, zero-width chars, homoglyphs, NFC normalization | Always on |
| **ReDoS Guard** | Timeout-protected regex execution | Always on |
| **PII Redaction** | Raw PII values are **never** echoed — always redacted with fixed placeholders | Always on |
| **Input Limits** | Text capped at configurable max (default 500K chars) | `J7_MAX_TEXT_LENGTH` |
| **Request ID** | Validated/sanitized to prevent log injection (alphanumeric + `-_`, max 128 chars) | Via `X-Request-ID` header |
| **Config Override Guard** | Security-sensitive settings blocked from per-request overrides | Always on |
| **Exception Handling** | Global handler prevents stack trace leakage | Always on |
| **Docs Disabled** | `/docs` and `/redoc` disabled in production; enabled when `J7_DEBUG=true` | `J7_DEBUG` |

## Docker

```bash
docker build -t joshua7 .
docker run -p 8000:8000 joshua7
```

## License

Proprietary — Content Shield (Iron Forge Studios)

---

*Built with faith. Proceeds support St. Jude's Children's Hospital.*
