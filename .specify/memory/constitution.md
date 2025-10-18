<!--
SYNC IMPACT REPORT:
Version: 0.0.0 → 1.0.0
Added Principles:
- 0. Offline-First Architecture
- 1. Reliability First
- 2. Observability
- 3. Security (deployment-dependent)
- 4. Maintainability
- 5. Testability
Added Sections:
- Design Decisions (Clarifications)
- Implementation Standards
Templates Status:
- ⚠ .specify/templates/plan-template.md: Pending manual review
- ⚠ .specify/templates/spec-template.md: Pending manual review
- ⚠ .specify/templates/tasks-template.md: Pending manual review
Ratification Date: Set to 2025-10-17 (constitution creation date)
-->

# RealtimeVoiceChat Constitution

Transform RealtimeVoiceChat from a research-quality demo into a production-ready, scalable, and maintainable real-time AI voice conversation platform optimized for edge devices (Raspberry Pi 5) and personal/offline use.

## Core Principles

### 0. Offline-First Architecture (PRIMARY)

**System MUST run 100% offline by default** with the Ollama backend. All models downloaded once and cached locally. No cloud API calls required for core functionality. Optional cloud backends (OpenAI) for enhanced quality only.

**Rationale:** Privacy, cost elimination, reliability without internet dependency, air-gapped deployment capability, GDPR/HIPAA compliance by design.

### 1. Reliability First

**All components MUST gracefully handle failures.** No silent errors - log everything with context. Implement circuit breakers for external dependencies. Add health checks for all critical services.

**Error handling strategy:** 3 retries with exponential backoff (2s, 4s, 8s) for transient failures (STT/LLM/TTS). Skip retries for validation errors or user cancellations.

**Rationale:** System must be dependable for single-user personal deployment where no operator is monitoring.

### 2. Observability (Edge-Optimized)

**For Pi 5 deployments:** Health checks + resource metrics ONLY (CPU/memory/temperature). Structured JSON logging. Component status tracking.

**For production deployments:** Add comprehensive metrics (latency histograms, throughput), request tracing, performance profiling.

**Rationale:** Minimize overhead on resource-constrained devices while maintaining debuggability.

### 3. Security (Deployment-Dependent)

**Personal/offline use:** Authentication NOT NEEDED. Basic input validation REQUIRED (prevent crashes). Error sanitization REQUIRED (no path leaks).

**Internet-exposed/multi-user:** Authentication REQUIRED. Rate limiting REQUIRED. Strict input validation. Secrets management (no hardcoded keys).

**Rationale:** Security requirements scale with deployment risk. Personal localhost deployments don't need enterprise-grade auth overhead.

### 4. Maintainability

**Single Responsibility Principle** - one file, one concern. Maximum 300 lines per file. Each class in its own file. Clear module hierarchy. Explicit imports (no `from x import *`). Comprehensive documentation.

**Rationale:** Long files (883, 700, 1400 lines) impede understanding and modification. Strict limits enforce modular design.

### 5. Testability

**Personal/offline deployment:** 60% code coverage minimum. Focus on unit tests (business logic) + integration tests (pipeline + interruption).

**Production deployment:** 80% code coverage. Add load tests, extended integration tests (reconnection, error recovery).

**Critical paths:** STT→LLM→TTS pipeline (end-to-end latency <1.8s), user interruption handling (mid-generation cancellation).

**Rationale:** Test coverage proportional to deployment criticality. Personal use tolerates lower coverage.

## Design Decisions (Clarifications - Session 2025-10-17)

These decisions were clarified through structured ambiguity resolution:

1. **Pi 5 Target Profile:** Max Performance for one concurrent user, auto-multilingual (TinyLlama 1.1B, faster-whisper multilingual base INT8, Piper medium voice, ~3GB RAM, ~1.5s latency)

2. **Session Storage:** In-memory only (dict-based, 5-min timeout, no Redis/DB overhead)

3. **Monitoring Scope:** Health + resource metrics (CPU/temp/memory/swap monitoring for Pi 5 thermal management)

4. **Retry Strategy:** 3 attempts, exponential backoff (2s/4s/8s), applied to model loading and inference, skipped for user errors

5. **Integration Test Scope:** Core paths only (full pipeline + interruption handling, ~2-3 min test time)

## Implementation Standards

### File Organization

```
code/
  server/           # FastAPI app, WebSocket handler, routes (<300 lines each)
  pipeline/         # Coordinator, workers (LLM, TTS), state classes
  llm/              # Base interface, Ollama/OpenAI/LMStudio/llama.cpp implementations
  callbacks/        # Transcription and audio callbacks
  middleware/       # Auth (optional), rate limiting (optional), logging
  utils/            # Retry decorators, circuit breakers, memory management
  config/           # Pydantic settings, environment configs, profiles
  storage/          # In-memory session store
  security/         # Input validators (required), secrets (optional)
  monitoring/       # Pi 5 resource monitor, health checks, metrics
  exceptions.py     # Custom exception hierarchy
  health_checks.py
  metrics.py
```

### Technology Constraints

- Python 3.10+
- FastAPI for server
- faster-whisper (INT8) for STT (replaces RealtimeSTT)
- llama.cpp for LLM (replaces heavy Ollama for Pi 5)
- Piper TTS (ONNX, 50MB models, CPU-optimized)
- In-memory dict storage (no external databases)
- Docker with ARM64 support (Dockerfile.pi5)

### Performance Targets (Raspberry Pi 5)

| Metric           | Target        | Max Acceptable        |
| ---------------- | ------------- | --------------------- |
| Total RAM        | 3-4GB         | 6GB                   |
| STT Latency      | 150-250ms     | 400ms                 |
| LLM Latency      | 300-800ms     | 1200ms                |
| TTS Latency      | 200-500ms     | 800ms                 |
| Total TTFR       | 800-1800ms    | 2500ms                |
| CPU Temp         | <75°C         | 80°C (throttle point) |
| Concurrent Users | 1 (optimized) | 3 (degraded)          |

## Governance

This constitution supersedes ad-hoc coding practices. All pull requests and code reviews MUST verify compliance with core principles.

**Amendment Process:**

- MINOR version bump: New principle or materially expanded guidance
- PATCH version bump: Clarifications, wording fixes, non-semantic refinements
- MAJOR version bump: Backward-incompatible changes, principle removal/redefinition

**Compliance Review:** Before each phase completion (Phases 1-5), verify all deliverables align with principles. For personal/offline deployment, principles 0, 1, 4, 5 are NON-NEGOTIABLE.

**Deployment-Specific Overrides:** Principle 3 (Security) and Principle 2 (Observability) scale with deployment scenario (Personal/Team/Public/Enterprise as defined in `.specify/CONSTITUTION.md`).

**Version**: 1.0.0 | **Ratified**: 2025-10-17 | **Last Amended**: 2025-10-17
