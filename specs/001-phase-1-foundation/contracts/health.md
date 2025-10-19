# API Contract: Health Check Endpoint

**Endpoint:** `GET /health`  
**Version:** 1.0.0  
**Feature:** 001-phase-1-foundation

## Overview

Returns the health status of all system components. Used for:

- Load balancer health checks (if deployed behind load balancer)
- Monitoring systems (Prometheus, Nagios, etc.)
- Manual system verification

## Request

### HTTP Method

```
GET /health
```

### Headers

None required.

### Query Parameters

None.

### Request Body

None (GET request).

---

## Response

### Success Response (200 OK)

All components are healthy.

**Headers:**

```
Content-Type: application/json
Cache-Control: max-age=30
```

**Body:**

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

**Schema:**

```json
{
  "type": "object",
  "required": ["status", "components", "timestamp"],
  "properties": {
    "status": {
      "type": "string",
      "enum": ["healthy"]
    },
    "components": {
      "type": "object",
      "required": ["audio", "llm", "tts", "system"],
      "properties": {
        "audio": { "type": "boolean" },
        "llm": { "type": "boolean" },
        "tts": { "type": "boolean" },
        "system": { "type": "boolean" }
      }
    },
    "timestamp": {
      "type": "string",
      "format": "date-time"
    }
  }
}
```

---

### Degraded Response (503 Service Unavailable)

Some non-critical components are unhealthy, but system can still operate.

**Headers:**

```
Content-Type: application/json
Cache-Control: no-cache
```

**Body:**

```json
{
  "status": "degraded",
  "components": {
    "audio": true,
    "llm": true,
    "tts": false,
    "system": true
  },
  "timestamp": "2025-10-17T14:32:01.150Z",
  "details": {
    "tts": "Piper engine not loaded"
  }
}
```

**Degradation Rules:**

- `tts = false`: System can still transcribe and generate text responses (no audio output)
- `system = false`: High CPU/RAM/temp, but still functional

**Optional Details Field:**

- **Type**: Object (key = component name, value = diagnostic string)
- **Max Length**: 500 characters per component
- **When Included**: Only when component is unhealthy or degraded
- **Purpose**: Provide actionable diagnostic info for operators

---

### Unhealthy Response (503 Service Unavailable)

Critical components are down, system cannot operate.

**Headers:**

```
Content-Type: application/json
Cache-Control: no-cache
```

**Body:**

```json
{
  "status": "unhealthy",
  "components": {
    "audio": false,
    "llm": false,
    "tts": false,
    "system": true
  },
  "timestamp": "2025-10-17T14:32:01.150Z"
}
```

**Critical Components:**

- `audio`: Cannot accept user input
- `llm`: Cannot generate responses

---

### Error Response (500 Internal Server Error)

Health check itself failed (rare).

**Headers:**

```
Content-Type: application/json
Cache-Control: no-cache
```

**Body:**

```json
{
  "status": "error",
  "error": "Health check timed out after 10s",
  "timestamp": "2025-10-17T14:32:01.150Z"
}
```

---

## Component Health Check Logic

### Audio Processor

✅ **Healthy if:**

- Audio processor instance exists
- No recent crashes in logs (last 60s)

❌ **Unhealthy if:**

- Audio processor is None
- Recent crash detected

### LLM Backend

✅ **Healthy if:**

- LLM client can connect to backend (Ollama/llama.cpp)
- Test prompt completes within 5s

❌ **Unhealthy if:**

- Connection refused
- Timeout after 5s

### TTS Engine

✅ **Healthy if:**

- TTS engine (Piper) is loaded
- Can synthesize test phrase within 3s

❌ **Unhealthy if:**

- Engine not loaded
- Synthesis fails or times out

### System Resources

✅ **Healthy if:**

- Available RAM > 1GB
- CPU temp < 75°C (optimal) OR 75-79°C (approaching throttle, log WARNING)
- CPU usage < 95%
- Swap usage < 2GB

❌ **Unhealthy if:**

- Available RAM < 500MB (critical)
- CPU temp ≥ 80°C (throttling active)
- CPU usage ≥ 95% (sustained)
- Swap usage ≥ 4GB (thrashing)

**Note:** Temperature range 75-79°C is considered healthy with warning to alert operators before throttling begins at 80°C.

---

## Performance Requirements

- **Latency Target**: < 500ms (p99)
- **Timeout**: 10s total (5s per component check)
- **Caching**: Results cached for 30s to avoid overhead
- **Concurrent Execution**: All checks run in parallel

---

## Examples

### Example 1: Healthy System

```bash
$ curl http://localhost:8000/health

HTTP/1.1 200 OK
Content-Type: application/json

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

### Example 2: TTS Degraded (Piper not loaded)

```bash
$ curl http://localhost:8000/health

HTTP/1.1 503 Service Unavailable
Content-Type: application/json

{
  "status": "degraded",
  "components": {
    "audio": true,
    "llm": true,
    "tts": false,
    "system": true
  },
  "timestamp": "2025-10-17T14:32:05.230Z"
}
```

### Example 3: Critical Failure (LLM unreachable)

```bash
$ curl http://localhost:8000/health

HTTP/1.1 503 Service Unavailable
Content-Type: application/json

{
  "status": "unhealthy",
  "components": {
    "audio": true,
    "llm": false,
    "tts": true,
    "system": true
  },
  "timestamp": "2025-10-17T14:35:12.450Z"
}
```

---

## Security Considerations

- **No Authentication Required**: Health checks must be accessible to monitoring systems
- **No Sensitive Data**: Response contains no user data, API keys, or system paths
- **Rate Limiting**: Not applied to health checks (monitoring systems need reliable access)
- **DDoS Protection**: 30s cache prevents health check abuse from overwhelming system

---

## Testing

### Unit Tests

```python
async def test_health_check_all_healthy():
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert all(data["components"].values())

async def test_health_check_tts_degraded():
    # Mock TTS engine as unavailable
    with patch("code.health_checks.check_tts_engine", return_value=False):
        response = await client.get("/health")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "degraded"
        assert data["components"]["tts"] is False

async def test_health_check_llm_critical():
    # Mock LLM backend as unreachable
    with patch("code.health_checks.check_llm_backend", return_value=False):
        response = await client.get("/health")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["components"]["llm"] is False
```

### Integration Tests

```python
async def test_health_check_real_components():
    """Test health check against real running components."""
    response = await client.get("/health")
    assert response.status_code in [200, 503]
    data = response.json()
    assert "status" in data
    assert "components" in data
    assert "timestamp" in data
```

---

## Changelog

**v1.0.0** (2025-10-17)

- Initial health check endpoint specification
- Component checks: audio, llm, tts, system
- 200/503/500 status codes
- 30s caching, 10s timeout
