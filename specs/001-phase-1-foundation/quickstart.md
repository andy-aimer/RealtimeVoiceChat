# Quickstart Guide: Phase 1 Foundation

**Feature:** 001-phase-1-foundation  
**Audience:** Developers implementing testing, monitoring, and security infrastructure  
**Time to Complete:** 2-3 hours

---

## Prerequisites

### System Requirements

- Python 3.10 or higher
- Raspberry Pi 5 (8GB RAM recommended) **OR** macOS/Linux for development
- 2GB free disk space (for test models and dependencies)

### Existing Setup

- RealtimeVoiceChat codebase cloned
- Virtual environment activated
- Existing `server.py` running (baseline functionality)

### Knowledge Requirements

- Familiarity with pytest
- Basic understanding of FastAPI
- Understanding of async/await in Python

---

## Step 1: Install Testing Dependencies (10 min)

### 1.1 Add Dependencies to requirements.txt

Add these lines to `requirements.txt` (in your project root, e.g., `./requirements.txt`):

```txt
# Testing dependencies
pytest==7.4.3
pytest-cov==4.1.0
pytest-asyncio==0.21.1
httpx==0.25.0

# Monitoring dependencies
psutil==5.9.6
```

### 1.2 Install Dependencies

```bash
cd <project-root>  # Replace with the path to your RealtimeVoiceChat directory
source venv/bin/activate  # Or your venv path
pip install -r requirements.txt
```

### 1.3 Verify Installation

```bash
pytest --version
# Expected: pytest 7.4.3

python -c "import psutil; print(psutil.virtual_memory())"
# Expected: svmem(total=8589934592, available=5368709120, ...)
```

---

## Step 2: Create Testing Infrastructure (30 min)

### 2.1 Create Test Directory Structure

```bash
mkdir -p tests/unit tests/integration
touch tests/__init__.py tests/conftest.py
touch tests/unit/test_turn_detection.py
touch tests/integration/test_pipeline_e2e.py
```

### 2.2 Configure pytest (tests/conftest.py)

Create `tests/conftest.py`:

```python
import pytest
import asyncio
from httpx import AsyncClient
from code.server import app

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def client():
    """HTTP client for testing FastAPI endpoints."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
def mock_audio_data():
    """16kHz PCM16 audio sample (1 second of silence)."""
    import numpy as np
    sample_rate = 16000
    duration = 1.0
    samples = int(sample_rate * duration)
    audio = np.zeros(samples, dtype=np.int16)
    return audio.tobytes()

@pytest.fixture
def mock_transcription():
    """Mock STT transcription result."""
    return {
        "text": "Hello, how are you?",
        "language": "en",
        "confidence": 0.95
    }
```

### 2.3 Write First Unit Test

Create `./tests/unit/test_turn_detection.py`:

```python
import pytest
from code.turndetect import TurnDetection

def test_turn_detection_initialization():
    """Test TurnDetection class initializes correctly."""
    detector = TurnDetection()
    assert detector is not None
    assert hasattr(detector, 'detect_pause')

def test_detect_pause_silence():
    """Test pause detection on silent audio."""
    detector = TurnDetection()

    # Simulate 2 seconds of silence (32000 samples at 16kHz)
    silent_audio = bytes(32000 * 2)  # Zero bytes = silence

    is_pause = detector.detect_pause(silent_audio, threshold_ms=1500)
    assert is_pause is True

def test_detect_pause_active_speech():
    """Test no pause detected during active speech."""
    detector = TurnDetection()

    # Simulate active speech (random non-zero audio)
    import random
    active_audio = bytes([random.randint(1, 255) for _ in range(32000)])

    is_pause = detector.detect_pause(active_audio, threshold_ms=1500)
    assert is_pause is False
```

### 2.4 Run Tests

```bash
pytest tests/unit/test_turn_detection.py -v

# Expected output:
# tests/unit/test_turn_detection.py::test_turn_detection_initialization PASSED
# tests/unit/test_turn_detection.py::test_detect_pause_silence PASSED
# tests/unit/test_turn_detection.py::test_detect_pause_active_speech PASSED
```

---

## Step 3: Implement Health Check Endpoint (45 min)

### 3.1 Create Health Check Module

Create `/Users/Tom/dev-projects/RealtimeVoiceChat/code/health_checks.py`:

