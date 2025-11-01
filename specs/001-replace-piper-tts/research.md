# Research Findings: Piper TTS Integration

**Feature**: Replace RealtimeTTS with Piper TTS  
**Date**: November 1, 2025  
**Research Phase**: Complete

## Research Tasks Completed

### 1. Piper TTS Integration Requirements

**Decision**: Use piper-tts Python library with ONNX runtime backend  
**Rationale**:

- Native Python bindings available via `piper-tts` package
- ONNX runtime provides CPU optimization suitable for Pi 5
- Supports streaming audio generation required for real-time chat
- Models are offline-first (~50MB per voice)

**Alternatives considered**:

- Direct ONNX runtime integration (more complex, reinventing API layer)
- Festival/eSpeak (lower quality, limited voice options)
- Mozilla TTS (deprecated, heavier resource usage)

### 2. Voice Model Selection Strategy

**Decision**: Bundle 3 high-quality English voices: en_US-lessac-medium, en_US-amy-medium, en_GB-alan-medium  
**Rationale**:

- Covers US/UK English variants for user preference
- Medium quality balances file size (~50MB each) vs audio quality
- Lessac and Amy provide gender diversity
- Alan provides accent diversity (British English)

**Alternatives considered**:

- Low quality models (faster but noticeably worse audio)
- High quality models (better audio but 150MB+ each, Pi 5 memory constraints)
- Multilingual support (adds complexity, current system is English-focused)

### 3. Streaming Audio Implementation

**Decision**: Use Piper's built-in streaming with chunk-based audio delivery matching RealtimeTTS interface  
**Rationale**:

- Piper supports streaming synthesis (generates audio while processing text)
- Can maintain existing audio pipeline expectations
- Compatible with WebSocket real-time delivery requirements
- Preserves <2 second latency target

**Alternatives considered**:

- Full synthesis then playback (higher latency, fails streaming requirement)
- Custom streaming implementation (complex, reinventing tested functionality)

### 4. Configuration Migration Strategy

**Decision**: Create voice profile mapping from RealtimeTTS engines to Piper voices with backward compatibility  
**Rationale**:

- Users with saved "coqui"/"kokoro"/"orpheus" preferences get mapped to equivalent Piper voices
- New installations default to best general-purpose voice (lessac-medium)
- Maintains existing configuration file structure where possible

**Configuration Mapping**:

```yaml
voice_migration:
  coqui: "en_US-lessac-medium" # Closest quality match
  kokoro: "en_US-amy-medium" # Alternative voice option
  orpheus: "en_GB-alan-medium" # Accent variety
  default: "en_US-lessac-medium" # New installation default
```

### 5. Performance Optimization for Pi 5

**Decision**: Use ONNX CPU provider with thread optimization and model caching  
**Rationale**:

- Pi 5 ARM Cortex-A76 CPU supports efficient ONNX inference
- Model loading can be done once at startup (100-200ms overhead)
- Thread count optimization for quad-core Pi 5
- Memory-mapped models reduce startup time

**Pi 5 Specific Optimizations**:

- Set ONNX thread count to 3 (leave 1 core for system)
- Pre-load all 3 voice models at startup
- Use memory mapping to reduce model load time
- Implement model switching without reload when possible

### 6. Error Handling and Fallback Strategy

**Decision**: Graceful degradation with text-only fallback when TTS fails  
**Rationale**:

- Critical that voice chat continues functioning even if TTS fails
- Users can still receive text responses if audio generation fails
- Maintains system availability per constitution reliability principle

**Fallback Hierarchy**:

1. Primary Piper voice synthesis
2. Alternative Piper voice (if model corrupted)
3. System notification of TTS failure + text-only response
4. Log failure details for debugging

### 7. Testing Strategy

**Decision**: Comprehensive unit tests for Piper integration + existing integration test framework  
**Rationale**:

- Unit tests verify Piper library integration and voice switching
- Integration tests ensure end-to-end pipeline compatibility
- Performance tests validate latency requirements on Pi 5

**Test Coverage Plan**:

- Voice model loading and initialization
- Text-to-audio conversion with different voice profiles
- Streaming audio chunk generation
- Error handling and fallback scenarios
- Memory usage and performance benchmarks
- Configuration migration from RealtimeTTS settings

## Implementation Dependencies

### Required Packages

```
piper-tts>=1.2.0          # Main Piper TTS library
onnxruntime>=1.16.0        # ONNX inference runtime
numpy>=1.24.0              # Audio data processing
aiofiles>=23.0.0          # Async model file loading
```

### Voice Model Downloads

- Models downloaded during Docker build or first startup
- Stored in `src/models/piper/` directory
- Total download size: ~150MB for 3 voices
- Download source: Hugging Face piper-tts model repository

### Configuration Changes

- Update `requirements.txt` to remove RealtimeTTS dependencies
- Add Piper-specific configuration section to settings
- Migrate existing voice preference mappings
- Update Docker build to include model downloads

## Risk Mitigation

### Identified Risks:

1. **Voice quality regression**: Piper voices may sound different than current RealtimeTTS engines

   - **Mitigation**: Provide voice samples for user testing, allow easy switching between voices

2. **Pi 5 performance impact**: Multiple models may consume too much memory

   - **Mitigation**: Implement lazy loading, monitor memory usage, provide single-voice deployment option

3. **Migration complexity**: Existing deployments may break during transition

   - **Mitigation**: Maintain fallback to simple TTS, provide clear migration guide, test on existing installations

4. **Model download failures**: Network issues during model download
   - **Mitigation**: Bundle models in Docker image, provide retry logic with exponential backoff

## Ready for Implementation

All technical research complete. No remaining [NEEDS CLARIFICATION] items. Ready to proceed to Phase 1 design and contracts generation.
