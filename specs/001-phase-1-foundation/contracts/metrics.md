# API Contract: Metrics Endpoint

**Endpoint:** `GET /metrics`  
**Version:** 1.0.0  
**Feature:** 001-phase-1-foundation

## Overview

Returns system resource metrics in Prometheus plain text format. Used for:

- Prometheus scraping
- Grafana dashboards
- Resource monitoring and alerting
- Pi 5 throttling detection

## Request

### HTTP Method

```
GET /metrics
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

**Headers:**

```
Content-Type: text/plain; version=0.0.4
```

**Body:**

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

## Metrics Specifications

### 1. system_memory_available_bytes

**Type:** Gauge  
**Unit:** Bytes  
**Description:** Available system memory (not including swap)

**Source:** `psutil.virtual_memory().available`  
**Range:** `[0, total_ram]`

**Alert Thresholds (Pi 5, 8GB RAM):**

- ⚠️ Warning: < 2GB (< 2147483648 bytes)
- 🚨 Critical: < 1GB (< 1073741824 bytes)

---

### 2. system_cpu_temperature_celsius

**Type:** Gauge  
**Unit:** Celsius  
**Description:** CPU core temperature (Pi 5 specific)

**Source (Raspberry Pi):**

The temperature is determined using the following fallback chain:

1. `vcgencmd measure_temp` (primary; requires root or video group permissions and may not be available in containerized environments)
2. `/sys/class/thermal/thermal_zone0/temp` (fallback if `vcgencmd` is unavailable or fails)
3. `-1` (if neither method is available, or on non-Pi platforms)

**Error Handling:**  
If all fallback methods fail, the metric value will be set to `-1` to indicate that the temperature is unavailable.

**Range:** `[-1, 100]` (special value -1 = "unavailable")

**Alert Thresholds (Pi 5):**

- ⚠️ Warning: ≥ 75°C (approaching throttle)
- 🚨 Critical: ≥ 80°C (CPU throttling active)

---

### 3. system_cpu_percent

**Type:** Gauge  
**Unit:** Percent  
**Description:** Current CPU usage (all cores averaged)

**Source:** `psutil.cpu_percent(interval=0.1)`  
**Range:** `[0, 100]`

**Alert Thresholds:**

- ⚠️ Warning: ≥ 80% (sustained over 5 minutes)
- 🚨 Critical: ≥ 95% (sustained over 1 minute)

---

### 4. system_swap_usage_bytes

**Type:** Gauge  
**Unit:** Bytes  
**Description:** Current swap memory usage

**Source:** `psutil.swap_memory().used`  
**Range:** `[0, total_swap]`

**Alert Thresholds (Pi 5, 8GB RAM):**

- ⚠️ Warning: ≥ 2GB (memory pressure)
- 🚨 Critical: ≥ 4GB (thrashing likely)

---

## Performance Requirements

- **Polling Frequency**: 1Hz (metrics updated every second)
- **Caching**: Last values cached, no historical data
- **Latency Target**: < 50ms (p99)
- **Overhead**: < 1% CPU, < 10MB RAM

---

## Examples

### Example 1: Healthy Pi 5 System

```bash
$ curl http://localhost:8000/metrics

HTTP/1.1 200 OK
Content-Type: text/plain; version=0.0.4

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

### Example 2: Pi 5 Under Load (High Temp, Swapping)

```bash
$ curl http://localhost:8000/metrics

HTTP/1.1 200 OK
Content-Type: text/plain; version=0.0.4

# HELP system_memory_available_bytes Available system memory
# TYPE system_memory_available_bytes gauge
system_memory_available_bytes 1073741824

# HELP system_cpu_temperature_celsius CPU temperature
# TYPE system_cpu_temperature_celsius gauge
system_cpu_temperature_celsius 78.3

# HELP system_cpu_percent CPU usage percentage
# TYPE system_cpu_percent gauge
system_cpu_percent 92.5

# HELP system_swap_usage_bytes Swap memory usage
# TYPE system_swap_usage_bytes gauge
system_swap_usage_bytes 2147483648
```

### Example 3: macOS Development Machine (No Temp)

```bash
$ curl http://localhost:8000/metrics

HTTP/1.1 200 OK
Content-Type: text/plain; version=0.0.4

# HELP system_memory_available_bytes Available system memory
# TYPE system_memory_available_bytes gauge
system_memory_available_bytes 8589934592

# HELP system_cpu_temperature_celsius CPU temperature
# TYPE system_cpu_temperature_celsius gauge
system_cpu_temperature_celsius -1

# HELP system_cpu_percent CPU usage percentage
# TYPE system_cpu_percent gauge
system_cpu_percent 15.8

# HELP system_swap_usage_bytes Swap memory usage
# TYPE system_swap_usage_bytes gauge
system_swap_usage_bytes 0
```