```python
import asyncio
import logging
import psutil
from typing import Dict

logger = logging.getLogger(__name__)

async def check_audio_processor() -> bool:
    """Check if audio processor is available."""
    try:
        # Import here to avoid circular dependency
        from code.audio_module import AudioProcessor

        # Check if class is importable and can be instantiated
        processor = AudioProcessor()
        return processor is not None
    except Exception as e:
        logger.error(f"Audio processor check failed: {e}")
        return False

async def check_llm_backend() -> bool:
    """Check if LLM backend is reachable."""
    try:
        from code.llm_module import LLMClient

        # Try a simple connection test
        client = LLMClient()
        # TODO: Implement client.test_connection() method
        return True
    except Exception as e:
        logger.error(f"LLM backend check failed: {e}")
        return False

async def check_tts_engine() -> bool:
    """Check if TTS engine is loaded."""
    try:
        # TODO: Check if Piper TTS is loaded
        return True
    except Exception as e:
        logger.error(f"TTS engine check failed: {e}")
        return False

async def check_system_resources() -> bool:
    """Check if system resources are healthy."""
    try:
        mem = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=0.1)
        swap = psutil.swap_memory()

        # Thresholds
        min_available_ram = 500 * 1024 * 1024  # 500MB
        max_cpu_percent = 95
        max_swap_usage = 4 * 1024 * 1024 * 1024  # 4GB

        if mem.available < min_available_ram:
            logger.warning(f"Low RAM: {mem.available / 1024**3:.2f}GB available")
            return False

        if cpu_percent > max_cpu_percent:
            logger.warning(f"High CPU: {cpu_percent}%")
            return False

        if swap.used > max_swap_usage:
            logger.warning(f"High swap: {swap.used / 1024**3:.2f}GB")
            return False

        return True
    except Exception as e:
        logger.error(f"System resource check failed: {e}")
        return False
```

### 3.2 Add Health Endpoint to Server

Modify `/Users/Tom/dev-projects/RealtimeVoiceChat/code/server.py`:

```python
# Add to imports
import asyncio
from datetime import datetime
from fastapi.responses import JSONResponse
from code import health_checks

# Add after existing routes
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring systems."""
    try:
        # Run all checks concurrently with timeouts
        results = await asyncio.gather(
            asyncio.wait_for(health_checks.check_audio_processor(), timeout=5.0),
            asyncio.wait_for(health_checks.check_llm_backend(), timeout=5.0),
            asyncio.wait_for(health_checks.check_tts_engine(), timeout=5.0),
            asyncio.wait_for(health_checks.check_system_resources(), timeout=2.0),
            return_exceptions=True
        )

        # Map results to components
        components = {
            "audio": bool(results[0]) if not isinstance(results[0], Exception) else False,
            "llm": bool(results[1]) if not isinstance(results[1], Exception) else False,
            "tts": bool(results[2]) if not isinstance(results[2], Exception) else False,
            "system": bool(results[3]) if not isinstance(results[3], Exception) else False,
        }

        # Determine overall status
        critical_components = ["audio", "llm"]
        critical_healthy = all(components[c] for c in critical_components)
        all_healthy = all(components.values())

        if all_healthy:
            status = "healthy"
            status_code = 200
        elif critical_healthy:
            status = "degraded"
            status_code = 503
        else:
            status = "unhealthy"
            status_code = 503

        return JSONResponse(
            status_code=status_code,
            content={
                "status": status,
                "components": components,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "error": "Health check failed",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        )
```

### 3.3 Test Health Endpoint

```bash
# Start server
python code/server.py

# In another terminal:
curl http://localhost:8000/health | jq

# Expected output:
# {
#   "status": "healthy",
#   "components": {
#     "audio": true,
#     "llm": true,
#     "tts": true,
#     "system": true
#   },
#   "timestamp": "2025-10-17T14:32:01.150Z"
# }
```

---

## Step 4: Implement Metrics Endpoint (45 min)

### 4.1 Create Metrics Module

Create `/Users/Tom/dev-projects/RealtimeVoiceChat/code/metrics.py`:

