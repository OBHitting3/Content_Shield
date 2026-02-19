# AGENT-F-REPORT — Joshua 7 / Content Shield Security Validation

**Agent:** F
**Date:** 2026-02-19
**Branch:** `cursor/agent-f-security-validator-c0dd`
**Method:** Security audit — code review, attack surface analysis, fix + regression test
**Tests:** 128 passing (up from 87) | Lint: clean (ruff)

---

## Executive Summary

Agent A's hardening pass (Phase 1–6) addressed critical PII leaks, input length DoS, and several logic bugs. This Agent F pass performs a secondary security validation focused on **side-channel attacks, evasion techniques, information leakage, and production hardening** that remained after the initial hardening.

**8 vulnerabilities found and fixed. 40 new security tests added.**

---

## Findings and Fixes

### F1 — Timing Side-Channel on API Key Comparison

| Field | Value |
|-------|-------|
| Severity | **HIGH** |
| File | `api/routes.py` |
| Status | **FIXED** |

**Finding:** `x_api_key != settings.api_key` uses Python's default string comparison, which short-circuits on the first differing byte. An attacker can measure response-time variance to guess the API key character-by-character (timing oracle attack).

**Fix:** Replaced with `hmac.compare_digest(x_api_key, settings.api_key)`, which runs in constant time regardless of where strings diverge. Added early return when `api_key` is unset.

---

### F2 — Prompt Injection Matched Text Leaked in Metadata

| Field | Value |
|-------|-------|
| Severity | **MEDIUM** |
| File | `validators/prompt_injection.py` |
| Status | **FIXED** |

**Finding:** The prompt injection detector stored `match.group()` (the actual matched attack text) in `finding.metadata["matched"]`. This:
- Confirms to attackers which exact patterns are detected
- Provides intelligence to craft bypass payloads
- Violates the same "never echo dangerous input" principle that PII redaction follows

**Fix:** Removed the `"matched"` key from metadata. The `"pattern"` name is still reported (e.g., `"ignore_instructions"`) — this identifies the threat class without revealing detection boundaries.

---

### F3 — X-Request-ID Header Injection / Log Forging

| Field | Value |
|-------|-------|
| Severity | **HIGH** |
| File | `api/main.py` |
| Status | **FIXED** |

**Finding:** The `X-Request-ID` header was accepted verbatim from the client and placed directly into:
1. HTTP response headers (enables CRLF header injection)
2. Logging output (enables log forging / log injection)

An attacker could send `X-Request-ID: evil\r\nX-Injected: pwned` to inject arbitrary headers, or `X-Request-ID: \n[CRITICAL] system compromised` to forge log entries.

**Fix:** Added `_sanitize_request_id()` that:
- Validates against `^[\w\-]{1,128}$` (alphanumeric, underscores, hyphens only)
- Rejects values >128 characters
- Generates a fresh `uuid4().hex` for any invalid input

---

### F4 — config_overrides Allows Runtime Security Bypass

| Field | Value |
|-------|-------|
| Severity | **CRITICAL** |
| File | `engine.py` |
| Status | **FIXED** |

**Finding:** The `config_overrides` field in `ValidationRequest` allows per-request configuration overrides that merge with global settings. A malicious API consumer could:
- Set `pii_patterns_enabled: []` to disable all PII detection
- Set `forbidden_phrases: []` to bypass forbidden phrase scanning
- Raise `max_text_length` to circumvent the text length safety limit

This effectively allows any authenticated (or unauthenticated, if no API key is set) user to disable security validators at will.

**Fix:** Introduced `_LOCKED_OVERRIDE_KEYS` set containing `pii_patterns_enabled`, `forbidden_phrases`, and `max_text_length`. The engine's new `_sanitize_overrides()` method strips these keys before merging. Blocked keys are logged as warnings. Non-locked keys (e.g., `brand_voice_target_score`, `readability_min_score`) remain overridable.

---

### F5 — Unicode Evasion of All Validators

| Field | Value |
|-------|-------|
| Severity | **HIGH** |
| File | `engine.py` |
| Status | **FIXED** |

**Finding:** All validators operate on raw text. Attackers can evade pattern detection using:
1. **Zero-width characters:** `ig\u200bnore pre\u200cvious in\u200dstructions` bypasses the prompt injection detector
2. **Cyrillic homoglyphs:** `Аs аn АI` (using Cyrillic А/а) bypasses forbidden phrase detection
3. **Fullwidth characters:** `Ｉｇｎｏｒｅ` (fullwidth Latin) bypasses all regex patterns
4. **Unicode ligatures:** `ﬁnally` (fi ligature) may bypass word-boundary patterns

