# Antigravity Quota API - Improvement Plan

## Project Overview
The **antigravity-quota** project is a FastAPI-based REST API (v0.3.0) that monitors Google Cloud Code AI model quotas for Gemini and Claude models. It features automatic OAuth token refresh, request caching, and terminal-friendly output with ANSI colors.

**Tech Stack:** Python 3.13, FastAPI, httpx, pytest, Docker, uv package manager
**Current State:** Well-structured, production-ready, ~1141 lines of code with good documentation

---

## Improvement Recommendations

### 🔴 **CRITICAL PRIORITY** - Security & Reliability

#### 1. Add API Authentication
**Problem:** All endpoints are publicly accessible without any authentication
**Risk:** Anyone can query your quota data
**Solution:**
- Add API key middleware or JWT-based authentication
- Protect `/quota/*` endpoints while keeping `/docs` accessible
- Store API keys in environment variables
- **Files to modify:**
  - `src/api.py` - Add authentication dependency
  - `src/config.py` - Add API_KEY configuration
  - `.env.example` - Document API_KEY variable
- **Implementation:** Use FastAPI's `Depends()` with a custom auth validator

#### 2. Implement Rate Limiting
**Problem:** No protection against API abuse
**Risk:** DoS attacks, quota exhaustion from spam requests
**Solution:**
- Add `slowapi` library for FastAPI rate limiting
- Configure reasonable limits (e.g., 60 requests/minute per client)
- **Files to modify:**
  - `pyproject.toml` - Add slowapi dependency
  - `src/api.py` - Add rate limiter middleware
- **Implementation:**
  ```python
  from slowapi import Limiter, _rate_limit_exceeded_handler
  from slowapi.util import get_remote_address
  ```

#### ~~3. Replace Global Cache with Thread-Safe Solution~~
#### ~~4. Fix Bare Exception Handler~~
---

### 🟡 **HIGH PRIORITY** - DevOps & Code Quality

#### 5. Create CI/CD Pipeline
**Problem:** No automated testing, linting, or deployment
**Impact:** Manual testing burden, potential for broken deployments
**Solution:** Create GitHub Actions workflow
- **New file:** `.github/workflows/ci.yml`
- **Pipeline stages:**
  1. Lint with `ruff` (seems to be intended, `.ruff_cache` in .gitignore)
  2. Type check with `mypy` or `pyright`
  3. Run tests with `pytest` + coverage reporting
  4. Security scan with `safety` or `trivy`
  5. Build Docker image
  6. Push to container registry (optional)

**Example workflow:**
```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv sync --all-groups
      - run: uv run ruff check .
      - run: uv run mypy src/
      - run: uv run pytest --cov=src --cov-report=term-missing
      - run: safety check
```

#### 6. Add Code Coverage Tracking
**Problem:** No visibility into test coverage
**Current:** pytest configured, but no coverage tool
**Solution:**
- Add `pytest-cov` to dev dependencies
- Configure coverage thresholds (aim for 80%+)
- **Files to modify:**
  - `pyproject.toml` - Add pytest-cov, configure coverage settings
- **Configuration:**
  ```toml
  [tool.pytest.ini_options]
  testpaths = ["test"]
  addopts = "--cov=src --cov-report=html --cov-report=term-missing --cov-fail-under=80"
  ```

#### 7. Configure Type Checking
**Problem:** Type hints exist but no enforcement
**Current:** Good type annotations, but no mypy/pyright
**Solution:**
- Add `mypy` or `pyright` to dev dependencies
- Configure strict mode for maximum safety
- **Files to modify:**
  - `pyproject.toml` - Add type checker dependency and config
- **Configuration:**
  ```toml
  [tool.mypy]
  python_version = "3.13"
  strict = true
  warn_return_any = true
  warn_unused_configs = true
  ```

#### 8. Add Linting & Formatting
**Problem:** No code style enforcement
**Evidence:** `.ruff_cache` in .gitignore suggests intent to use ruff
**Solution:**
- Add `ruff` for linting and formatting
- Configure rules and format settings
- **Files to modify:**
  - `pyproject.toml` - Add ruff dependency and configuration
- **Configuration:**
  ```toml
  [tool.ruff]
  line-length = 100
  select = ["E", "F", "I", "N", "W", "UP"]
  fix = true
  ```

