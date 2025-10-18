# RealtimeVoiceChat Production-Ready Constitution

## 🎯 Mission Statement

Transform RealtimeVoiceChat from a research-quality demo into a production-ready, scalable, and maintainable real-time AI voice conversation platform.

## 📋 Core Principles

### 1. **Reliability First**

- All components must gracefully handle failures
- No silent errors - log everything with context
- Implement circuit breakers for external dependencies
- Add health checks for all critical services

### 0. **Offline-First Architecture** 🔌

- **System runs 100% offline by default** (with Ollama backend)
- All models downloaded once, cached locally
- No cloud API calls required for core functionality
- Optional cloud backends (OpenAI) for enhanced quality
- One-time internet setup, then fully air-gapped capable

### 2. **Observability**

- Comprehensive logging with structured format (JSON)
- Metrics for latency, throughput, and error rates
- Request tracing across the entire pipeline
- Performance profiling for bottleneck identification

### 3. **Security**

- **Authentication (deployment-dependent)**:
  - ❌ **Not needed** for: localhost, home network, offline/air-gapped, single-user
  - ✅ **Required** for: internet-exposed, multi-user, enterprise, SaaS
- Rate limiting to prevent abuse (optional for single-user)
- Input validation on all user-provided data
- Secrets management (no hardcoded keys)

### 4. **Maintainability**

- Single Responsibility Principle - one file, one concern
- Maximum 300 lines per file
- Clear separation of concerns
- Comprehensive documentation

### 5. **Testability**

- Minimum 80% code coverage
- Unit tests for all business logic
- Integration tests for critical paths
- Load tests for performance validation

---

## � Clarifications

### Session 2025-10-17

- Q: Raspberry Pi 5 Primary Quality Profile → A: Max Performance for one concurrent user, auto-multilingual (TinyLlama 1.1B, faster-whisper multilingual base model, Piper medium voice, ~3GB RAM, ~1.5s latency, supports language auto-detection)
- Q: Session State Storage Strategy → A: In-memory only (simple dict-based storage, session lost on crash, 5-minute timeout, lowest overhead for single-user)
- Q: Critical Metrics for Phase 1 Monitoring → A: Health + Resource metrics (/health endpoint, CPU/memory/temperature monitoring for Pi 5 thermal/resource management)
- Q: Error Handling Retry Strategy → A: 3 retries with exponential backoff (2s, 4s, 8s delays, balanced for Pi 5 resource constraints and transient failures)
- Q: Integration Test Scope - Critical Paths → A: Core: Pipeline + Interruption (Full STT→LLM→TTS pipeline + user interrupt mid-generation, covers main UX, ~2-3 min test time)

---

## �🚀 Production Readiness Roadmap

### Phase 1: Foundation (Week 1-2)

**Goal**: Establish testing, monitoring, and security basics

#### 1.1 Testing Infrastructure

- [ ] Set up pytest with coverage reporting
- [ ] Add unit tests for:
  - `TurnDetection` class (pause calculation logic)
  - `TextSimilarity` and `TextContext` helpers
  - `AudioProcessor` audio processing functions
  - `TranscriptionCallbacks` state management
- [ ] Add integration tests for:
  - **Full STT → LLM → TTS pipeline** (end-to-end latency validation, target: <1.8s)
  - **User interruption handling** (mid-generation cancellation, cleanup verification)
- [ ] Target: 60% code coverage minimum

**Files to Create:**

```
tests/
  unit/
    test_turn_detection.py
    test_audio_processing.py
    test_text_utils.py
    test_callbacks.py
  integration/
    test_pipeline_e2e.py           # Full pipeline test (~1-2 min)
    test_interruption_handling.py  # User interrupt test (~30s-1 min)
  conftest.py (pytest fixtures)
```

**Note:** WebSocket connection lifecycle and reconnection tests deferred. Focus on core conversational UX for Pi 5. Can add extended tests (reconnection, error recovery) in Phase 4 if needed.

#### 1.2 Health Checks & Monitoring

- [ ] Add `/health` endpoint checking:
  - Audio processor status
  - LLM backend connectivity (llama.cpp/Ollama)
  - TTS engine availability (Piper)
  - System resources (CPU/RAM/swap)
- [ ] Add `/metrics` endpoint with resource metrics:
  - `system_memory_available_bytes` (gauge)
  - `system_cpu_temperature_celsius` (gauge) - Critical for Pi 5 throttling detection
  - `system_cpu_percent` (gauge)
  - `system_swap_usage_bytes` (gauge)
- [ ] Implement basic structured logging (JSON format)
- [ ] Add component status tracking

**Files to Create/Modify:**

- `code/health_checks.py` - Health check implementations
- `code/metrics.py` - Lightweight resource metrics (no full Prometheus stack)
- `code/monitoring/pi5_monitor.py` - Pi 5 specific resource monitoring
- `code/middleware/logging.py` - Structured logging middleware
- Modify `server.py` to add health/metrics routes

