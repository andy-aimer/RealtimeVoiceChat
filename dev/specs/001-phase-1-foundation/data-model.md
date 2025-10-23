# Data Model: Phase 1 Foundation

**Feature:** 001-phase-1-foundation  
**Version:** 1.0.0  
**Date:** 2025-10-17

## Entities

### 1. HealthCheckResult

Represents the health status of a system component.

**Fields:**

- `component_name` (string, required): Name of the component being checked (e.g., "audio", "llm", "tts", "system")
- `is_healthy` (boolean, required): Whether the component is functioning correctly
- `details` (string, optional): Human-readable details about the health status
- `latency_ms` (float, optional): Time taken to perform the health check in milliseconds
- `timestamp` (datetime, required): When the health check was performed (ISO 8601 format)

**Relationships:**

- Part of `HealthCheckResponse` (composition)

**Constraints:**

- `component_name` must be one of: `["audio", "llm", "tts", "system"]`
- `latency_ms` must be ≥ 0
- `timestamp` must be valid ISO 8601 datetime

**Example:**

```json
{
  "component_name": "llm",
  "is_healthy": true,
  "details": "Connected to Ollama (model: tinyllama:1.1b-chat-q4)",
  "latency_ms": 45.3,
  "timestamp": "2025-10-17T14:32:01.123Z"
}
```

---

### 2. HealthCheckResponse

Aggregate health status response for the `/health` endpoint.

**Fields:**

- `status` (string, required): Overall system health status
- `components` (dict[string, boolean], required): Map of component names to health status
- `details` (list[HealthCheckResult], optional): Detailed health check results for each component
- `timestamp` (datetime, required): When the aggregate check was performed

**Constraints:**

- `status` must be one of: `["healthy", "degraded", "unhealthy"]`
- `status = "healthy"` if all components are healthy
- `status = "degraded"` if some components are unhealthy but system can operate
- `status = "unhealthy"` if critical components (llm, audio) are down
- `components` keys must match `["audio", "llm", "tts", "system"]`

**Example:**

```json
{
  "status": "healthy",
  "components": {
    "audio": true,
    "llm": true,
    "tts": true,
    "system": true
  },
  "timestamp": "2025-10-17T14:32:01.150Z"
}
```

---

### 3. SystemMetrics

System resource metrics for the `/metrics` endpoint (Prometheus format).

**Fields:**

- `system_memory_available_bytes` (int, gauge): Available system memory in bytes
- `system_cpu_temperature_celsius` (float, gauge): CPU temperature in Celsius (-1 if unavailable)
- `system_cpu_percent` (float, gauge): CPU usage percentage (0-100)
- `system_swap_usage_bytes` (int, gauge): Swap memory usage in bytes

**Constraints:**

- `system_memory_available_bytes` ≥ 0
- `system_cpu_temperature_celsius` ≥ -1 (special value for "unavailable")
- `system_cpu_percent` ∈ [0, 100]
- `system_swap_usage_bytes` ≥ 0

**Output Format:** Prometheus plain text

```
# HELP system_memory_available_bytes Available system memory
# TYPE system_memory_available_bytes gauge
system_memory_available_bytes 5368709120

# HELP system_cpu_temperature_celsius CPU temperature
# TYPE system_cpu_temperature_celsius gauge
system_cpu_temperature_celsius 62.5

# HELP system_cpu_percent CPU usage percentage
# TYPE system_cpu_percent gauge
system_cpu_percent 34.2

# HELP system_swap_usage_bytes Swap memory usage
# TYPE system_swap_usage_bytes gauge
system_swap_usage_bytes 0
```

---

### 4. TestResult

Represents the result of a test execution (unit or integration).

**Fields:**

- `test_name` (string, required): Name of the test function/class
- `status` (string, required): Test execution status
- `duration_ms` (float, required): Test execution time in milliseconds
- `error_message` (string, optional): Error message if test failed
- `metrics` (dict[string, float], optional): Test-specific metrics (e.g., `{"latency": 1650.5}`)

**Constraints:**

- `status` must be one of: `["passed", "failed", "skipped", "error"]`
- `duration_ms` ≥ 0

**Example:**

```python
{
  "test_name": "test_full_pipeline_latency",
  "status": "passed",
  "duration_ms": 1650.5,
  "metrics": {
    "pipeline_latency": 1650.5,
    "stt_latency": 220.3,
    "llm_latency": 980.1,
    "tts_latency": 450.1
  }
}
```

---

### 5. LogEntry

Structured log entry for JSON logging.