---

## Prometheus Integration

### Scrape Configuration

Add to `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: "realtimevoicechat"
    scrape_interval: 5s # Poll every 5 seconds
    static_configs:
      - targets: ["localhost:8000"]
    metrics_path: "/metrics"
```

### Grafana Dashboard Queries

**CPU Temperature Panel:**

```promql
system_cpu_temperature_celsius{job="realtimevoicechat"}
```

**Memory Availability Panel:**

```promql
system_memory_available_bytes{job="realtimevoicechat"} / (1024^3)  # Convert to GB
```

**CPU Usage Panel:**

```promql
system_cpu_percent{job="realtimevoicechat"}
```

**Swap Usage Panel:**

```promql
system_swap_usage_bytes{job="realtimevoicechat"} / (1024^3)  # Convert to GB
```

### Alert Rules

**Critical CPU Temperature (Pi 5):**

```yaml
- alert: CPUTempCritical
  expr: system_cpu_temperature_celsius >= 80
  for: 1m
  annotations:
    summary: "CPU temperature critical ({{ $value }}°C)"
    description: "Pi 5 is throttling due to high temperature"
```

**Low Memory Alert:**

```yaml
- alert: LowMemory
  expr: system_memory_available_bytes < 1073741824 # < 1GB
  for: 2m
  annotations:
    summary: "Low available memory ({{ $value | humanize }}B)"
    description: "System may start swapping or OOM"
```

**High Swap Usage Alert:**

```yaml
- alert: HighSwapUsage
  expr: system_swap_usage_bytes > 2147483648 # > 2GB
  for: 5m
  annotations:
    summary: "High swap usage ({{ $value | humanize }}B)"
    description: "System is memory-constrained and swapping heavily"
```

---

## Security Considerations

- **No Authentication Required**: Metrics must be accessible to Prometheus scraper
- **No Sensitive Data**: Metrics contain only system resource data (no user info)
- **Rate Limiting**: Not applied to metrics endpoint (Prometheus needs reliable access)
- **Resource Impact**: Metrics collection adds < 1% CPU overhead

---

## Testing

### Unit Tests

```python
async def test_metrics_endpoint_format():
    response = await client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/plain; version=0.0.4"

    body = response.text
    assert "system_memory_available_bytes" in body
    assert "system_cpu_temperature_celsius" in body
    assert "system_cpu_percent" in body
    assert "system_swap_usage_bytes" in body

async def test_metrics_values_valid():
    response = await client.get("/metrics")
    body = response.text

    # Parse metrics
    metrics = parse_prometheus_text(body)

    assert metrics["system_memory_available_bytes"] >= 0
    assert metrics["system_cpu_temperature_celsius"] >= -1
    assert 0 <= metrics["system_cpu_percent"] <= 100
    assert metrics["system_swap_usage_bytes"] >= 0

async def test_metrics_low_latency():
    start = time.perf_counter()
    response = await client.get("/metrics")
    elapsed = time.perf_counter() - start

    assert response.status_code == 200
    assert elapsed < 0.1  # < 100ms
```

### Integration Tests

```python
async def test_metrics_prometheus_compatible():
    """Test metrics can be scraped by Prometheus."""
    response = await client.get("/metrics")

    # Verify Prometheus parser can parse output
    from prometheus_client.parser import text_string_to_metric_families

    metrics = list(text_string_to_metric_families(response.text))
    assert len(metrics) == 4

    metric_names = [m.name for m in metrics]
    assert "system_memory_available_bytes" in metric_names
    assert "system_cpu_temperature_celsius" in metric_names
    assert "system_cpu_percent" in metric_names
    assert "system_swap_usage_bytes" in metric_names
```

---

## Future Enhancements (Phase 4)

1. **Application-Level Metrics:**

   - `realtimevoicechat_websocket_connections_active` (gauge)
   - `realtimevoicechat_pipeline_latency_seconds` (histogram)
   - `realtimevoicechat_llm_requests_total` (counter)
   - `realtimevoicechat_tts_bytes_generated_total` (counter)

2. **GPU Metrics (if using GPU on Pi 5):**

   - `system_gpu_temperature_celsius` (gauge)
   - `system_gpu_memory_used_bytes` (gauge)

3. **Disk I/O Metrics:**
   - `system_disk_read_bytes_total` (counter)
   - `system_disk_write_bytes_total` (counter)

---

## Changelog

**v1.0.0** (2025-10-17)

- Initial metrics endpoint specification
- 4 core metrics: memory, CPU temp, CPU usage, swap
- Prometheus plain text format
- Pi 5 optimization (minimal overhead)
