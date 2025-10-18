# Feature Spec: Phase 1 Foundation

**Feature ID:** 001-phase-1-foundation  
**Status:** Planning  
**Created:** 2025-10-17  
**Target Deployment:** Raspberry Pi 5, 8GB RAM, Offline-First

## Overview

Establish foundational testing, monitoring, and security infrastructure for the RealtimeVoiceChat system. This phase focuses on creating a robust base for future development while optimizing for Raspberry Pi 5 constraints.

## Goals

1. **Testing Infrastructure**: Achieve 60% code coverage with unit and integration tests
2. **Health & Monitoring**: Implement edge-optimized health checks and resource metrics for Pi 5
3. **Security Baseline**: Add input validation and optional authentication for internet-exposed deployments

## Scope

### In Scope

#### 1.1 Testing Infrastructure

- pytest setup with coverage reporting
- Unit tests for core components:
  - `TurnDetection` class (pause calculation logic)
  - `TextSimilarity` and `TextContext` helpers
  - `AudioProcessor` audio processing functions
  - `TranscriptionCallbacks` state management
- Integration tests:
  - **Full STT → LLM → TTS pipeline** (end-to-end latency validation, target: <1.8s)
  - **User interruption handling** (mid-generation cancellation, cleanup verification)
- Target: 60% code coverage minimum

#### 1.2 Health Checks & Monitoring

- `/health` endpoint checking:
  - Audio processor status
  - LLM backend connectivity (llama.cpp/Ollama)
  - TTS engine availability (Piper)
  - System resources (CPU/RAM/swap)
- `/metrics` endpoint with resource metrics:
  - `system_memory_available_bytes` (gauge)
  - `system_cpu_temperature_celsius` (gauge) - Critical for Pi 5 throttling detection
  - `system_cpu_percent` (gauge)
  - `system_swap_usage_bytes` (gauge)
- Basic structured logging (JSON format)
- Component status tracking

#### 1.3 Security Basics

**For All Deployments:**

- Input validation for JSON messages (prevent malformed data crashes)
- Sanitize user text input (prevent injection attacks on LLM)
- Error message sanitization (don't leak system paths)

**For Internet-Exposed Deployments (Optional):**

- API key authentication for WebSocket
- Rate limiting (per IP/user):
  - 5 concurrent connections per IP
  - 100 messages per minute per connection
- Secrets manager for API keys

### Out of Scope

- WebSocket connection lifecycle and reconnection tests (deferred to Phase 4)
- Advanced metrics (latency histograms, request tracing) - minimizing overhead for Pi 5
- Circuit breakers and advanced error recovery (deferred to Phase 2)
- Full Prometheus/Grafana stack (using lightweight metrics only)

## Technical Approach

### Architecture Decisions

1. **Testing Strategy**: Focus on core conversational UX (pipeline + interruption) rather than exhaustive connection testing
2. **Monitoring**: Edge-optimized metrics are preferred over comprehensive monitoring to minimize resource consumption and avoid performance degradation on Raspberry Pi 5. Monitoring the Pi 5 CPU temperature is critical. The warning threshold is set at 75°C, and the throttling threshold is set at 80°C to prevent hardware slowdowns.
3. **Security**: Deployment-dependent approach (minimal for personal/offline, robust for internet-exposed)
4. **Logging**: Structured JSON logging for easier parsing and log aggregation on constrained devices, reducing parsing overhead and supporting lightweight monitoring solutions.

### File Structure

```
tests/
  unit/
    test_turn_detection.py           # Turn detection logic tests
    test_audio_processing.py         # Audio processor tests
    test_text_utils.py               # Text similarity/context tests
    test_callbacks.py                # Callback state management tests
  integration/
    test_pipeline_e2e.py             # Full pipeline test (~1-2 min)
    test_interruption_handling.py   # User interrupt test (~30s-1 min)
  conftest.py                        # Pytest fixtures

code/
  health_checks.py                   # Health check implementations
  metrics.py                         # Lightweight resource metrics
  monitoring/
    pi5_monitor.py                   # Pi 5 specific resource monitoring
  middleware/
    logging.py                       # Structured logging middleware
  security/
    validators.py                    # Input validation (required)
    auth.py                          # Authentication (optional)
    rate_limiter.py                  # Rate limiting (optional)
    secrets.py                       # Secrets manager (optional)
```

## Success Criteria

### Functional Requirements

- [ ] All unit tests pass with ≥60% code coverage
- [ ] Integration tests validate full pipeline latency <1.8s on Pi 5
- [ ] Integration tests verify clean interruption handling (no zombie processes)
- [ ] `/health` endpoint returns component status (200 if healthy, 503 if degraded)
- [ ] `/metrics` endpoint exposes resource metrics in plain text format
- [ ] Input validation prevents malformed JSON from crashing server
- [ ] Structured logs output valid JSON for all log levels

### Non-Functional Requirements

- [ ] Monitoring overhead: <2% CPU, <50MB RAM on Pi 5
- [ ] Test suite execution time: <5 minutes total
- [ ] Zero additional dependencies for personal/offline deployments
- [ ] Security middleware adds <10ms latency per request

## Dependencies

### Technical Dependencies

- `pytest` (≥7.0.0)
- `pytest-cov` (coverage reporting)
- `pytest-asyncio` (async test support)
- `psutil` (system resource monitoring)
- FastAPI's `TestClient` (HTTP/WebSocket testing)

### External Dependencies

- None for personal/offline deployment
- Secrets manager (e.g., HashiCorp Vault, AWS Secrets Manager) for internet-exposed deployments

### Constitution Alignment

- **Offline-First** ✓ No network dependencies for core monitoring
- **Reliability** ✓ Retry logic foundation (implemented in Phase 2)
- **Observability** ✓ Edge-optimized health/metrics for Pi 5
- **Security** ✓ Deployment-dependent (minimal → robust)
- **Maintainability** ✓ Clear file organization (<300 lines per file)
- **Testability** ✓ 60% coverage target achieved

## Risks & Mitigations

| Risk                               | Impact | Mitigation                                   |
| ---------------------------------- | ------ | -------------------------------------------- |
| psutil overhead on Pi 5            | Medium | Limit metrics polling to 1Hz, cache readings |
| Test flakiness on slow hardware    | Medium | Increase timeout thresholds for Pi 5 tests   |
| Security overhead for personal use | Low    | Make auth/rate-limiting optional via config  |
| JSON logging disk I/O              | Low    | Buffer logs in memory, batch writes          |

## Timeline Estimate

- **Testing Infrastructure**: 3-4 days
- **Health & Monitoring**: 2-3 days
- **Security Basics**: 2-3 days
- **Integration & Documentation**: 1-2 days
- **Total**: 8-12 days (Week 1-2)

## Open Questions

_To be resolved during Phase 0 (Research) and Phase 1 (Design)_

1. Should we use pytest-benchmark for latency validation, or custom timing code?
2. What format for `/metrics` endpoint? (Plain text, JSON, or both?)
3. Should health checks run synchronously or asynchronously?
4. How to handle CPU temperature monitoring on non-Pi platforms (macOS, Windows)?

---

**Next Steps:**

1. Execute Phase 0 (Research) workflow
2. Generate research.md with decisions on open questions
3. Execute Phase 1 (Design) workflow
4. Generate data-model.md, contracts/, quickstart.md
