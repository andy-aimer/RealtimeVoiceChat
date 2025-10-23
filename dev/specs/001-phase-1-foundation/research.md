# Research Document: Phase 1 Foundation

**Feature:** 001-phase-1-foundation  
**Date:** 2025-10-17  
**Author:** AI Assistant

## Open Questions & Decisions

### Q1: Latency Validation Approach

**Question:** Should we use pytest-benchmark for latency validation, or custom timing code?

**Decision:** Use custom timing code with `time.perf_counter()`

**Rationale:**

- **Simplicity**: pytest-benchmark adds complexity and statistical analysis overhead unnecessary for single-user Pi 5 deployment
- **Control**: Custom timing gives direct control over warmup runs, timeout handling, and failure conditions
- **Pi 5 Constraints**: Benchmark frameworks consume extra RAM/CPU for statistical calculations
- **Clear Pass/Fail**: Integration tests need binary pass/fail based on latency thresholds (< 1.8s), not statistical distributions

**Implementation:**

```python
from time import perf_counter

async def test_full_pipeline_latency():
    # Warmup run (models loaded)
    await run_pipeline_once()

    # Custom timing is used instead of pytest-benchmark for simplicity and direct control.
    # This avoids extra dependencies and statistical overhead, and provides a clear pass/fail.
    # See rationale above for details.

    # Actual test
    start = perf_counter()
    result = await run_full_pipeline(audio_input)
    elapsed = perf_counter() - start

    assert elapsed < 1.8, f"Pipeline took {elapsed:.2f}s (threshold: 1.8s)"
    assert result.transcription is not None
    assert result.llm_response is not None
    assert result.audio_output is not None
```

**Alternatives Considered:**

- pytest-benchmark: Rejected due to overhead and complexity
- Manual stopwatch testing: Rejected as non-automated, unreliable

---

### Q2: Metrics Endpoint Format

**Question:** What format for `/metrics` endpoint? (Plain text, JSON, or both?)

**Decision:** Plain text format (Prometheus-compatible)

**Rationale:**

- **Industry Standard**: Prometheus plain text format is widely supported by monitoring tools (Prometheus, Grafana, VictoriaMetrics)
- **Human Readable**: Easy to curl and inspect manually
- **Minimal Overhead**: Simple string formatting, no JSON serialization overhead
- **Future Compatibility**: Can integrate with Prometheus if scaling beyond Pi 5 in Phase 4

**Implementation:**

```python
@app.get("/metrics")
async def metrics():
    return Response(
        content=f"""# HELP system_memory_available_bytes Available system memory
# TYPE system_memory_available_bytes gauge
system_memory_available_bytes {psutil.virtual_memory().available}

# HELP system_cpu_temperature_celsius CPU temperature
# TYPE system_cpu_temperature_celsius gauge
system_cpu_temperature_celsius {get_cpu_temperature()}

# HELP system_cpu_percent CPU usage percentage
# TYPE system_cpu_percent gauge
system_cpu_percent {psutil.cpu_percent(interval=0.1)}

# HELP system_swap_usage_bytes Swap memory usage
# TYPE system_swap_usage_bytes gauge
system_swap_usage_bytes {psutil.swap_memory().used}
""",
        media_type="text/plain"
    )
```

**Alternatives Considered:**

- JSON format: Rejected (requires parsing, not Prometheus-compatible)
- Both formats: Rejected (unnecessary complexity for single-user deployment)

---

### Q3: Health Check Execution Model

**Question:** Should health checks run synchronously or asynchronously?

**Decision:** Asynchronous with timeout protection

**Rationale:**

- **FastAPI Best Practice**: FastAPI is async-first; blocking health checks can bottleneck event loop
- **Responsiveness**: Health checks should not block user interactions on WebSocket
- **Component Independence**: Each component check (STT/LLM/TTS) can run concurrently
- **Timeout Safety**: Use `asyncio.wait_for()` to prevent hung checks from blocking endpoint

**Implementation:**

```python
@app.get("/health")
async def health_check():
    try:
        # Run checks concurrently with 5s timeout
        results = await asyncio.gather(
            asyncio.wait_for(check_audio_processor(), timeout=5.0),
            asyncio.wait_for(check_llm_backend(), timeout=5.0),
            asyncio.wait_for(check_tts_engine(), timeout=5.0),
            asyncio.wait_for(check_system_resources(), timeout=2.0),
            return_exceptions=True
        )

        # Aggregate results
        healthy = all(r is True for r in results if not isinstance(r, Exception))
        status_code = 200 if healthy else 503

        return JSONResponse(
            status_code=status_code,
            content={
                "status": "healthy" if healthy else "degraded",
                "components": {
                    "audio": bool(results[0]),
                    "llm": bool(results[1]),
                    "tts": bool(results[2]),
                    "system": bool(results[3])
                }
            }
        )
    except Exception as e:
        return JSONResponse(status_code=503, content={"status": "unhealthy", "error": str(e)})
```

**Alternatives Considered:**

- Synchronous checks: Rejected (blocks event loop, poor FastAPI practice)
- Sequential async checks: Rejected (slower than concurrent, no benefit)

---

### Q4: Cross-Platform CPU Temperature Monitoring

**Question:** How to handle CPU temperature monitoring on non-Pi platforms (macOS, Windows)?

**Decision:** Platform-specific implementation with graceful fallback

**Rationale:**

