# RealtimeVoiceChat Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-10-18

## Active Technologies

- **Python 3.10+**: Core language
- **FastAPI**: Web framework for HTTP/WebSocket endpoints
- **pytest 7.4.3**: Testing framework with async support
- **httpx 0.25.0**: Async HTTP client for testing
- **psutil 5.9.6**: System resource monitoring
- **Pydantic**: Data validation and settings management

## Database & Storage

- In-memory dict-based session storage (no external databases)
- No persistent storage for health/metrics (cached values only)

## Project Structure

```
code/
  health_checks.py          # Component health checks
  metrics.py                # System metrics (Prometheus format)
  server.py                 # FastAPI app with /health and /metrics
  monitoring/
    pi5_monitor.py         # Pi 5 resource monitoring
  middleware/
    logging.py             # Structured JSON logging
  security/
    validators.py          # Input validation

tests/
  conftest.py              # Pytest fixtures
  unit/                    # Unit tests
  integration/             # Integration tests
```

## Commands

```bash
# Run all tests with coverage
pytest tests/ -v --cov=code --cov-report=html --cov-report=term

# Run only unit tests
pytest tests/unit/ -v

# Run only integration tests
pytest tests/integration/ -v

# Start development server
python code/server.py

# Check health endpoint
curl http://localhost:8000/health | jq

# Check metrics endpoint
curl http://localhost:8000/metrics
```

## Code Style

- **File Size Limit**: Maximum 300 lines per file (strict)
- **Test Coverage**: 60% minimum for personal deployment, 80% for production
- **Error Handling**: 3 retries with exponential backoff (2s, 4s, 8s)
- **Logging**: Structured JSON format
- **Performance**: <2% CPU overhead for monitoring on Pi 5

## Recent Changes

- **001-phase-1-foundation** (2025-10-18): Added testing infrastructure, health/metrics endpoints, input validation

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