**Fields:**

- `timestamp` (datetime, required): Log entry timestamp (ISO 8601)
- `level` (string, required): Log level
- `logger` (string, required): Logger name (typically module path)
- `message` (string, required): Human-readable log message
- `context` (dict, optional): Additional structured context

**Constraints:**

- `level` must be one of: `["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]`
- `logger` should follow pattern: `realtimevoicechat.<module>`
- `message` max length: 1000 characters (truncate longer messages)

**Example:**

```json
{
  "timestamp": "2025-10-17T14:32:01.123Z",
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

---

### 6. ValidationError

Represents input validation errors.

**Fields:**

- `field` (string, required): Name of the invalid field
- `error_code` (string, required): Machine-readable error code
- `message` (string, required): Human-readable error message
- `received_value` (any, optional): The invalid value received (sanitized)

**Constraints:**

- `error_code` must follow pattern: `[A-Z_]+` (e.g., `INVALID_JSON`, `FIELD_TOO_LONG`)
- `message` max length: 500 characters

**Example:**

```json
{
  "field": "data.text",
  "error_code": "FIELD_TOO_LONG",
  "message": "Text input exceeds maximum length of 5000 characters",
  "received_value": "<truncated after 100 chars>"
}
```

---

## Relationships

```
HealthCheckResponse (1) ---> (N) HealthCheckResult
  - Aggregates results from multiple component checks

TestResult (1) ---> (N) TestResult
  - Test suites contain multiple test results
  - Integration tests may have nested test results

LogEntry (1) ---> (1) dict (context)
  - Each log entry has optional structured context
```

---

## State Transitions

### HealthCheckResult Status

```
Unknown → Checking → [Healthy | Unhealthy]
Healthy ⇄ Unhealthy (component can recover or fail)
```

### TestResult Status

```
Pending → Running → [Passed | Failed | Skipped | Error]
(Terminal states: Passed, Failed, Skipped, Error)
```

---

## Storage & Persistence

### In-Memory Storage

- **HealthCheckResult**: Cached for 30 seconds, refreshed on `/health` request
- **SystemMetrics**: Polled at 1Hz, served from cache on `/metrics` request
- **LogEntry**: Buffered in memory (max 1000 entries), flushed to disk every 10s or on shutdown

### No Persistent Storage

- Test results: Reported to pytest, not persisted
- Validation errors: Logged and returned in HTTP response, not persisted

---

## Indexes & Performance

### Health Checks

- **Caching Strategy**: Use `asyncio.Cache` (TTL: 30s) to avoid redundant checks
- **Timeout**: 5s per component check, 2s for system checks
- **Concurrent Execution**: All component checks run in parallel

### Metrics Collection

- **Polling Frequency**: 1Hz (every 1 second)
- **Caching**: Last values cached, no historical data
- **Optimization**: Use `psutil` with `interval=0` for non-blocking calls

---

## Validation Rules

### JSON Message Validation

```python
{
  "type": {
    "type": "string",
    "enum": ["audio", "text", "control"],
    "minLength": 1,
    "maxLength": 32
  },
  "data": {
    "type": "object",
    "maxSize": 1048576,  # 1MB max message size
    "additionalProperties": True
  },
  "additionalProperties": False
}
```

### Text Input Validation

```python
{
  "text": {
    "type": "string",
    "minLength": 1,
    "maxLength": 5000,  # 5000 characters max
    "sanitize": True,   # Strip special characters
    "pattern": "^[\\w\\s\\p{P}]+$"
  },
  "additionalProperties": False
}
```

---

## Migration Strategy

**Phase 1 → Phase 2:**

- When refactoring `server.py`, preserve health/metrics endpoints
- Move `HealthCheckResult` to `code/models/health.py`
- Move `SystemMetrics` to `code/models/metrics.py`

**Phase 3 (Scalability):**

- If moving to Redis/PostgreSQL, add persistence for:
  - Historical metrics (time-series data)
  - Aggregated health check logs
- Keep in-memory caching for low-latency access

---

## Constitution Alignment

✅ **Offline-First**: All data models operate without external dependencies  
✅ **Reliability**: Health checks have timeout protection, graceful degradation  
✅ **Observability**: Metrics follow Prometheus standard for tooling compatibility  
✅ **Security**: Validation rules prevent injection attacks, size limits prevent DoS  
✅ **Maintainability**: Clear entity boundaries, max 300 lines per model file  
✅ **Testability**: All entities have example data for unit testing

---

**Status:** Data model complete, ready for contract generation
