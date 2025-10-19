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
- Coverage Targets:
  - **Personal/Offline Deployment**: 60% code coverage minimum (Phase 1-2)
  - **Production/Internet Deployment**: 80% code coverage target (Phase 3+, per constitution)

#### 1.2 Health Checks & Monitoring

- `/health` endpoint checking:
  - Audio processor status
  - LLM backend connectivity (llama.cpp/Ollama)
  - TTS engine availability (Piper)
  - System resources (CPU/RAM/swap)
  - **Response Format**: JSON with `Content-Type: application/json` header
  - **Response Caching**: Results cached for 30s to minimize overhead
  - **Component Check Timeout**: 5s per component (all 4 checks run in parallel using asyncio.gather)
  - **Total Endpoint Timeout**: 10s (includes 5s parallel checks + overhead + error handling)
  - **Optional Details Field**: May include component-specific diagnostic info (max 500 chars per component)
- `/metrics` endpoint with resource metrics:
  - `system_memory_available_bytes` (gauge)
  - `system_cpu_temperature_celsius` (gauge) - Critical for Pi 5 throttling detection
    - **Pi 5 Platform**: Read from `/sys/class/thermal/thermal_zone0/temp` (primary) or `vcgencmd measure_temp` (fallback)
    - **Non-Pi Platforms**: Return `-1` to indicate unavailable
  - `system_cpu_percent` (gauge)
  - `system_swap_usage_bytes` (gauge)
  - **Response Format**: Prometheus plain text format with `Content-Type: text/plain; version=0.0.4` header
  - **Polling Frequency**: 1Hz internal updates (metrics updated every second)
  - **Latency Target**: <50ms response time (p99)
- Basic structured logging (JSON format)
  - **Log Fields**:
    - Required: `timestamp` (ISO 8601), `level`, `logger`, `message`
    - Optional: `component`, `session_id`, additional context in `context` object
  - **Log Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
  - **Example Format**:
    ```json
    {
      "timestamp": "2025-10-18T14:32:01.123Z",
      "level": "INFO",
      "logger": "realtimevoicechat.server",
      "message": "WebSocket connection established",
      "context": {
        "session_id": "abc123",
        "component": "websocket_handler",
        "remote_addr": "127.0.0.1:54321"
      }
    }
    ```
- Component status tracking

#### 1.3 Security Basics

**For All Deployments:**

- Input validation for JSON messages (prevent malformed data crashes)
  - **Message Size Limit**: 1MB maximum (1,048,576 bytes) measured on raw message to prevent memory exhaustion
  - **Text Length Limit**: 5,000 characters maximum, applied **after** Unicode normalization (NFC) and **before** sanitization
  - **Justification**: Balances user experience (long messages) with DoS protection on Pi 5 (8GB RAM)
- Sanitize user text input (prevent injection attacks on LLM)

3. **Prompt Injection Prevention (Phase 1: Detection Only):**

   - **Detect and log** patterns like:
     - `"ignore previous instructions"` (case-insensitive)
     - `"disregard all prior context"` (case-insensitive)
     - `"you are now a [different persona]"` (pattern matching)
     - `"system:"` or `"assistant:"` (role spoofing attempts)
   - **Action**: Log WARNING with request context (timestamp, message preview), allow message through
   - **Rationale**: Personal/offline deployment has no threat model requiring blocking
   - **Phase 3**: Add configurable stripping/rejection for internet-exposed deployments

   - **Special Token Escaping**: Strip model-specific tokens:
     - `<|endoftext|>`, `<|im_start|>`, `<|im_end|>` (OpenAI format)
     - `###`, `</s>`, `[INST]`, `[/INST]` (common LLM delimiters)
   - **Character Filtering**: Allow Unicode letters, digits, whitespace, punctuation; block control characters except `\n` and `\t`

