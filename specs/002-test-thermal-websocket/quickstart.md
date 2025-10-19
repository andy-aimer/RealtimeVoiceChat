# Phase 2 Quickstart Guide

**Feature**: Phase 2 Infrastructure Improvements  
**Branch**: `002-test-thermal-websocket`  
**Date**: October 19, 2025

## Overview

This guide provides quick start instructions for testing and using Phase 2 infrastructure improvements: thread cleanup (P1), thermal protection (P2), and WebSocket reconnection (P3).

---

## Prerequisites

```bash
# Ensure Phase 1 foundation is complete
git checkout 001-phase-1-foundation---IT-6

# Checkout Phase 2 branch
git checkout 002-test-thermal-websocket

# Install dependencies (if any new ones)
pip install -r requirements.txt

# Optional: Install pytest-xdist for test isolation
pip install pytest-xdist
```

---

## P1: Thread Cleanup Testing

### Problem (Phase 1)

```bash
# Before fix: Test suite hangs indefinitely
pytest tests/
# Hangs after ~20 tests, requires Ctrl+C

# Workaround: Run file-by-file
pytest tests/test_audio.py
pytest tests/test_llm.py
# Each file completes, but slow (~8-10 minutes total)
```

### Solution (Phase 2)

```bash
# After fix: Full test suite completes
pytest tests/ --cov=code --cov-report=html
# Expected:
# - All tests pass
# - Completes in <5 minutes
# - Coverage ≥60%
# - No orphaned threads
```

### Verify Thread Cleanup

```python
# tests/integration/test_full_suite.py
import pytest
import threading
import time

def test_no_orphaned_threads():
    """Verify TurnDetector threads cleaned up after use"""
    from code.turndetect import TurnDetector

    initial_threads = threading.active_count()

    # Use TurnDetector with context manager
    with TurnDetector() as detector:
        # Threads should be running
        assert threading.active_count() > initial_threads

    # Wait for cleanup
    time.sleep(0.5)

    # Threads should be cleaned up
    final_threads = threading.active_count()
    assert final_threads == initial_threads
```

### Run Individual Tests

```bash
# Run specific test module
pytest tests/unit/test_thread_cleanup.py -v

# Run with debugging
pytest tests/unit/test_thread_cleanup.py -v --log-cli-level=DEBUG

# Run with coverage
pytest tests/unit/test_thread_cleanup.py --cov=code.utils.lifecycle
```

### Optional: pytest-xdist

```bash
# Run tests in parallel with process isolation
pytest tests/ -n auto --dist loadfile

# Expected: Each test file runs in separate process
# Benefits: No thread accumulation between tests
```

---

## P2: Thermal Protection Testing

### Quick Test (All Platforms)

```python
# Test thermal monitoring with simulation mode
python -c "
from code.monitoring.thermal_monitor import ThermalMonitor
import time

monitor = ThermalMonitor(simulation_mode=True)
print(f'Temperature: {monitor.get_temperature()}°C')
print(f'Platform supported: {monitor.get_state().platform_supported}')

# Simulate high temperature
monitor._simulate_temperature(85.0)
print(f'Protection active: {monitor.check_thermal_protection()}')

# Simulate cooldown
monitor._simulate_temperature(79.0)
print(f'Protection active: {monitor.check_thermal_protection()}')
"
```

Expected output:

```
Temperature: 25.0°C
Platform supported: True
Protection active: True
Protection active: False
```

### Raspberry Pi 5 Test (Hardware)

```bash
# Check if thermal interface available
cat /sys/class/thermal/thermal_zone0/temp
# Expected: Integer (e.g., 45000 = 45.0°C)

# Run thermal monitor in standalone mode
python -m code.monitoring.thermal_monitor --verbose

# Expected output:
# [INFO] Thermal monitor started
# [INFO] Current temperature: 45.0°C (normal)
# ... (every 1 second)
```

### Stress Test (Raspberry Pi 5 Only)