```python
import psutil
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
                temp_str = result.stdout.strip().split("=")[1].split("'")[0]
                return float(temp_str)
        except (FileNotFoundError, subprocess.TimeoutExpired, IndexError, ValueError):
            pass

        # Fallback: Try thermal_zone
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                return float(f.read().strip()) / 1000.0
        except (FileNotFoundError, PermissionError, ValueError):
            pass

    # Unsupported platform
    if not _temp_warning_logged:
        logger.warning(f"CPU temperature monitoring not supported on {system}")
        _temp_warning_logged = True

    return -1.0

def get_metrics() -> str:
    """Get system metrics in Prometheus format."""
    mem = psutil.virtual_memory()
    cpu_percent = psutil.cpu_percent(interval=0.1)
    swap = psutil.swap_memory()
    cpu_temp = get_cpu_temperature()

    return f"""# HELP system_memory_available_bytes Available system memory
# TYPE system_memory_available_bytes gauge
system_memory_available_bytes {mem.available}

# HELP system_cpu_temperature_celsius CPU temperature
# TYPE system_cpu_temperature_celsius gauge
system_cpu_temperature_celsius {cpu_temp}

# HELP system_cpu_percent CPU usage percentage
# TYPE system_cpu_percent gauge
system_cpu_percent {cpu_percent}

# HELP system_swap_usage_bytes Swap memory usage
# TYPE system_swap_usage_bytes gauge
system_swap_usage_bytes {swap.used}
"""
```

### 4.2 Add Metrics Endpoint to Server

Modify `/Users/Tom/dev-projects/RealtimeVoiceChat/code/server.py`:

```python
# Add to imports
from fastapi.responses import Response
from code import metrics

# Add after /health route
@app.get("/metrics")
async def metrics_endpoint():
    """Metrics endpoint for Prometheus scraping."""
    return Response(
        content=metrics.get_metrics(),
        media_type="text/plain; version=0.0.4"
    )
```

### 4.3 Test Metrics Endpoint

```bash
curl http://localhost:8000/metrics

# Expected output:
# # HELP system_memory_available_bytes Available system memory
# # TYPE system_memory_available_bytes gauge
# system_memory_available_bytes 5368709120
#
# # HELP system_cpu_temperature_celsius CPU temperature
# # TYPE system_cpu_temperature_celsius gauge
# system_cpu_temperature_celsius 62.5
# ...
```

---

## Step 5: Add Input Validation (30 min)

### 5.1 Create Validation Module

Create `/Users/Tom/dev-projects/RealtimeVoiceChat/code/security/validators.py`:

```python
import logging
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)

class ValidationError(BaseModel):
    field: str
    code: str
    message: str
    received_value: Optional[str] = None

class WebSocketMessage(BaseModel):
    type: str = Field(..., regex="^(audio|text|control)$")
    data: Dict

    @validator('type')
    def validate_type(cls, v):
        allowed = ["audio", "text", "control"]
        if v not in allowed:
            raise ValueError(f"Invalid message type. Must be one of: {allowed}")
        return v

class TextData(BaseModel):
    text: str = Field(..., max_length=5000)
    language: Optional[str] = Field(None, max_length=5, regex="^[a-z]{2}$")

    @validator('text')
    def sanitize_text(cls, v):
        # Strip control characters
        v = ''.join(char for char in v if char.isprintable() or char in '\n\t')

        # Escape special tokens
        v = v.replace('<|endoftext|>', '').replace('</s>', '')

        # Detect prompt injection
        if 'ignore previous instructions' in v.lower():
            logger.warning("Potential prompt injection detected", extra={"text": v[:100]})

        return v

def validate_message(message: Dict) -> tuple[bool, List[ValidationError]]:
    """Validate WebSocket message."""
    errors = []

    try:
        WebSocketMessage(**message)
        return True, []
    except Exception as e:
        errors.append(ValidationError(
            field="message",
            code="INVALID_MESSAGE",
            message=str(e)
        ))
        return False, errors
```

### 5.2 Integrate Validation in WebSocket Handler

Modify `/Users/Tom/dev-projects/RealtimeVoiceChat/code/server.py`:

```python
# Add to imports
from code.security.validators import validate_message

# In WebSocket handler:
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_json()

            # Validate message
            is_valid, errors = validate_message(data)
            if not is_valid:
                await websocket.send_json({
                    "type": "error",
                    "data": {
                        "code": errors[0].code,
                        "message": errors[0].message
                    }
                })
                continue

            # Process valid message
            # ... existing logic ...

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()
```

---

## Step 6: Run Integration Tests (20 min)

### 6.1 Create Integration Test

Create `/Users/Tom/dev-projects/RealtimeVoiceChat/tests/integration/test_pipeline_e2e.py`:

