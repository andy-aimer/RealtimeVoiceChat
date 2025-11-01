# Implementation Plan: Replace RealtimeTTS with Piper TTS

**Branch**: `001-replace-piper-tts` | **Date**: November 1, 2025 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-replace-piper-tts/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Replace the current RealtimeTTS engines (Coqui, Kokoro, Orpheus) with Piper TTS as the primary text-to-speech provider. This migration aims to reduce dependencies, improve system reliability, and maintain offline-first architecture while preserving voice quality and streaming capabilities.

## Technical Context

**Language/Version**: Python 3.12  
**Primary Dependencies**: FastAPI, uvicorn, Piper TTS (ONNX runtime), numpy, asyncio  
**Storage**: Configuration files (JSON/YAML), in-memory voice profiles cache  
**Testing**: pytest, pytest-asyncio, pytest-cov (existing test framework)  
**Target Platform**: Linux (Docker), Raspberry Pi 5 ARM64, macOS/Windows development
**Project Type**: Single application (real-time voice chat system)  
**Performance Goals**: <2s TTS generation for <200 char messages, maintain existing latency expectations  
**Constraints**: Offline-capable, <100MB additional memory usage, Pi 5 compatible, maintain streaming audio  
**Scale/Scope**: Single-user focused, 3 minimum voice options, existing audio pipeline compatibility

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

### ✅ Principle 0: Offline-First Architecture (PRIMARY)

- **Status**: PASS - Piper TTS runs 100% offline with local ONNX models
- **Verification**: No cloud API dependencies, models cached locally after download

### ✅ Principle 1: Reliability First

- **Status**: PASS - Plan includes graceful failure handling and fallbacks
- **Verification**: FR-006 requires graceful TTS failures, logging and retry mechanisms planned

### ✅ Principle 2: Observability (Edge-Optimized)

- **Status**: PASS - Metrics logging planned for Pi 5 deployment
- **Verification**: FR-010 requires TTS processing metrics, aligns with resource monitoring

### ✅ Principle 4: Maintainability

- **Status**: PASS - Maintains existing API interface, modular replacement approach
- **Verification**: FR-003 preserves current interface, limiting scope to TTS engine only

### ✅ Principle 5: Testability

- **Status**: PASS - Existing test framework maintained, clear acceptance scenarios
- **Verification**: Pytest framework continues, independent test scenarios defined per user story

### Performance Targets Compliance (Pi 5)

- **TTS Latency**: Target 200-500ms ≤ 800ms max ✅
- **Memory**: Piper models ~50MB each, fits within constraints ✅
- **Total TTFR**: Current <2s target maintained ✅

## Project Structure

### Documentation (this feature)

```
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```
src/
├── audio_module.py         # TTS engine interface and Piper integration
├── tts_simple.py          # Existing fallback TTS (maintained)
├── server.py              # FastAPI application (minimal changes)
├── middleware/            # Logging and configuration
├── config/                # Voice profiles and Piper settings
└── models/                # Downloaded Piper ONNX models

tests/
├── unit/                  # TTS engine unit tests
│   ├── test_piper_integration.py
│   └── test_audio_module.py
└── integration/           # End-to-end voice pipeline tests
    └── test_tts_pipeline.py

requirements.txt           # Remove RealtimeTTS, add Piper dependencies
requirements.production.txt # Updated production dependencies
```

**Structure Decision**: Single project structure selected. This is a focused TTS engine replacement within the existing RealtimeVoiceChat application. Primary changes concentrated in `src/audio_module.py` with configuration updates and new model storage directory.

## Complexity Tracking

_Fill ONLY if Constitution Check has violations that must be justified_

| Violation                  | Why Needed         | Simpler Alternative Rejected Because |
| -------------------------- | ------------------ | ------------------------------------ |
| [e.g., 4th project]        | [current need]     | [why 3 projects insufficient]        |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient]  |