```bash
# Install stress-ng (if not installed)
sudo apt install stress-ng

# Generate CPU load to trigger thermal protection
stress-ng --cpu 4 --timeout 60s &

# Monitor thermal protection in real-time
python -c "
from code.monitoring.thermal_monitor import ThermalMonitor
import time

monitor = ThermalMonitor()
monitor.start_monitoring()

print('Monitoring for 60 seconds (stress test)...')
for _ in range(60):
    state = monitor.get_state()
    status = 'PROTECTED' if state.protection_active else 'NORMAL'
    print(f'[{status}] Temp: {state.current_temp:.1f}°C')
    time.sleep(1)

monitor.stop_monitoring()
print(f'Max temp observed: {monitor.get_state().max_temp_observed:.1f}°C')
print(f'Trigger count: {monitor.get_state().trigger_count}')
"
```

Expected behavior:

- Temperature rises under load
- Protection triggers at 85°C (CRITICAL log)
- Temperature stabilizes or drops
- Protection resumes at <80°C (INFO log)

### Integration Test

```bash
# Test thermal protection with LLM integration
pytest tests/integration/test_thermal_integration.py -v

# Expected:
# - Thermal trigger pauses LLM inference
# - Thermal resume restarts LLM inference
# - No crashes or exceptions
```

### Non-Pi Platform Behavior

```python
# On macOS/Windows/Linux (non-Pi)
from code.monitoring.thermal_monitor import ThermalMonitor

monitor = ThermalMonitor()
temp = monitor.get_temperature()
print(f"Temperature: {temp}°C")
# Expected: -1.0 (graceful fallback, no error)

state = monitor.get_state()
print(f"Platform supported: {state.platform_supported}")
# Expected: False

print(f"Protection active: {state.protection_active}")
# Expected: False (never activates on unsupported platforms)
```

---

## P3: WebSocket Reconnection Testing

### Server Setup

```bash
# Start server
python code/server.py

# Expected output:
# INFO:     Uvicorn running on http://localhost:8000
# INFO:     Session cleanup task started
```

### Client Test (Browser Console)

Open browser to `http://localhost:8000` and open DevTools console:

```javascript
// Test 1: Normal connection
// Expected: "Connected" message, session_id received

// Test 2: Disconnect network
// Chrome DevTools -> Network tab -> Toggle offline mode
// Expected: "Disconnected" message, automatic reconnection attempts

// Test 3: Reconnect network
// Toggle offline mode off
// Expected: "Reconnecting (attempt 1/10)..." → "Connected" within 10s

// Test 4: Session persistence
// Send message: ws.send(JSON.stringify({message: "Hello"}))
// Disconnect, reconnect within 5 minutes
// Expected: Session restored, conversation_context preserved
```

### Automated Test

```bash
# Run WebSocket lifecycle tests
pytest tests/integration/test_websocket_lifecycle.py -v

# Expected tests:
# - test_websocket_connection: Basic connection
# - test_websocket_reconnection: Disconnect/reconnect flow
# - test_session_persistence: Context preserved across reconnections
# - test_reconnection_timeout: Session expiration after 5 minutes
# - test_exponential_backoff: Retry delays (1s, 2s, 4s, 8s, ...)
```

### Manual Reconnection Test

```bash
# Terminal 1: Start server
python code/server.py

# Terminal 2: Test client with automatic reconnection
python -c "
import asyncio
import websockets
import json

async def test_reconnection():
    uri = 'ws://localhost:8000/ws'
    session_id = None

    # Initial connection
    async with websockets.connect(uri) as ws:
        data = json.loads(await ws.recv())
        session_id = data['session_id']
        print(f'Session created: {session_id}')

        await ws.send(json.dumps({'message': 'Hello'}))
        print('Message sent')

    # Disconnect (close connection)
    print('Disconnected, waiting 2 seconds...')
    await asyncio.sleep(2)

    # Reconnect with session_id
    async with websockets.connect(f'{uri}?session_id={session_id}') as ws:
        data = json.loads(await ws.recv())
        print(f'Session restored: {data}')
        assert data['type'] == 'session_restored'
        assert data['session_id'] == session_id

asyncio.run(test_reconnection())
"
```

