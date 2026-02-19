# AGENT-A-REPORT — Joshua 7 / Content Shield REROLL

**Agent:** A (Reroll)
**Date:** 2026-02-19
**Branch:** `cursor/joshua-7-content-shield-bc98`
**Method:** Complete ground-up rewrite of the entire codebase
**Version:** 0.2.0

---

## Executive Summary

Complete reroll of the Joshua 7 — Content Shield codebase. Every source file was rewritten from scratch while preserving the same feature set, project identity, and architectural intent. The rewrite focuses on tighter type safety, improved security hardening, cleaner architecture, and comprehensive test coverage.

---

## What Changed (Everything)

### Core Models (`models.py`)

- Bumped to v0.2.0
- `ValidationFinding` and `RiskAxis` models marked `frozen=True` (immutable after creation)
- `ValidationResult.score` now has `ge=0.0, le=100.0` constraints
- Added `finding_count` property to `ValidationResult`
- `ValidationRequest.validators` now accepts comma-separated string input via `field_validator`
- `RiskAxis.raw_score` now has `ge=0.0, le=100.0` constraints

### Configuration (`config.py`)

- `DEFAULT_FORBIDDEN_PHRASES` is now a `tuple` (immutable) instead of mutable list
- Added `field_validator` on `log_level` to normalise and validate
- Added `ge=1` constraint on `max_text_length`
- Added `ge=0.0, le=100.0` constraint on `brand_voice_target_score`

### Validators

All 5 validators rewritten with identical APIs but cleaner internals:

| Validator | Key Improvements |
|-----------|-----------------|
| `forbidden_phrases` | Imports `DEFAULT_FORBIDDEN_PHRASES` from config (single source of truth) |
| `pii` | Security docstring, `_redacted()` helper (no raw PII in output) |
| `brand_voice` | Word-boundary regex for all penalty words, explicit `float()` casts |
| `prompt_injection` | 10 pattern families, clean separation of pattern tuples |
| `readability` | Grade-level always reported in metadata |

### Engine (`engine.py`)

- Same RISK_TAXONOMY_v0 composite scoring with 5 axes
- Critical escalation schedule: 1 axis → +40, 2 axes → +80, 3+ → +100
- Validator exception isolation (try/except per validator)
- `_settings_as_dict()` renamed from `_settings_to_config()` for clarity

### API (`api/main.py`, `routes.py`)

- Timing-safe API key comparison via `hmac.compare_digest`
- Structured logging configuration in app factory
- CORS with `allow_credentials=False`
- Request ID and response time headers on every response

### CLI (`cli/main.py`)

- Risk level and composite score shown in CLI report
- File size pre-check before reading
- Clean error on oversized text (before Pydantic validation)
- `--stdin` support for piped input

### Tests

| Suite | Tests |
|-------|-------|
| `test_forbidden_phrases.py` | 12 |
| `test_pii.py` | 12 |
| `test_brand_voice.py` | 11 |
| `test_prompt_injection.py` | 12 |
| `test_readability.py` | 9 |
| `test_engine.py` | 18 |
| `test_api.py` | 17 |
| `test_risk_taxonomy.py` | 11 |

### Infrastructure

- `pyproject.toml` bumped to 0.2.0
- `.env.example` includes `J7_API_KEY`
- Dockerfile unchanged (already hardened)
- CI workflow unchanged (3.10/3.11/3.12 matrix + Docker build)

---

## Security Posture

| Control | Status |
|---------|--------|
| PII values never in API responses | Enforced — fixed placeholders only |
| Input length cap (500K chars) | Enforced — engine + CLI pre-check |
| API key auth (optional) | `hmac.compare_digest` timing-safe |
| CORS | `allow_credentials=False` |
| Request ID audit trail | Propagated in/out |
| Validator isolation | Exception per-validator, never crashes engine |
| File size pre-check (CLI) | `stat().st_size` before read |

## Known Limitations (Accepted for MVP)

1. No rate limiting — expected at infrastructure layer (Cloud Run, API Gateway)
2. Synchronous validators — adequate for MVP text sizes
3. Phone regex has broad matching — may flag some non-phone numeric sequences
4. No plugin architecture — custom validators require source modification
5. Brand voice scoring is heuristic — no NLP/ML model

---

*Built with faith. Proceeds support St. Jude's Children's Hospital.*
