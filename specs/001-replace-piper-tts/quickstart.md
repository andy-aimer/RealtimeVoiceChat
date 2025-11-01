# Quick Start Guide: Piper TTS Integration

**Feature**: Replace RealtimeTTS with Piper TTS  
**Date**: November 1, 2025  
**Audience**: Developers implementing the Piper TTS integration

## Overview

This guide provides step-by-step instructions for implementing Piper TTS as a replacement for RealtimeTTS engines (Coqui, Kokoro, Orpheus) in the RealtimeVoiceChat application.

## Prerequisites

- Python 3.12+ environment
- Existing RealtimeVoiceChat codebase
- ~500MB disk space for voice models
- Internet connection for initial model downloads

## Installation Steps

### 1. Update Dependencies

**Remove RealtimeTTS dependencies:**

```bash
# Edit requirements.txt
# Remove: realtimetts[kokoro,coqui,orpheus]==0.5.5

# Add Piper TTS dependencies:
pip install piper-tts>=1.2.0
pip install onnxruntime>=1.16.0
pip install aiofiles>=23.0.0
```

**Update requirements.txt:**

```txt
# Replace RealtimeTTS line with:
piper-tts>=1.2.0
onnxruntime>=1.16.0
aiofiles>=23.0.0
```

### 2. Download Voice Models

**Create model directory:**

```bash
mkdir -p src/models/piper
```

**Download required voices:**

```bash
# US English (Lessac) - Default voice
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json

# US English (Amy) - Alternative voice
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx.json

# British English (Alan) - Accent variety
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/alan/medium/en_GB-alan-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/alan/medium/en_GB-alan-medium.onnx.json
```

### 3. Update Audio Module

**Modify `src/audio_module.py`:**

Replace RealtimeTTS imports:

```python
# OLD - Remove these imports
from RealtimeTTS import (CoquiEngine, KokoroEngine, OrpheusEngine,
                         OrpheusVoice, TextToAudioStream)

# NEW - Add Piper imports
import piper
import onnxruntime
from typing import Dict, Optional
import asyncio
import numpy as np
```

**Add Piper TTS integration class:**

```python
class PiperTTSEngine:
    """Piper TTS engine integration"""

    def __init__(self, model_path: str = "src/models/piper"):
        self.model_path = model_path
        self.voices: Dict[str, piper.PiperVoice] = {}
        self.current_voice = None

    async def initialize(self):
        """Load available voice models"""
        voice_configs = {
            "en_US-lessac-medium": "US English (Lessac)",
            "en_US-amy-medium": "US English (Amy)",
            "en_GB-alan-medium": "British English (Alan)"
        }

        for voice_id, display_name in voice_configs.items():
            model_file = f"{self.model_path}/{voice_id}.onnx"
            config_file = f"{self.model_path}/{voice_id}.onnx.json"

            try:
                voice = piper.PiperVoice.load(model_file, config_file)
                self.voices[voice_id] = voice
                logger.info(f"Loaded voice: {display_name}")
            except Exception as e:
                logger.error(f"Failed to load voice {voice_id}: {e}")

        # Set default voice
        self.current_voice = self.voices.get("en_US-lessac-medium")

    def synthesize(self, text: str, voice_id: str = None) -> bytes:
        """Synthesize text to audio"""
        voice = self.voices.get(voice_id) or self.current_voice
        if not voice:
            raise ValueError("No voice available for synthesis")

        # Generate audio
        audio_bytes = voice.synthesize(text)
        return audio_bytes

    async def synthesize_streaming(self, text: str, voice_id: str = None):
        """Generate streaming audio chunks"""
        voice = self.voices.get(voice_id) or self.current_voice
        if not voice:
            raise ValueError("No voice available for synthesis")

        # Stream audio generation
        for audio_chunk in voice.synthesize_stream(text):
            yield audio_chunk
```

### 4. Update Configuration Migration

**Add voice mapping configuration:**

```python
# Add to configuration handling
VOICE_MIGRATION_MAP = {
    "coqui": "en_US-lessac-medium",
    "kokoro": "en_US-amy-medium",
    "orpheus": "en_GB-alan-medium",
    "default": "en_US-lessac-medium"
}

def migrate_voice_preference(old_engine: str) -> str:
    """Migrate old RealtimeTTS engine preference to Piper voice"""
    return VOICE_MIGRATION_MAP.get(old_engine, "en_US-lessac-medium")
```

### 5. Update Server Integration

**Modify `src/server.py` initialization:**