- **Pi 5 Priority**: Temperature monitoring is critical for Pi 5 throttling detection (target <75°C, max 80°C)
- **Development Flexibility**: Developers on macOS/Windows should not experience errors
- **Graceful Degradation**: Return `-1` or `null` on unsupported platforms, log warning once

**Implementation:**

```python
import platform
import subprocess
import logging

logger = logging.getLogger(__name__)
_temp_warning_logged = False

def get_cpu_temperature() -> float:
    """Get CPU temperature in Celsius. Returns -1 if unavailable."""
    global _temp_warning_logged

    system = platform.system()

    if system == "Linux":
        # Raspberry Pi (vcgencmd)
        try:
            result = subprocess.run(
                ["vcgencmd", "measure_temp"],
                capture_output=True,
                text=True,
                timeout=1.0
            )
            if result.returncode == 0:
                # Output: "temp=42.0'C"
                temp_str = result.stdout.strip().split("=")[1].split("'")[0]
                return float(temp_str)
        except (FileNotFoundError, subprocess.TimeoutExpired, IndexError, ValueError):
            pass

        # Fallback: Try thermal_zone files
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                return float(f.read().strip()) / 1000.0
        except (FileNotFoundError, PermissionError, ValueError):
            pass

    elif system == "Darwin":  # macOS
        try:
            result = subprocess.run(
                ["osx-cpu-temp"],
                capture_output=True,
                text=True,
                timeout=1.0
            )
            if result.returncode == 0:
                # Output: "42.0°C"
                return float(result.stdout.strip().replace("°C", ""))
        except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
            pass

    # Unsupported platform or command failed
    if not _temp_warning_logged:
        logger.warning(f"CPU temperature monitoring not supported on {system}")
        _temp_warning_logged = True

    return -1.0
```

**Alternatives Considered:**

- Fail hard on unsupported platforms: Rejected (breaks dev experience)
- Use third-party libraries (e.g., `py-cpuinfo`): Rejected (adds dependency, limited Pi support)
- Skip temperature metric entirely: Rejected (critical for Pi 5 production use)

---

## Additional Research Findings

### Testing Dependencies

**Chosen Stack:**

- `pytest==7.4.3` (stable, mature async support)
- `pytest-cov==4.1.0` (coverage reporting)
- `pytest-asyncio==0.21.1` (async test support)
- `httpx==0.25.0` (async HTTP client for FastAPI testing, replaces deprecated `starlette.testclient`)

**Justification:**

- FastAPI recommends `httpx` for async testing over `starlette.testclient`
- `pytest-asyncio` allows `async def test_...` functions for WebSocket/async testing
- No additional dependencies needed for personal/offline deployment

### Structured Logging Format

**Chosen Format:** JSON with custom fields

```json
{
  "timestamp": "2025-10-17T14:32:01.123Z",
  "level": "INFO",
  "logger": "realtimevoicechat.server",
  "message": "WebSocket connection established",
  "context": {
    "user_id": "anonymous",
    "session_id": "abc123",
    "component": "websocket_handler"
  }
}
```

**Justification:**

- Easy to parse with `jq` or log aggregation tools
- Structured context allows filtering by component/session
- Standard timestamp format (ISO 8601)
- Minimal overhead (Python's `json.dumps` is highly optimized)

### Security: Input Validation Rules

**JSON Message Validation:**

- Max message size: 1MB (prevent memory exhaustion)
- Required fields: `type` (string), `data` (object)
- Allowed message types: `audio`, `text`, `control`
- Text input: Max 5000 characters, sanitize special characters

**LLM Input Sanitization:**

- Strip prompt injection attempts (e.g., "Ignore previous instructions")
- Limit context history to last 10 messages (prevent context stuffing)
- Escape special tokens used by model (e.g., `<|endoftext|>`)

---

## Performance Estimates

### Monitoring Overhead (Pi 5)

| Metric Collection       | CPU Impact | RAM Impact | Frequency |
| ----------------------- | ---------- | ---------- | --------- |
| psutil.virtual_memory() | <0.1%      | 0 MB       | 1Hz       |
| psutil.cpu_percent()    | ~0.5%      | 0 MB       | 1Hz       |
| get_cpu_temperature()   | <0.1%      | 0 MB       | 1Hz       |
| psutil.swap_memory()    | <0.1%      | 0 MB       | 1Hz       |
| **Total**               | **<1%**    | **<10 MB** | **1Hz**   |

**Conclusion:** Monitoring overhead is well within target (<2% CPU, <50MB RAM).

### Test Suite Execution Time

| Test Category              | Estimated Time  | Count         |
| -------------------------- | --------------- | ------------- |
| Unit tests                 | 10-20s          | ~15 tests     |
| Integration (pipeline)     | 90-120s         | 1 test        |
| Integration (interruption) | 30-60s          | 1 test        |
| **Total**                  | **2.5-3.5 min** | **~17 tests** |

**Conclusion:** Well within 5-minute target.

---

## Recommendations

1. **Implement monitoring first** - Health/metrics endpoints are quick wins, provide immediate value for Pi 5 testing
2. **Use fixtures liberally** - Create pytest fixtures for mock STT/LLM/TTS to speed up unit tests
3. **Test on Pi 5 hardware** - Latency thresholds may need adjustment based on actual Pi 5 performance
4. **Document security config** - Clearly document which security features are optional vs required
5. **Add monitoring dashboard** - Consider simple HTML dashboard for `/metrics` visualization (Phase 4)

---

**Status:** Research complete, ready for Phase 1 (Design)