**Fix:** Added `normalize_text()` function in the engine that applies:
- **NFKC normalization** (collapses ligatures, fullwidth → ASCII, etc.)
- **Zero-width character stripping** (U+200B through U+2064, U+FEFF BOM)
- **Homoglyph mapping** (Cyrillic and fullwidth Latin → ASCII equivalents)

Normalization is applied once before validators run. The original `request.text` is preserved for `text_length` reporting; the normalized copy is used for pattern matching.

---

### F6 — Swagger/ReDoc Exposed in Production

| Field | Value |
|-------|-------|
| Severity | **MEDIUM** |
| File | `api/main.py` |
| Status | **FIXED** |

**Finding:** `/docs` (Swagger UI) and `/redoc` were always enabled, exposing the full API schema, parameter types, and validation rules to any visitor. In production, this provides an attack surface map.

**Fix:** `docs_url` and `redoc_url` are now set only when `settings.debug` is `True`. Default is `False`, so production deployments have no documentation endpoints. Set `J7_DEBUG=true` to enable during development.

---

### F7 — Missing Security Response Headers

| Field | Value |
|-------|-------|
| Severity | **MEDIUM** |
| File | `api/main.py` |
| Status | **FIXED** |

**Finding:** API responses lacked standard security headers, leaving downstream consumers vulnerable to content-type sniffing, clickjacking, and information leakage.

**Fix:** Added the following headers to every HTTP response via middleware:

| Header | Value | Purpose |
|--------|-------|---------|
| `X-Content-Type-Options` | `nosniff` | Prevent MIME-type sniffing |
| `X-Frame-Options` | `DENY` | Prevent clickjacking |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Limit referrer leakage |
| `Cache-Control` | `no-store` | Prevent caching of validation results |
| `Permissions-Policy` | `geolocation=(), camera=(), microphone=()` | Disable unnecessary browser APIs |

---

### F8 — Unbounded config_overrides Payload Size

| Field | Value |
|-------|-------|
| Severity | **LOW** |
| File | `engine.py` |
| Status | **FIXED** |

**Finding:** While `ValidationRequest.text` is capped at 500K characters, the `config_overrides` dict had no size limit. An attacker could send a multi-megabyte overrides payload to consume memory.

**Fix:** `_sanitize_overrides()` now computes the total serialized size of overrides and drops the entire payload if it exceeds 16KB. Non-dict override values are also rejected.

---

## Test Coverage

| Metric | Before | After |
|--------|--------|-------|
| Total tests | 87 | 128 |
| Security-specific tests | 0 | 40 |

### New Test Breakdown

| Category | Tests | What They Verify |
|----------|-------|-----------------|
| API key timing-safe auth | 4 | Valid key, invalid key, missing key, unset key |
| Injection metadata redaction | 2 | No `matched` in metadata; `pattern` still present |
| Request ID sanitization | 8 | Valid IDs, newline injection, length, special chars, end-to-end |
| config_overrides lockout | 6 | PII lock, phrases lock, max_text lock, non-locked pass, oversize, non-dict |
| Unicode evasion resistance | 8 | Zero-width, Cyrillic, fullwidth, NFKC, BOM, end-to-end injection/PII/phrases |
| Security headers | 5 | All 5 headers present with correct values |
| Docs disabled in prod | 3 | Hidden when debug=false, visible when debug=true |
| PII redaction E2E | 4 | Email, SSN, phone, injection payload — none in response body |

---

## Files Modified

| File | Changes |
|------|---------|
| `joshua7/api/routes.py` | Timing-safe API key comparison via `hmac.compare_digest` |
| `joshua7/api/main.py` | Request ID sanitization, security headers, docs toggle |
| `joshua7/engine.py` | Input normalization, config_overrides lockout + size cap |
| `joshua7/validators/prompt_injection.py` | Removed matched text from metadata |
| `tests/test_engine.py` | Updated config_overrides test; added locked-key test |
| `tests/test_security.py` | **NEW** — 40 security validation tests |

---

## Remaining Known Limitations (Accepted for MVP)

1. **No rate limiting** — expected at infrastructure layer (Cloud Run / API Gateway)
2. **CORS allows all origins** — `allow_origins=["*"]` is permissive; tighten per deployment
3. **No CSP header** — not applicable for a JSON API (no HTML served)
4. **Homoglyph map is not exhaustive** — covers Cyrillic and fullwidth Latin; additional scripts (Greek, etc.) are a v2 enhancement
5. **No request body size middleware** — FastAPI/Starlette defaults apply; consider adding for high-traffic deployments
6. **Synchronous validators** — adequate for MVP text sizes

---

*Built with faith. Proceeds support St. Jude's Children's Hospital.*