```python
# Replace RealtimeTTS initialization
# OLD:
# audio_processor = AudioProcessor(engine="kokoro")

# NEW:
piper_engine = PiperTTSEngine()
await piper_engine.initialize()
audio_processor = AudioProcessor(tts_engine=piper_engine)
```

### 6. Add Health Checks

**Create TTS health endpoint:**

```python
@app.get("/tts/health")
async def tts_health():
    """Check TTS engine status"""
    try:
        voices_loaded = len(piper_engine.voices)
        return {
            "status": "healthy" if voices_loaded > 0 else "unhealthy",
            "voices_loaded": voices_loaded,
            "available_voices": list(piper_engine.voices.keys())
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

## Testing the Integration

### 1. Unit Tests

**Create `tests/unit/test_piper_integration.py`:**

```python
import pytest
from src.audio_module import PiperTTSEngine

@pytest.mark.asyncio
async def test_piper_engine_initialization():
    """Test Piper engine loads voices successfully"""
    engine = PiperTTSEngine()
    await engine.initialize()

    assert len(engine.voices) >= 1
    assert engine.current_voice is not None

def test_voice_synthesis():
    """Test basic text synthesis"""
    engine = PiperTTSEngine()
    audio_data = engine.synthesize("Hello, this is a test.")

    assert isinstance(audio_data, bytes)
    assert len(audio_data) > 0
```

### 2. Integration Tests

**Test end-to-end pipeline:**

```bash
# Start server
python -m uvicorn src.server:app --reload

# Test TTS endpoint
curl -X POST http://localhost:8000/tts/synthesize \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello from Piper TTS", "voice_id": "en_US-lessac-medium"}'
```

### 3. Performance Validation

**Verify latency requirements:**

```python
import time

start_time = time.time()
audio_data = engine.synthesize("Test message under 200 characters for latency measurement.")
processing_time = (time.time() - start_time) * 1000

assert processing_time < 2000  # Must be under 2 seconds
```

## Configuration Examples

### Docker Deployment

**Update Dockerfile to include models:**

```dockerfile
# Add to Dockerfile
RUN mkdir -p /app/src/models/piper

# Download models during build
RUN pip install piper-tts onnxruntime
RUN python -c "import piper; piper.download_voice('en_US-lessac-medium', '/app/src/models/piper')"
```

### Environment Configuration

**Update environment variables:**

```bash
export TTS_ENGINE=piper
export TTS_MODEL_PATH=/app/src/models/piper
export TTS_DEFAULT_VOICE=en_US-lessac-medium
export ONNX_THREAD_COUNT=3  # For Pi 5
```

## Troubleshooting

### Common Issues

**1. Voice models not loading:**

```bash
# Check model files exist
ls -la src/models/piper/
# Should see .onnx and .onnx.json files

# Check file permissions
chmod 644 src/models/piper/*
```

**2. ONNX runtime errors on Pi 5:**

```python
# Set CPU provider explicitly
import onnxruntime
providers = ['CPUExecutionProvider']
```

**3. Memory issues with multiple voices:**

```python
# Implement lazy loading
def load_voice_on_demand(self, voice_id: str):
    if voice_id not in self.loaded_voices:
        # Load only when needed
        self.loaded_voices[voice_id] = piper.PiperVoice.load(...)
```

### Performance Optimization

**Pi 5 specific settings:**

```python
# Optimize for Pi 5 ARM64
PIPER_CONFIG = {
    "thread_count": 3,  # Leave 1 core for system
    "providers": ["CPUExecutionProvider"],
    "session_options": {
        "intra_op_num_threads": 3,
        "inter_op_num_threads": 1
    }
}
```

## Migration Checklist

- [ ] Remove RealtimeTTS dependencies from requirements.txt
- [ ] Add Piper TTS dependencies
- [ ] Download and verify voice models (3 voices minimum)
- [ ] Update audio_module.py with Piper integration
- [ ] Implement voice preference migration
- [ ] Update server initialization
- [ ] Add health check endpoints
- [ ] Create unit tests for Piper integration
- [ ] Run integration tests for full pipeline
- [ ] Verify performance meets latency requirements (<2s)
- [ ] Test fallback behavior when TTS fails
- [ ] Update Docker configuration for production
- [ ] Document new voice configuration options

## Next Steps

After completing this integration:

1. **Performance Testing**: Benchmark on target Pi 5 hardware
2. **User Testing**: Validate voice quality meets user expectations
3. **Monitoring Setup**: Implement TTS performance metrics logging
4. **Documentation Update**: Update user-facing documentation for new voice options
5. **Rollout Planning**: Plan gradual migration for existing deployments

For issues or questions, refer to the full specification in `spec.md` and data model in `data-model.md`.