Expected output:

```
Session created: a1b2c3d4-...
Message sent
Disconnected, waiting 2 seconds...
Session restored: {'type': 'session_restored', 'session_id': 'a1b2c3d4-...', 'context': {...}}
```

### Session Expiration Test

```bash
# Test session timeout (5 minutes)
python -c "
import asyncio
import websockets
import json
import time

async def test_expiration():
    uri = 'ws://localhost:8000/ws'

    # Connect and get session_id
    async with websockets.connect(uri) as ws:
        data = json.loads(await ws.recv())
        session_id = data['session_id']
        print(f'Session created: {session_id}')

    # Wait beyond 5-minute timeout
    print('Waiting 6 minutes for session expiration...')
    time.sleep(360)

    # Try to reconnect
    async with websockets.connect(f'{uri}?session_id={session_id}') as ws:
        data = json.loads(await ws.recv())
        # Should receive session_created (new session)
        assert data['type'] == 'session_created'
        assert data['session_id'] != session_id
        print(f'Session expired, new session: {data[\"session_id\"]}')

asyncio.run(test_expiration())
"
```

---

## Integration Testing

### Full Pipeline Test

```bash
# Test complete voice chat pipeline with Phase 2 features
pytest tests/integration/test_full_pipeline.py -v

# Expected:
# - Test suite completes without hanging (P1)
# - Thermal monitoring active during LLM inference (P2)
# - WebSocket reconnection preserves conversation (P3)
```

### Coverage Report

```bash
# Generate HTML coverage report
pytest tests/ --cov=code --cov-report=html

# View report
open htmlcov/index.html

# Expected:
# - Overall coverage ≥60%
# - New modules (monitoring/, websocket/, utils/) ≥80%
# - Thread cleanup code 100% (critical path)
```

### CI/CD Simulation

```bash
# Simulate GitHub Actions CI workflow
bash -c "
set -e
echo 'Running tests...'
pytest tests/ --cov=code --cov-report=term --timeout=300
echo 'Tests passed!'
"

# Expected:
# - All tests pass
# - Completes in <5 minutes (no timeout)
# - Coverage meets target (≥60%)
```

---

## Troubleshooting

### Test Suite Still Hanging

```bash
# Check if ManagedThread cleanup implemented
grep -r "ManagedThread" code/turndetect.py

# Run with pytest-xdist for process isolation
pip install pytest-xdist
pytest tests/ -n auto --dist loadfile

# Debug specific thread issues
pytest tests/unit/test_thread_cleanup.py -v --log-cli-level=DEBUG
```

### Thermal Monitoring Not Working

```bash
# Check if on Raspberry Pi 5
python -c "
import platform
print(f'Platform: {platform.system()}')
print(f'Machine: {platform.machine()}')

# Try reading temperature file
try:
    with open('/sys/class/thermal/thermal_zone0/temp') as f:
        temp = int(f.read()) / 1000.0
        print(f'Temperature: {temp}°C')
except FileNotFoundError:
    print('Thermal interface not available (not Pi 5)')
"

# Use simulation mode for testing
export THERMAL_SIMULATION_MODE=true
python code/server.py
```

### WebSocket Reconnection Failing

```bash
# Check session manager logs
tail -f logs/server.log | grep -i session

# Test session creation directly
python -c "
from code.websocket.session_manager import SessionManager

manager = SessionManager(timeout_minutes=5)
session_id = manager.create_session()
print(f'Session created: {session_id}')

# Restore immediately
session = manager.restore_session(session_id)
print(f'Session restored: {session is not None}')
"

# Verify cleanup task running
curl http://localhost:8000/health
# Expected JSON includes: "active_sessions": <count>
```

---

## Performance Validation

### Test Suite Performance

