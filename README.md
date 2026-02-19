# Joshua 7 — Content Shield

Pre-publication AI content validation engine.

**Company:** Content Shield (Iron Forge Studios)
**Software:** Joshua 7
**Mission:** Defend human creators from AI-generated content risks before they publish.

## Validators (MVP)

| # | Validator | Purpose |
|---|-----------|---------|
| 1 | Forbidden Phrase Detector | Flag banned words/phrases in content |
| 2 | PII Validator | Detect emails, phone numbers, SSNs (values are **never** returned — always redacted) |
| 3 | Brand Voice Scorer | Score content against a target brand-voice profile |
| 4 | Prompt Injection Detector | Catch hidden prompt-injection attempts (10 pattern families) |
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
├── validators/
│   ├── base.py        # Abstract base validator
│   ├── forbidden_phrases.py
│   ├── pii.py
│   ├── brand_voice.py
│   ├── prompt_injection.py
│   └── readability.py
├── api/
│   ├── main.py        # FastAPI app factory
│   └── routes.py      # /validate endpoint
└── cli/
    └── main.py        # Typer CLI entry point
```

## Security

- **PII Redaction**: Raw emails, SSNs, and phone numbers are **never** echoed back in API responses.
- **Input Limits**: Text capped at 500K chars; request body hard-capped at 4 MB (configurable).
- **Timing-Safe Auth**: API key comparison uses HMAC constant-time comparison to prevent timing attacks.
- **Rate Limiting**: In-memory sliding-window rate limiter (default 60 req/min per client IP). Health endpoint is exempt.
- **Security Headers**: Every response includes `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `CSP`, `Referrer-Policy`, `Permissions-Policy`, and `Cache-Control: no-store`. HSTS is set over HTTPS.
- **CORS Hardening**: Origins, methods, and exposed headers are configurable (default `*` for dev).
- **Request ID Sanitization**: `X-Request-ID` is sanitized to prevent log/header injection (alphanumeric + hyphen/underscore, max 128 chars).
- **Config Override Sandboxing**: API `config_overrides` are restricted to validator-tuning keys only; infrastructure keys (`api_key`, `debug`, `host`, `port`, `max_text_length`) are silently blocked.
- **Error Sanitization**: Custom exception handlers ensure stack traces and internal paths never leak in API responses.
- **Trusted Host Validation**: Configurable via `J7_TRUSTED_HOSTS` (default allows all; restrict in production).
- **Audit Logging**: Security-relevant events (auth failures, rate limit hits, blocked overrides, sanitized headers) are logged at WARNING level.

## Docker

```bash
docker build -t joshua7 .
docker run -p 8000:8000 joshua7
```

## License

Proprietary — Content Shield (Iron Forge Studios)

---

*Built with faith. Proceeds support St. Jude's Children's Hospital.*