#### 9. Add Dependency Automation
**Problem:** No automated dependency updates or security scanning
**Risk:** Outdated packages, known vulnerabilities
**Solution:**
- Enable GitHub Dependabot or Renovate
- **New file:** `.github/dependabot.yml`
- **Configuration:**
  ```yaml
  version: 2
  updates:
    - package-ecosystem: "pip"
      directory: "/"
      schedule:
        interval: "weekly"
  ```

---

### 🟢 **MEDIUM PRIORITY** - Improvements

#### 10. Refactor to Pydantic Models
**Problem:** Dictionary-based data passing, prone to KeyError
**Example:** `src/api.py` returns plain dicts, not validated models
**Benefits:**
- Automatic validation
- Better IDE autocomplete
- Self-documenting code
- Type safety
**Solution:**
- Create Pydantic models for quota responses
- **New file:** `src/models.py`
- **Models needed:**
  - `QuotaModel` - Single model quota info
  - `QuotaResponse` - API response wrapper
  - `TokenData` - OAuth token structure
- **Files to modify:**
  - `src/api.py` - Use Pydantic models for responses
  - `src/cloudcode_client.py` - Use models for data structures

#### ~~11. Extract Magic Numbers to Constants~~
#### 12. Enhance Logging
**Problem:** Minimal logging, not configurable
**Current:** Only 5 log statements in cloudcode_client.py, none in api.py
**Solution:**
- Add comprehensive logging throughout
- Make log level configurable via environment variable
- Consider structured logging (JSON) for production
- **Files to modify:**
  - `src/config.py` - Add LOG_LEVEL environment variable
  - `main.py` - Use config.LOG_LEVEL
  - `src/api.py` - Add request/response logging
  - `src/cloudcode_client.py` - Add debug and error logging

#### 13. Improve Error Handling
**Problem:** Inconsistent error handling, generic HTTP 500 status codes
**Issues:**
- All HTTPExceptions use 500 status
- Should use 401 (Unauthorized), 403 (Forbidden), 503 (Service Unavailable)
**Solution:**
- Use appropriate HTTP status codes
- Add custom exception classes
- **Files to modify:**
  - `src/api.py` - Use specific status codes
  - `src/cloudcode_client.py` - Raise specific exceptions

#### 14. Add Structured Logging
**Problem:** Basic text logging, difficult to parse programmatically
**Benefit:** Better log aggregation, analysis, monitoring
**Solution:**
- Add `structlog` or `python-json-logger`
- Configure JSON output for production
- **Files to modify:**
  - `pyproject.toml` - Add structured logging library
  - `main.py` - Configure structured logging

---

### 🔵 **LOW PRIORITY** - Nice to Have

#### 15. Create Docker Compose Setup
**Problem:** Docker Compose only documented in README, no actual file
**Benefit:** Easier local development and deployment
**Solution:**
- **New file:** `docker-compose.yml`
- **Services:**
  - `api` - Main FastAPI application
  - `nginx` (optional) - Reverse proxy for HTTPS
  - `prometheus` (optional) - Metrics collection
  - `grafana` (optional) - Metrics visualization

#### 16. Add Prometheus Metrics
**Problem:** No metrics collection for monitoring
**Benefit:** Track request counts, latency, errors
**Solution:**
- Add `prometheus-fastapi-instrumentator`
- Create `/metrics` endpoint
- **Files to modify:**
  - `pyproject.toml` - Add instrumentator dependency
  - `src/api.py` - Add metrics middleware

#### 17. Add Health Check Endpoint
**Problem:** Docker health check uses `/docs`, not ideal
**Benefit:** Proper health checks for Kubernetes/orchestration
**Solution:**
- **New endpoint:** `GET /health`
- **Checks:**
  - Account file exists and is readable
  - Token is valid or can be refreshed
  - Google API is reachable (optional)
- **Files to modify:**
  - `src/api.py` - Add `/health` endpoint
  - `Dockerfile` - Update HEALTHCHECK to use `/health`

#### 18. Add HTTPS Support
**Problem:** Server runs on HTTP only
**Benefit:** Encrypted data in transit
**Solution:**
- Add reverse proxy (Nginx or Traefik) in Docker Compose
- Configure Let's Encrypt certificates
- **New files:**
  - `nginx.conf` - Nginx reverse proxy configuration
  - Update `docker-compose.yml` to include nginx service