- Error message sanitization (don't leak system paths)
  - **Never expose**: File paths, environment variables, API keys, internal IPs
  - **Generic errors**: Replace specific exceptions with user-friendly messages
  - **Error Response Format**: Consistent JSON structure for both WebSocket and HTTP:
    ```json
    {
      "type": "error",
      "data": {
        "code": "ERROR_CODE",
        "message": "User-friendly description",
        "field": "data.field_name"
      }
    }
    ```

**For Internet-Exposed Deployments:**

_Note: Advanced security features (API key authentication, rate limiting, secrets management) are **intentionally deferred to Phase 3: Security Hardening** per constitution Principle 3 (Security is deployment-dependent). Phase 1 targets personal/offline deployment where these features are not required. This is a documented architectural decision, not an oversight._

### Out of Scope

- WebSocket connection lifecycle and reconnection tests (deferred to Phase 4)
- Advanced metrics (latency histograms, request tracing) - minimizing overhead for Pi 5
- Circuit breakers and advanced error recovery (deferred to Phase 2)
- Full Prometheus/Grafana stack (using lightweight metrics only)
- **API key authentication** (deferred to Phase 3: Security Hardening)
- **Rate limiting** (deferred to Phase 3: Security Hardening)
- **Secrets manager integration** (deferred to Phase 3: Security Hardening)

---

## Edge Cases & Error Handling

### Boundary Conditions

1. **Message Size Boundaries**
   - Exactly 1MB message: REJECT with `MESSAGE_TOO_LARGE` error
   - Exactly 5,000 characters: ACCEPT (boundary is inclusive)
2. **Temperature Boundaries**

   - Below 75°C: Status = "healthy", no warning (optimal operating range)
   - 75-79°C: Status = "healthy", log WARNING (approaching throttle threshold)
   - Exactly 80°C or above: Status = "unhealthy", log CRITICAL (CPU throttling active)
   - Above 85°C: Status = "unhealthy", consider emergency shutdown (log CRITICAL, notify operator)
   
   **Phase 1 Behavior:** Passive monitoring only (log warnings, update health status)
   
   **Phase 2 Enhancement (Planned):** Automatic workload reduction
   - At 75°C: Log WARNING, continue normal operation
   - At 80°C: System status = "unhealthy", log CRITICAL, continue operation
   - At 85°C: Reduce LLM workload (lower temperature parameter) or pause TTS processing

3. **Memory Boundaries**

   - Exactly 1GB available: Status = "degraded", log WARNING
   - Exactly 500MB available: Status = "unhealthy", log CRITICAL
   - Below 100MB available: High risk of OOM, emergency measures

4. **Swap Usage Boundaries**

   - Below 2GB swap: Status = "healthy", normal operation
   - Exactly 2GB swap: Status = "degraded", log WARNING (memory pressure)
   - Exactly 4GB swap: Status = "unhealthy", log CRITICAL (thrashing likely)
   - Above 6GB swap: System severely constrained, performance degraded

5. **Component Timeouts**
   - Component check at exactly 5s: TIMEOUT, mark component as unhealthy
   - Health endpoint at exactly 10s: Return 500 Internal Server Error

### Platform-Specific Behavior

1. **CPU Temperature on Non-Pi Platforms**

   - **Unsupported platforms** (macOS/Windows/Linux non-Pi): Return `-1` for `system_cpu_temperature_celsius`
   - **Special value `-1`**: Indicates "temperature monitoring unavailable" (not an error)
   - **Detection method**: Check for `/sys/class/thermal/thermal_zone0/temp` or `vcgencmd` availability
   - **Behavior**: Fallback gracefully, no errors logged, monitoring systems should handle `-1` as valid value
   - **Metrics output**: Include `-1` in Prometheus format (parseable by standard tools)

2. **Permission Issues**
   - If `/sys/class/thermal/` is not readable: Return `-1` (no error)
   - If `vcgencmd` requires root and not available: Return `-1` (no error)

### Concurrent Request Handling

1. **Health Check Caching**

   - Multiple concurrent `/health` requests within 30s window: Return cached result
   - First request triggers actual checks, subsequent requests get cached response
   - Cache invalidation: 30s expiry or manual invalidation on config change

2. **Metrics Polling Under Load**
   - If metrics request arrives during high CPU load (>95%): Still respond within 50ms using cached values
   - Metrics update loop runs at 1Hz regardless of request frequency

### Data Edge Cases

1. **Empty or Null Values**

   - Empty log message: Use default message `"No message provided"`
   - Null component status: Treat as unhealthy (fail-safe)

2. **Metric Value Anomalies**

   - CPU usage > 100%: Cap at 100% (psutil may report >100% on multi-core)
   - Negative memory values: Log error, return 0 (fail-safe)

3. **Malformed Structured Logs**

   - If JSON serialization fails: Fall back to plain text log
   - If timestamp is invalid: Use current system time

4. **Unicode and Special Characters**
   - Emoji in text input: Preserve (Unicode is allowed)
   - Null bytes (`\x00`): Strip (security risk)
   - Invalid UTF-8 sequences: Replace with Unicode replacement character `�`
   - **Testing Required (Phase 1)**: Validate emoji preservation, null byte stripping, and invalid UTF-8 handling in security validator tests

### Error Recovery

1. **Component Check Failures**

   - If health check crashes: Return 500 error, log stack trace
   - If single component check times out: Mark that component unhealthy, continue checking others

2. **Metrics Collection Failures**

   - If psutil call fails: Return last known value, log WARNING
   - If all metrics fail: Return 500 error

3. **Validation Errors**
   - Multiple validation errors in one message: Return all errors in array
   - Critical validation failure (e.g., cannot parse JSON): Disconnect WebSocket with close code 1003

---

## Technical Approach

### Architecture Decisions

1. **Testing Strategy**: Focus on core conversational UX (pipeline + interruption) rather than exhaustive connection testing
2. **Monitoring**: Edge-optimized metrics are preferred over comprehensive monitoring to minimize resource consumption and avoid performance degradation on Raspberry Pi 5. Monitoring the Pi 5 CPU temperature is critical. The warning threshold is set at 75°C, and the throttling threshold is set at 80°C to prevent hardware slowdowns.
3. **Security**: Deployment-dependent approach (minimal for personal/offline, robust for internet-exposed)
4. **Logging**: Structured JSON logging for easier parsing and log aggregation on constrained devices, reducing parsing overhead and supporting lightweight monitoring solutions.

### Performance Targets

1. **Health Check Endpoint**

   - **Target Latency**: <500ms (p95) when all components healthy
   - **Maximum Latency**: 10s (hard timeout for entire endpoint)
   - **Component Check Strategy**: All 4 checks run in parallel using `asyncio.gather()` with 5s timeout per component
   - **Calculation**: 4 components checked in parallel = max 5s (slowest component) + ~0.5s overhead ≈ 5.5s worst case
   - **Note**: 500ms target achievable when components respond quickly (<100ms each)
   - **Implementation**: Use `asyncio.wait_for()` with timeout on the gather call

2. **Metrics Endpoint**

   - **Target Latency**: <50ms (p99)
   - **Strategy**: Return cached values updated at 1Hz

3. **Validation**
   - **Target Latency**: <10ms per message
   - **Strategy**: Lightweight regex and size checks only

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
    validators.py                    # Input validation (required for all deployments)
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

- **Personal/Offline Deployment**: No external service dependencies (Python library dependencies are acceptable)
- **Internet-Exposed Deployment** (Phase 3): Secrets manager integration (e.g., HashiCorp Vault, AWS Secrets Manager) optional

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