**Note:** Focus on Pi 5 resource constraints. Skip advanced metrics (latency histograms, request tracing) to minimize overhead. Add them in Phase 4 if needed.

#### 1.3 Security Basics

**For Internet-Exposed Deployments:**

- [ ] Add API key authentication for WebSocket
- [ ] Implement rate limiting (per IP/user):
  - 5 concurrent connections per IP
  - 100 messages per minute per connection
- [ ] Add input validation for JSON messages
- [ ] Use secrets manager for API keys (not env vars)

**For All Deployments (including personal/offline):**

- [ ] Input validation for JSON messages (prevent malformed data crashes)
- [ ] Sanitize user text input (prevent injection attacks on LLM)
- [ ] Error message sanitization (don't leak system paths)

**Files to Create/Modify:**

- `code/middleware/auth.py` - Authentication middleware _(optional)_
- `code/middleware/rate_limiter.py` - Rate limiting _(optional)_
- `code/security/secrets.py` - Secrets manager integration _(if using APIs)_
- `code/security/validators.py` - Input validation _(required)_
- Update `server.py` with middleware

---

### Phase 2: Refactoring (Week 3-4)

**Goal**: Improve code organization and maintainability

#### 2.1 Code Organization

**Current Issues:**

- `server.py` (883 lines) → Split into:

  - `server/app.py` (100 lines) - FastAPI app setup
  - `server/websocket_handler.py` (200 lines) - WebSocket logic
  - `server/routes.py` (50 lines) - HTTP routes
  - `callbacks/transcription_callbacks.py` (300 lines) - Callback class
  - `callbacks/audio_callbacks.py` (100 lines) - Audio-specific callbacks

- `speech_pipeline_manager.py` (700 lines) → Split into:

  - `pipeline/coordinator.py` (150 lines) - Main orchestration
  - `pipeline/workers/llm_worker.py` (200 lines) - LLM worker
  - `pipeline/workers/tts_quick_worker.py` (150 lines) - Quick TTS worker
  - `pipeline/workers/tts_final_worker.py` (150 lines) - Final TTS worker
  - `pipeline/generation_state.py` (100 lines) - State classes

- `llm_module.py` (1400 lines) → Split into:
  - `llm/base.py` (100 lines) - Base LLM interface
  - `llm/ollama.py` (300 lines) - Ollama implementation
  - `llm/openai.py` (200 lines) - OpenAI implementation
  - `llm/lmstudio.py` (150 lines) - LMStudio implementation
  - `llm/request_manager.py` (200 lines) - Request tracking/cancellation
  - `llm/metrics.py` (100 lines) - Performance measurement

**Refactoring Rules:**

- Maximum 300 lines per file
- Each class in its own file
- Clear module hierarchy
- Explicit imports (no `from x import *`)

#### 2.2 Error Handling Improvements

- [ ] Add custom exception hierarchy:
  ```python
  class RealtimeVoiceChatException(Exception): pass
  class STTException(RealtimeVoiceChatException): pass
  class LLMException(RealtimeVoiceChatException): pass
  class TTSException(RealtimeVoiceChatException): pass
  ```
- [ ] Implement retry decorators with exponential backoff:
  - 3 retry attempts maximum
  - Delays: 2s, 4s, 8s (exponential backoff)
  - Apply to: STT model loading, LLM inference, TTS generation
  - Skip retries for: user input validation errors, cancellation requests
- [ ] Add circuit breaker for LLM/TTS failures (optional for single-user)
- [ ] Graceful degradation (e.g., disable TTS if fails, continue with text)

**Files to Create:**

- `code/exceptions.py` - Custom exception classes
- `code/utils/retry.py` - Retry decorator with configurable backoff (default: 3 retries, [2s, 4s, 8s])
- `code/utils/circuit_breaker.py` - Circuit breaker implementation (optional)

#### 2.3 Configuration Management

- [ ] Replace scattered env vars with structured config
- [ ] Add config validation on startup
- [ ] Support multiple environments (dev/staging/prod)
- [ ] Add config hot-reload capability

**Files to Create:**

- `code/config/settings.py` - Pydantic settings
- `code/config/environments/` - Environment-specific configs
- `.env.example` - Template for environment variables

---

### Phase 3: Scalability (Week 5-6)

**Goal**: Enable horizontal scaling and improve performance

#### 3.1 Async/Await Migration

**Current Issue:** Heavy use of threading makes scaling difficult

- [ ] Replace threading with asyncio in:
  - `speech_pipeline_manager.py` workers
  - `llm_module.py` request handling
  - Audio processing where possible
- [ ] Use `asyncio.Queue` instead of `queue.Queue`
- [ ] Leverage async HTTP libraries (httpx) instead of requests

**Migration Strategy:**

1. Start with LLM module (least dependent)
2. Then TTS workers
3. Finally pipeline coordinator
4. Keep audio input as threads (blocking I/O with hardware)

#### 3.2 Session State Management

- [ ] Implement in-memory session management:
  - Dict-based storage for active sessions
  - 5-minute idle timeout with automatic cleanup
  - Connection state tracking per WebSocket
  - Conversation history pruning (keep last 5 turns)
- [ ] Add graceful session cleanup on disconnect
- [ ] Implement session recovery on reconnect (best-effort)

**Files to Create:**

- `code/session_manager.py` - In-memory session lifecycle management
- `code/storage/memory_store.py` - Dict-based session storage

**Note:** Redis/database persistence deferred. For single-user Pi 5, in-memory storage is sufficient and eliminates external dependencies.

#### 3.3 Performance Optimization

- [ ] Add response caching for repeated queries
- [ ] Implement model preloading pool
- [ ] Add request batching for TTS
- [ ] Optimize audio buffer management

---

### Phase 4: Operations (Week 7-8)

**Goal**: Production deployment and monitoring

#### 4.1 Deployment

- [ ] Create Kubernetes manifests:
  - Deployment with GPU node selector
  - Service + Ingress
  - ConfigMaps and Secrets
  - HorizontalPodAutoscaler
- [ ] Add CI/CD pipeline (GitHub Actions):
  - Run tests on PR
  - Build Docker images
  - Deploy to staging
  - Production deployment with approval
- [ ] Create Helm chart for easy deployment

**Files to Create:**

```
k8s/
  deployment.yaml
  service.yaml
  ingress.yaml
  configmap.yaml
  secrets.yaml
  hpa.yaml
.github/workflows/
  ci.yml
  cd-staging.yml
  cd-production.yml
helm/
  Chart.yaml
  values.yaml
  templates/
```

#### 4.2 Monitoring & Alerting

- [ ] Set up Grafana dashboards:
  - Request latency (p50, p95, p99)
  - Error rates by component
  - Active WebSocket connections
  - GPU utilization
  - Queue depths
- [ ] Configure alerts:
  - Error rate > 5%
  - Latency p95 > 2s
  - GPU memory > 90%
  - Connection drops > 10/min
- [ ] Add distributed tracing (Jaeger/Zipkin)

**Files to Create:**

- `monitoring/grafana-dashboards/` - Dashboard JSON
- `monitoring/alerts.yml` - Alert rules
- `docker-compose.monitoring.yml` - Local monitoring stack

#### 4.3 Documentation

- [ ] API documentation (OpenAPI/Swagger)
- [ ] Architecture diagrams (C4 model)
- [ ] Deployment guide
- [ ] Troubleshooting runbook
- [ ] Performance tuning guide

**Files to Create:**

- `docs/api.md` - API documentation
- `docs/architecture.md` - Architecture overview
- `docs/deployment.md` - Deployment instructions
- `docs/troubleshooting.md` - Common issues
- `docs/performance.md` - Tuning guide

---

## 📊 Success Metrics

### Code Quality

- [ ] Test coverage: ≥ 80%
- [ ] No files > 300 lines
- [ ] Pylint score: ≥ 8.0/10
- [ ] Type hints coverage: ≥ 90%

### Performance

- [ ] Time to First Response (TTFR): < 1s (p95)
- [ ] End-to-End Latency: < 2s (p95)
- [ ] Concurrent users supported: ≥ 20 per GPU
- [ ] Uptime: ≥ 99.5%

### Security

- [ ] No secrets in code/env files
- [ ] All endpoints require authentication
- [ ] Rate limiting active
- [ ] Security audit passed

### Operations

- [ ] Zero-downtime deployments
- [ ] Automated rollback on failure
- [ ] Mean Time to Recovery (MTTR): < 15 min
- [ ] Monitoring coverage: 100% of critical paths

---

## 🔧 Technical Standards

### Logging Format

```python
{
  "timestamp": "2025-10-17T10:30:45.123Z",
  "level": "INFO",
  "request_id": "req-123abc",
  "component": "llm_worker",
  "message": "Generation started",
  "metadata": {
    "model": "mistral-24b",
    "text_length": 45
  }
}
```

### Error Response Format

```json
{
  "error": {
    "code": "STT_TIMEOUT",
    "message": "Speech recognition timed out",
    "request_id": "req-123abc",
    "timestamp": "2025-10-17T10:30:45.123Z",
    "details": {}
  }
}
```

### Metrics to Track

- `websocket_connections_active` (gauge)
- `stt_latency_seconds` (histogram)
- `llm_latency_seconds` (histogram)
- `tts_latency_seconds` (histogram)
- `pipeline_errors_total` (counter by type)
- `audio_queue_depth` (gauge)
- `gpu_memory_used_bytes` (gauge)

---

## 🚨 Non-Negotiables

### Must Have Before Production (Internet-Exposed Deployments)

1. ✅ Authentication on all endpoints _(if multi-user or internet-exposed)_
2. ✅ Health checks and monitoring
3. ✅ Rate limiting _(if multi-user or internet-exposed)_
4. ✅ Comprehensive error handling
5. ✅ Test coverage ≥ 80%
6. ✅ Secrets management _(if using API keys)_
7. ✅ Structured logging
8. ✅ Load testing passed _(appropriate for deployment scale)_
9. ✅ Security audit completed _(if handling sensitive data)_
10. ✅ Disaster recovery plan documented

### Must Have for Personal/Offline Use

1. ✅ Comprehensive error handling
2. ✅ Basic health checks
3. ✅ Test coverage ≥ 60% _(lower threshold acceptable)_
4. ✅ Input validation
5. ✅ Graceful degradation
6. ✅ Clear error messages

### Nice to Have (Post-Launch)

- Multi-language support
- Voice cloning capabilities
- Custom TTS fine-tuning
- Advanced analytics dashboard
- A/B testing framework
- Mobile SDK

---

## ⚡ Edge Device & Efficiency Improvements

### Goal: Run on Raspberry Pi 5 (8GB RAM)

**Current Bottlenecks:**

- Whisper base.en model: ~1GB RAM + slow CPU inference
- Heavy Python dependencies (DeepSpeed, transformers)
- Inefficient audio processing loops
- Large LLM models requiring cloud API calls

### Phase 5: Resource Optimization (Week 9-10)

**Goal**: Reduce resource footprint by 75% while maintaining quality

#### 5.1 Speech-to-Text Optimization

**Replace RealtimeSTT with faster-whisper**

- [ ] Migrate from `openai/whisper` to `faster-whisper`
  - Uses CTranslate2 (4x faster, 50% less memory)
  - INT8 quantization support (further 2x memory reduction)
  - Better CPU optimization with SIMD instructions

**Implementation:**

```python
# Current (in transcribe.py):
from RealtimeSTT import AudioToTextRecorder

# Replace with:
from faster_whisper import WhisperModel

model = WhisperModel(
    "base.en",
    device="cpu",
    compute_type="int8",  # Quantized for speed
    cpu_threads=4,        # Optimize for Pi 5's cores
    num_workers=2         # Parallel processing
)
```

**Expected Gains:**

- Memory: 1GB → 512MB (50% reduction)
- Latency: 300ms → 100ms (3x faster)
- CPU usage: 80% → 35% (2.3x more efficient)

**Files to Modify:**

- `code/transcribe.py` - Replace STT backend
- `code/audio_in.py` - Update audio feeding logic
- `requirements.txt` - Replace `realtimestt` with `faster-whisper`

#### 5.2 Text-to-Speech Optimization

**Problem**: Coqui XTTS requires 2GB GPU memory

**Solutions:**

1. **Use Piper TTS (Recommended for Pi 5)**
   - CPU-only, optimized for edge devices
   - 50MB models (vs 2GB for Coqui)
   - Real-time on Pi 4, instant on Pi 5
   - ONNX Runtime for hardware acceleration

```python
# New audio_module.py engine:
from piper import PiperVoice

class PiperEngine:
    def __init__(self):
        self.voice = PiperVoice.load(
            "en_US-lessac-medium.onnx",
            use_cuda=False
        )

    def synthesize(self, text):
        # 10x faster than Coqui on CPU
        return self.voice.synthesize(text)
```

2. **Fallback: Kokoro with INT8 quantization**
   - Already in codebase, optimize further
   - Use ONNX Runtime with CPU acceleration
   - Enable audio chunk caching

**Expected Gains:**

- Memory: 2GB → 50-200MB (10-40x reduction)
- CPU: 60% → 15% usage
- Latency: 400ms → 80ms (5x faster)

**Files to Modify/Create:**

- `code/audio_module.py` - Add PiperEngine class
- `code/engines/piper_engine.py` - Piper implementation
- Update `requirements.txt` - Add `piper-tts`

#### 5.3 LLM Optimization

**Problem**: Cannot run large LLMs locally on 8GB RAM

**Solutions:**

1. **Use smaller quantized models with llama.cpp**

   ```python
   # Replace ollama with llama-cpp-python
   from llama_cpp import Llama

   llm = Llama(
       model_path="tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf",
       n_ctx=2048,        # Context window
       n_threads=4,       # Pi 5 cores
       n_batch=512,       # Batch size
       use_mlock=True,    # Keep model in RAM
   )
   ```

   **Model Options for Pi 5:**

   - TinyLlama 1.1B Q4: ~800MB RAM, decent quality
   - Phi-2 2.7B Q4: ~1.8GB RAM, better quality
   - Qwen 1.8B Q4: ~1.2GB RAM, best balance

2. **Streaming inference optimization**
   - Enable KV cache reuse for faster subsequent turns
   - Implement prefix caching for common prompts
   - Use flash attention (if ARM SVE available)

**Expected Gains:**

- Memory: 4-8GB → 800MB-1.8GB (4-10x reduction)
- Latency: 500ms → 200ms (2.5x faster on local)
- Cost: $0.002/request → $0 (free)

**Files to Modify/Create:**

- `code/llm/llama_cpp.py` - llama.cpp implementation
- `code/llm_module.py` - Add llama.cpp backend
- Update `requirements.txt` - Add `llama-cpp-python`

#### 5.4 Audio Processing Optimization

**Current Issues:**

- Resampling done in Python (scipy.signal)
- No SIMD optimization
- Inefficient buffer management

**Solutions:**

1. **Use librosa with numba JIT**

   ```python
   import librosa
   import numba

   @numba.jit(nopython=True)
   def fast_resample(audio, orig_sr, target_sr):
       return librosa.resample(
           audio,
           orig_sr=orig_sr,
           target_sr=target_sr,
           res_type='kaiser_fast'  # Faster algorithm
       )
   ```

2. **Use ARM NEON instructions**

   - Compile numpy with ARM optimizations
   - Use ARM Performance Libraries (if available)

3. **Optimize batching**
   ```python
   # Increase batch size to reduce overhead
   const BATCH_SAMPLES = 4096;  # Was 2048
   ```

**Expected Gains:**

- CPU: 15% → 8% usage
- Latency: 50ms → 20ms per batch

**Files to Modify:**

- `code/audio_in.py` - Optimize resampling
- `code/static/app.js` - Increase batch size
- Add `code/utils/audio_simd.py` - SIMD helpers

#### 5.5 Memory Management

**Current Issues:**

- Models loaded redundantly
- No memory pooling
- Large conversation histories

**Solutions:**

1. **Model quantization and sharing**

   ```python
   # Shared model instances
   from contextlib import contextmanager

   class ModelPool:
       _models = {}

       @classmethod
       @contextmanager
       def get_model(cls, name):
           if name not in cls._models:
               cls._models[name] = load_model(name)
           yield cls._models[name]
   ```

2. **Conversation history pruning**

   ```python
   # Keep only last N turns + system prompt
   MAX_HISTORY_TURNS = 5

   def prune_history(history):
       if len(history) > MAX_HISTORY_TURNS * 2:
           # Keep system + last N turns
           return [history[0]] + history[-(MAX_HISTORY_TURNS*2):]
       return history
   ```

3. **Swap to disk for inactive sessions**
   - Use mmap for model weights
   - Implement LRU eviction policy

**Expected Gains:**

- Memory: 6-8GB → 3-4GB baseline usage
- Session capacity: 1-2 → 5-10 concurrent users

**Files to Create:**

- `code/utils/model_pool.py` - Model management
- `code/utils/memory_manager.py` - Memory optimization

#### 5.6 System-Level Optimizations

**Operating System Tweaks:**

```bash
# /boot/config.txt for Pi 5
# Increase GPU memory for potential HW acceleration
gpu_mem=256

# Enable ARM performance mode
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# Increase swap for safety
sudo dphys-swapfile swapoff
sudo sed -i 's/CONF_SWAPSIZE=100/CONF_SWAPSIZE=2048/' /etc/dphys-swapfile
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

**Docker Optimizations:**

```dockerfile
# Dockerfile.pi5
FROM arm64v8/ubuntu:22.04

# Use multi-stage build to reduce image size
# Install only runtime dependencies
RUN apt-get install --no-install-recommends \
    python3.11 \
    libgomp1 \
    libopenblas0

# Pre-compile Python files
RUN python -m compileall /app/code

# Use jemalloc for better memory allocation
ENV LD_PRELOAD=/usr/lib/aarch64-linux-gnu/libjemalloc.so.2
```

**Expected Gains:**

- Docker image: 8GB → 2GB (4x smaller)
- Startup time: 60s → 15s (4x faster)
- Memory overhead: 500MB → 150MB

**Files to Create:**

- `Dockerfile.pi5` - ARM-optimized Dockerfile
- `docker-compose.pi5.yml` - Pi 5 specific config
- `docs/raspberry-pi-setup.md` - Setup guide

#### 5.7 Benchmark Targets for Raspberry Pi 5

| Metric               | Current (x86 GPU) | Target (Pi 5) | Max Acceptable |
| -------------------- | ----------------- | ------------- | -------------- |
| **Total RAM Usage**  | 8-12GB            | 3-4GB         | 6GB            |
| **STT Latency**      | 100-300ms         | 150-250ms     | 400ms          |
| **LLM Latency**      | 200-500ms         | 300-800ms     | 1200ms         |
| **TTS Latency**      | 200-400ms         | 200-500ms     | 800ms          |
| **Total TTFR**       | 500-1200ms        | 800-1800ms    | 2500ms         |
| **Concurrent Users** | 20+               | 2-3           | 5              |
| **Idle CPU**         | 5%                | 15%           | 30%            |
| **Active CPU**       | 60-80%            | 70-90%        | 95%            |

#### 5.8 Implementation Checklist

**Week 9: Core Optimizations**

- [ ] Replace RealtimeSTT with faster-whisper (INT8, multilingual base model with auto-detection)
- [ ] Add Piper TTS engine support (medium voice quality)
- [ ] Implement llama.cpp backend with TinyLlama 1.1B Q4
- [ ] Optimize audio resampling with numba
- [ ] Add model pooling and memory management (single-user optimized)
- [ ] Create ARM-specific Dockerfile (Dockerfile.pi5)
- [ ] Configure for max performance profile (1 concurrent user)
- [ ] Test on actual Pi 5 hardware with multilingual input

**Week 10: Testing & Documentation**

- [ ] Load test with 3 concurrent users
- [ ] Measure memory usage under load
- [ ] Profile CPU bottlenecks
- [ ] Create Pi 5 setup documentation
- [ ] Add performance tuning guide
- [ ] Create fallback strategies for edge cases
- [ ] Document model quality vs. speed tradeoffs

#### 5.9 Quality vs. Performance Tradeoffs

**User Configuration Profiles:**

1. **Max Performance (Pi 5 PRIMARY TARGET)** ⭐

   ```yaml
   stt:
     model: faster-whisper-base-int8 # Multilingual auto-detection
     device: cpu
     language: auto # Auto-detect language
   llm:
     backend: llama-cpp
     model: tinyllama-1.1b-q4
   tts:
     engine: piper
     voice: lessac-medium
   quality: Good
   latency: ~1.5s
   ram: ~3GB
   max_concurrent_users: 1 # Optimized for single user
   multilingual: true # Supports auto language detection
   ```

2. **Balanced**

   ```yaml
   stt:
     model: faster-whisper-small.en-int8
   llm:
     model: phi-2-2.7b-q4
   tts:
     engine: piper
     voice: lessac-high
   quality: Better
   latency: ~2.5s
   ram: ~4.5GB
   ```

3. **Quality First (Requires cloud)**
   ```yaml
   stt:
     model: faster-whisper-base.en
   llm:
     backend: openai
     model: gpt-4o-mini
   tts:
     engine: piper
     voice: lessac-high
   quality: Best
   latency: ~2s
   ram: ~2GB
   cost: ~$0.001/turn
   ```

**Files to Create:**

- `code/config/profiles/pi5_performance.yaml`
- `code/config/profiles/pi5_balanced.yaml`
- `code/config/profiles/pi5_quality.yaml`

#### 5.10 Monitoring for Resource-Constrained Devices

**Additional Metrics:**

- `system_memory_available_bytes` (gauge)
- `system_cpu_temperature_celsius` (gauge)
- `model_inference_memory_bytes` (histogram)
- `audio_processing_cpu_percent` (gauge)
- `swap_usage_bytes` (gauge)

**Auto-scaling Logic:**

```python
# Graceful degradation
if system_memory < 1_000_000_000:  # < 1GB free
    # Switch to smallest models
    switch_to_profile("minimal")

if cpu_temp > 75:  # Pi 5 throttles at 80°C
    # Reduce concurrent processing
    reduce_batch_sizes()

if swap_usage > 500_000_000:  # > 500MB swap
    # Clear caches, prune history aggressively
    emergency_memory_cleanup()
```

**Files to Create:**

- `code/monitoring/resource_monitor.py`
- `code/utils/auto_scaler.py`

---

## 📝 Implementation Notes

### File Organization Standards

```
code/
  server/
    app.py
    websocket_handler.py
    routes.py
  pipeline/
    coordinator.py
    workers/
      llm_worker.py
      tts_quick_worker.py
      tts_final_worker.py
    generation_state.py
  llm/
    base.py
    ollama.py
    openai.py
    lmstudio.py
    request_manager.py
  callbacks/
    transcription_callbacks.py
    audio_callbacks.py
  middleware/
    auth.py
    rate_limiter.py
    logging_middleware.py
  utils/
    retry.py
    circuit_breaker.py
  config/
    settings.py
  storage/
    redis_store.py
    database.py
  exceptions.py
  health_checks.py
  metrics.py
```

### Dependency Management

- Pin all versions in `requirements.txt`
- Separate `requirements-dev.txt` for test tools
- Use `pip-compile` to lock transitive dependencies
- Regular security audits with `safety` and `bandit`

### Git Workflow

- Feature branches from `main`
- PR required for all changes
- Minimum 1 approval required
- All tests must pass
- No direct commits to `main`
- Semantic versioning for releases

---

## 🔌 Offline Operation Guide

### Can RealtimeVoiceChat Run Fully Offline?

**YES** ✅ - The system is designed to run **100% offline** with the default configuration.

#### Component Offline Status

| Component              | Offline? | Storage    | Notes                |
| ---------------------- | -------- | ---------- | -------------------- |
| **STT (Whisper)**      | ✅ YES   | ~140MB-1GB | Downloads once       |
| **LLM (Ollama)**       | ✅ YES   | ~4-12GB    | Default, fully local |
| **TTS (Coqui/Kokoro)** | ✅ YES   | ~500MB-2GB | All local            |
| **Turn Detection**     | ✅ YES   | ~250MB     | HuggingFace cached   |
| **VAD (Silero)**       | ✅ YES   | ~2MB       | PyTorch Hub cached   |
| **OpenAI (optional)**  | ❌ NO    | 0MB        | Cloud-only option    |

#### One-Time Setup (Requires Internet)

```bash
# 1. Pull Docker images and start
docker compose pull && docker compose up -d

# 2. Pull LLM model
docker compose exec ollama ollama pull hf.co/bartowski/huihui-ai_Mistral-Small-24B-Instruct-2501-abliterated-GGUF:Q4_K_M

# 3. Verify (models download automatically on first run)
curl http://localhost:8000/health

# 4. NOW DISCONNECT FROM INTERNET! 🎉
```

**Total offline storage: ~5-14GB** depending on model choices.

#### Raspberry Pi 5 Offline Bundle

**Optimized for 8GB RAM (only ~3.25GB needed):**

- faster-whisper base: 140MB
- TinyLlama 1.1B: 800MB
- Piper TTS: 50MB
- Supporting models: 250MB
- Docker images: 2GB

#### Creating Offline Bundle

```bash
# scripts/create-offline-bundle.sh
docker compose pull && docker compose up -d
# ... download all models ...
docker save realtime-voice-chat ollama/ollama | gzip > offline-bundle.tar.gz
# Export volumes: ollama_data, huggingface_cache, torch_cache
```

#### Benefits of Offline Operation

1. **Privacy** 🔒 - No data leaves device, GDPR/HIPAA compliant
2. **Cost** 💰 - Zero API fees, one-time hardware only
3. **Reliability** 🛡️ - No internet dependency, no rate limits
4. **Speed** ⚡ - No network latency, consistent performance
5. **Security** 🔐 - Air-gapped deployment possible

#### Verifying Offline

```bash
# Disconnect network
sudo nmcli networking off

# Test
curl http://localhost:8000/health
# Should work! ✅

# Reconnect
sudo nmcli networking on
```

---

## 🚀 Deployment Scenarios & Requirements

### Scenario 1: Personal/Home Use (Raspberry Pi 5) 🏠

**Use Case:** Single user, local network, offline operation

**Requirements:**

- ❌ Authentication: **NOT NEEDED**
- ❌ Rate limiting: **NOT NEEDED**
- ❌ Monitoring: **OPTIONAL** (nice for debugging)
- ✅ Input validation: **BASIC** (prevent crashes)
- ✅ Error handling: **REQUIRED**
- ✅ Offline capability: **REQUIRED**

**Configuration:**

```yaml
# config/personal.yaml
deployment_mode: personal
auth_enabled: false
rate_limiting_enabled: false
allow_public_access: false
bind_address: 127.0.0.1 # localhost only
offline_mode: true
```

**Security Posture:** Physical security is sufficient. Device should be behind home router/firewall.

---

### Scenario 2: Small Team/Lab (Local Network) 🧪

**Use Case:** 3-5 users, trusted local network, shared resource

**Requirements:**

- ⚠️ Authentication: **OPTIONAL** (simple API key)
- ⚠️ Rate limiting: **OPTIONAL** (prevent one user hogging resources)
- ✅ Monitoring: **RECOMMENDED** (track usage)
- ✅ Input validation: **REQUIRED**
- ✅ Error handling: **REQUIRED**
- ⚠️ Offline capable: **OPTIONAL**

**Configuration:**

```yaml
# config/team.yaml
deployment_mode: team
auth_enabled: true
auth_type: simple_api_key # Not OAuth, just shared key
rate_limiting_enabled: true
max_concurrent_users: 5
bind_address: 0.0.0.0 # Accept LAN connections
offline_mode: true
```

**Security Posture:** Shared API key, network segmentation, basic logging.

---

### Scenario 3: Public Demo/Research (Internet) 🌐

**Use Case:** Public demo, research project, limited internet access

**Requirements:**

- ✅ Authentication: **REQUIRED** (prevent abuse)
- ✅ Rate limiting: **REQUIRED** (aggressive limits)
- ✅ Monitoring: **REQUIRED**
- ✅ Input validation: **STRICT**
- ✅ Error handling: **REQUIRED**
- ✅ CAPTCHA/Bot protection: **RECOMMENDED**

**Configuration:**

```yaml
# config/public.yaml
deployment_mode: public
auth_enabled: true
auth_type: api_key_per_user
rate_limiting_enabled: true
max_requests_per_minute: 10
max_concurrent_connections: 50
bind_address: 0.0.0.0
offline_mode: false # May use cloud LLMs
captcha_enabled: true
session_timeout: 300 # 5 minutes
```

**Security Posture:** Full authentication, aggressive rate limiting, DDoS protection, monitoring/alerting.

---

### Scenario 4: Enterprise/Production SaaS 🏢

**Use Case:** Multi-tenant commercial service, compliance required

**Requirements:**

- ✅ Authentication: **REQUIRED** (OAuth2/SSO)
- ✅ Authorization: **REQUIRED** (per-user/org data isolation)
- ✅ Rate limiting: **REQUIRED** (tiered by plan)
- ✅ Monitoring: **REQUIRED** (full observability)
- ✅ Audit logging: **REQUIRED** (compliance)
- ✅ Encryption: **REQUIRED** (at rest + in transit)
- ✅ Backup/DR: **REQUIRED**

**Configuration:**

```yaml
# config/production.yaml
deployment_mode: production
auth_enabled: true
auth_type: oauth2
authorization_enabled: true
rate_limiting_enabled: true
rate_limit_tier_based: true
encryption_at_rest: true
ssl_required: true
audit_logging: true
gdpr_compliant: true
data_retention_days: 90
```

**Security Posture:** Enterprise-grade security, compliance certifications, 24/7 monitoring, SOC 2/HIPAA compliance.

---

### Quick Decision Matrix

| Feature              | Personal    | Team           | Public      | Enterprise  |
| -------------------- | ----------- | -------------- | ----------- | ----------- |
| **Authentication**   | ❌          | ⚠️ Optional    | ✅ Required | ✅ Required |
| **Rate Limiting**    | ❌          | ⚠️ Optional    | ✅ Required | ✅ Required |
| **Monitoring**       | ⚠️ Optional | ✅ Recommended | ✅ Required | ✅ Required |
| **SSL/HTTPS**        | ❌          | ⚠️ Optional    | ✅ Required | ✅ Required |
| **Audit Logs**       | ❌          | ❌             | ⚠️ Optional | ✅ Required |
| **Input Validation** | ✅ Basic    | ✅ Required    | ✅ Strict   | ✅ Strict   |
| **Test Coverage**    | 60%         | 70%            | 80%         | 90%         |
| **Max Users**        | 1           | 3-5            | 50-100      | 1000+       |
| **Offline Capable**  | ✅ Yes      | ✅ Yes         | ⚠️ Optional | ❌ No       |

---

### Environment Variable Examples

**Personal/Home (.env.personal):**

```bash
DEPLOYMENT_MODE=personal
AUTH_ENABLED=false
RATE_LIMITING_ENABLED=false
BIND_ADDRESS=127.0.0.1
OFFLINE_MODE=true
LOG_LEVEL=INFO
```

**Public Demo (.env.public):**

```bash
DEPLOYMENT_MODE=public
AUTH_ENABLED=true
API_KEY=your-secret-key-here
RATE_LIMITING_ENABLED=true
MAX_REQUESTS_PER_MINUTE=10
BIND_ADDRESS=0.0.0.0
OFFLINE_MODE=false
LOG_LEVEL=WARNING
CAPTCHA_ENABLED=true
```

**Enterprise (.env.production):**

```bash
DEPLOYMENT_MODE=production
AUTH_ENABLED=true
AUTH_TYPE=oauth2
OAUTH_PROVIDER=auth0
RATE_LIMITING_ENABLED=true
ENCRYPTION_ENABLED=true
SSL_CERT_PATH=/etc/ssl/certs/app.crt
SSL_KEY_PATH=/etc/ssl/private/app.key
AUDIT_LOGGING=true
LOG_LEVEL=INFO
SENTRY_DSN=https://your-sentry-dsn
```

---

## 🎓 Learning Resources

For team members working on this project:

- [FastAPI Best Practices](https://fastapi.tiangolo.com/tutorial/)
- [asyncio Documentation](https://docs.python.org/3/library/asyncio.html)
- [Prometheus Metrics](https://prometheus.io/docs/practices/naming/)
- [12-Factor App Methodology](https://12factor.net/)
- [Clean Architecture in Python](https://www.cosmicpython.com/)

---

## 📞 Escalation Path

For production issues:

1. Check `/health` endpoint
2. Review logs in monitoring dashboard
3. Check Grafana alerts
4. Consult troubleshooting runbook
5. If unresolved: Page on-call engineer

---

## ✅ Definition of Done

A task is complete when:

- [ ] Code written and reviewed
- [ ] Unit tests added (coverage ≥ 80%)
- [ ] Integration tests pass
- [ ] Documentation updated
- [ ] No linting errors
- [ ] Security review passed
- [ ] Performance benchmarks met
- [ ] Deployed to staging and validated
- [ ] Monitoring/alerts configured

---

**Version**: 1.0  
**Last Updated**: October 17, 2025  
**Owner**: Engineering Team  
**Review Cycle**: Monthly