```bash
# Measure test suite execution time
time pytest tests/

# Expected: <5 minutes (SC-001)
# Compare with Phase 1: ~8-10 minutes (file-by-file)
```

### Thermal Response Time

```python
# Measure thermal protection trigger latency
from code.monitoring.thermal_monitor import ThermalMonitor
import time

monitor = ThermalMonitor(simulation_mode=True)

triggered = False
def callback(state):
    global triggered
    triggered = True

monitor.register_callback(callback)
monitor.start_monitoring()

# Simulate high temperature
start = time.time()
monitor._simulate_temperature(85.0)

while not triggered and time.time() - start < 15:
    time.sleep(0.1)

latency = time.time() - start
print(f'Trigger latency: {latency:.2f}s')
assert latency < 10.0  # SC-006: Within 10 seconds

monitor.stop_monitoring()
```

### WebSocket Reconnection Time

```bash
# Measure reconnection latency
pytest tests/integration/test_websocket_lifecycle.py::test_reconnection_latency -v

# Expected: 90% of reconnections <10s (SC-014)
```

---

## Configuration

### Environment Variables

```bash
# Thermal monitoring
export THERMAL_ENABLED=true
export THERMAL_TRIGGER_THRESHOLD=85.0
export THERMAL_RESUME_THRESHOLD=80.0
export THERMAL_POLL_INTERVAL=1.0
export THERMAL_SIMULATION_MODE=false

# WebSocket sessions
export WEBSOCKET_SESSION_TIMEOUT_MINUTES=5
export WEBSOCKET_PING_INTERVAL_SECONDS=30
export WEBSOCKET_MAX_RECONNECTION_ATTEMPTS=10

# Thread lifecycle
export THREAD_STOP_TIMEOUT_SECONDS=5.0
export THREAD_LOG_LEVEL=INFO
```

### Configuration File

```bash
# Create .env file in project root
cat > .env << EOF
THERMAL_ENABLED=true
THERMAL_TRIGGER_THRESHOLD=85.0
THERMAL_RESUME_THRESHOLD=80.0
WEBSOCKET_SESSION_TIMEOUT_MINUTES=5
THREAD_STOP_TIMEOUT_SECONDS=5.0
EOF

# Load configuration
python -c "
from code.config.phase2_config import Phase2Config
config = Phase2Config()
print(config.dict())
"
```

---

## Next Steps

### After Phase 2 Validation

1. **Merge to main**:

   ```bash
   git checkout main
   git merge 002-test-thermal-websocket
   git push origin main
   ```

2. **Tag release**:

   ```bash
   git tag -a v0.2.0 -m "Phase 2: Infrastructure improvements"
   git push origin v0.2.0
   ```

3. **Update documentation**:

   - README.md (mention thermal protection, WebSocket reconnection)
   - DEPLOYMENT.md (Raspberry Pi 5 thermal configuration)
   - CHANGELOG.md (Phase 2 features)

4. **Deploy to Raspberry Pi 5**:
   ```bash
   # On Pi 5
   git pull origin main
   docker-compose down
   docker-compose up -d --build
   ```

---

## Success Criteria Checklist

**P1: Thread Cleanup** ✅

- [ ] Test suite completes in <5 minutes (10/10 runs)
- [ ] GitHub Actions CI completes without timeout
- [ ] Coverage report generated (≥60%)
- [ ] Zero orphaned threads after tests

**P2: Thermal Protection** ✅

- [ ] Protection triggers within 10s of 85°C
- [ ] Temperature capped at 87°C during load
- [ ] Resumes within 30s of dropping below 80°C
- [ ] Zero thermal crashes during testing
- [ ] Clear notification logs (CRITICAL/INFO)

**P3: WebSocket Reliability** ✅

- [ ] 95% recovery from disconnections <60s
- [ ] 100% session preservation for disconnections <5 min
- [ ] Clear error messages for failures
- [ ] 90% reconnections succeed within 10s
- [ ] Zero data loss during disconnect/reconnect

---

**Last Updated**: October 19, 2025