#### 19. Add Error Tracking
**Problem:** No centralized error tracking
**Benefit:** Automatic exception reporting, faster bug detection
**Solution:**
- Integrate Sentry or similar service
- **Files to modify:**
  - `pyproject.toml` - Add sentry-sdk[fastapi]
  - `main.py` - Initialize Sentry
  - `src/config.py` - Add SENTRY_DSN environment variable

---

## Implementation Phases

### Phase 1 (Immediate - Week 1)
**Focus:** Security & Code Quality Basics
1. ✅ Add API authentication (#1)
2. ✅ Add rate limiting (#2)
3. ✅ Fix bare exception handler (#4)
4. ✅ Add code coverage tracking (#6)
5. ✅ Configure type checking (#7)
6. ✅ Add linting & formatting (#8)

**Estimated Effort:** 4-6 hours
**Files:** `src/api.py`, `src/cloudcode_client.py`, `src/config.py`, `pyproject.toml`, `.env.example`

### Phase 2 (Short-term - Week 2)
**Focus:** Automation & DevOps
1. ✅ Create CI/CD pipeline (#5)
2. ✅ Add dependency automation (#9)
3. ✅ Replace global cache (#3)
4. ✅ Extract magic numbers (#11)

**Estimated Effort:** 4-6 hours
**Files:** `.github/workflows/ci.yml`, `.github/dependabot.yml`, `src/cloudcode_client.py`, `src/constants.py`

### Phase 3 (Medium-term - Week 3-4)
**Focus:** Code Structure & Monitoring
1. ✅ Refactor to Pydantic models (#10)
2. ✅ Enhance logging (#12)
3. ✅ Improve error handling (#13)
4. ✅ Add health check endpoint (#17)
5. ✅ Create Docker Compose setup (#15)

**Estimated Effort:** 6-8 hours
**Files:** `src/models.py`, `src/api.py`, `src/cloudcode_client.py`, `main.py`, `docker-compose.yml`, `Dockerfile`

### Phase 4 (Long-term - Month 2+)
**Focus:** Production Readiness
1. ✅ Add structured logging (#14)
2. ✅ Add Prometheus metrics (#16)
3. ✅ Add HTTPS support (#18)
4. ✅ Add error tracking (#19)

**Estimated Effort:** 8-10 hours
**Files:** `main.py`, `src/api.py`, `docker-compose.yml`, `nginx.conf`

---

## Critical Files Reference

**Core Application:**
- `src/api.py` (294 lines) - FastAPI endpoints, will need the most changes
- `src/cloudcode_client.py` (176 lines) - OAuth and Google API client
- `src/config.py` (42 lines) - Configuration management
- `main.py` - Application entry point

**Testing:**
- `test/test_api.py` (465 lines) - API tests
- `test/test_cloudcode_client.py` (142 lines) - Client tests

**Configuration:**
- `pyproject.toml` - Dependencies and tool configuration
- `.env.example` - Environment template
- `Dockerfile` - Container build

**Documentation:**
- `README.md` (209 lines) - User documentation
- `API.md` (414 lines) - API reference

---

## Metrics for Success

**Code Quality:**
- ✅ Test coverage ≥ 80%
- ✅ All type checks passing (mypy strict mode)
- ✅ Zero linting errors (ruff)
- ✅ All security scans passing (safety/trivy)

**Security:**
- ✅ API authentication implemented
- ✅ Rate limiting active
- ✅ No bare exception handlers
- ✅ HTTPS configured (production)

**Automation:**
- ✅ CI pipeline running on all PRs
- ✅ Automated dependency updates enabled
- ✅ Automated security scanning

**Monitoring:**
- ✅ Structured logging implemented
- ✅ Metrics endpoint available
- ✅ Health check endpoint functional
- ✅ Error tracking integrated

---

## Notes

- **Current strengths to preserve:**
  - Excellent documentation (README.md, API.md)
  - Comprehensive test suite
  - Clean Docker setup
  - Minimal dependencies

- **Architecture decisions:**
  - Keep lightweight design (don't over-engineer)
  - Maintain single-service architecture (no microservices needed)
  - Preserve fast startup and low resource usage

- **Backward compatibility:**
  - API endpoints should remain unchanged
  - Environment variables can be extended but existing ones should work
  - Docker image should maintain same ports and volume mounts