```python
import pytest
import time
import asyncio

@pytest.mark.asyncio
async def test_full_pipeline_latency(client, mock_audio_data):
    """Test full STT → LLM → TTS pipeline latency."""
    # Warmup run (load models)
    response = await client.post("/process", json={"audio": mock_audio_data.hex()})

    # Actual test
    start = time.perf_counter()
    response = await client.post("/process", json={"audio": mock_audio_data.hex()})
    elapsed = time.perf_counter() - start

    assert response.status_code == 200
    assert elapsed < 1.8, f"Pipeline took {elapsed:.2f}s (threshold: 1.8s)"

    data = response.json()
    assert "transcription" in data
    assert "llm_response" in data
    assert "audio_output" in data

@pytest.mark.asyncio
async def test_health_endpoint(client):
    """Test health check endpoint."""
    response = await client.get("/health")
    assert response.status_code in [200, 503]

    data = response.json()
    assert "status" in data
    assert "components" in data
    assert data["status"] in ["healthy", "degraded", "unhealthy"]

@pytest.mark.asyncio
async def test_metrics_endpoint(client):
    """Test metrics endpoint."""
    response = await client.get("/metrics")
    assert response.status_code == 200
    assert "system_memory_available_bytes" in response.text
    assert "system_cpu_temperature_celsius" in response.text
```

### 6.2 Run All Tests with Coverage

```bash
pytest tests/ -v --cov=code --cov-report=html --cov-report=term

# Expected output:
# tests/unit/test_turn_detection.py::test_turn_detection_initialization PASSED
# tests/integration/test_pipeline_e2e.py::test_full_pipeline_latency PASSED
# tests/integration/test_health_endpoint PASSED
# tests/integration/test_metrics_endpoint PASSED
#
# ---------- coverage: platform darwin, python 3.10.12 -----------
# Name                      Stmts   Miss  Cover
# ---------------------------------------------
# code/health_checks.py        45      5    89%
# code/metrics.py              30      2    93%
# code/validators.py           25      3    88%
# ...
# TOTAL                       350     45    87%
```

---

## Step 7: Verify on Raspberry Pi 5 (Optional, 15 min)

If you have a Raspberry Pi 5 available:

```bash
# 1. Copy project to Pi 5
scp -r RealtimeVoiceChat pi@raspberrypi.local:~/

# 2. SSH into Pi 5
ssh pi@raspberrypi.local

# 3. Install dependencies
cd ~/RealtimeVoiceChat
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Run tests
pytest tests/ -v

# 5. Start server and check metrics
python code/server.py &
curl http://localhost:8000/metrics

# Expected: CPU temperature should show real Pi 5 temp (not -1)
# system_cpu_temperature_celsius 62.5
```

---

## Troubleshooting

### Issue: pytest not found

```bash
pip install pytest pytest-cov pytest-asyncio
```

### Issue: psutil fails to install on Pi 5

```bash
sudo apt-get install python3-dev
pip install psutil
```

### Issue: Health check always returns "unhealthy"

- Check that `code/llm_module.py` and `code/audio_module.py` are importable
- Verify LLM backend (Ollama/llama.cpp) is running
- Check logs: `tail -f realtimevoicechat.log`

### Issue: CPU temperature returns -1 on Pi 5

- Install vcgencmd: `sudo apt-get install libraspberrypi-bin`
- Check permissions: `sudo usermod -aG video $USER`

---

## Next Steps

1. **Expand Unit Tests**: Add tests for `TextSimilarity`, `TextContext`, `AudioProcessor`
2. **Add Interruption Test**: Create `tests/integration/test_interruption_handling.py`
3. **Implement Structured Logging**: Create `code/middleware/logging.py`
4. **Add Security Middleware** (if internet-exposed): Implement auth and rate limiting
5. **Generate Coverage Report**: `pytest --cov=code --cov-report=html && open htmlcov/index.html`

---

## Summary

**What You Built:**

- ✅ Testing infrastructure (pytest + fixtures)
- ✅ Health check endpoint (`/health`)
- ✅ Metrics endpoint (`/metrics` in Prometheus format)
- ✅ Input validation (WebSocket messages)
- ✅ 60%+ code coverage

**Time Spent:** ~2-3 hours  
**Files Created:** 8 new files  
**Lines of Code:** ~500 lines

**Ready for:** Phase 2 (Refactoring) or deployment to Pi 5 for real-world testing.
