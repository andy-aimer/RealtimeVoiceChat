# Data Model: Piper TTS Integration

**Feature**: Replace RealtimeTTS with Piper TTS  
**Date**: November 1, 2025  
**Phase**: Design (Phase 1)

## Core Entities

### TTS Engine Configuration

**Purpose**: Manages Piper-specific settings and voice configurations

**Fields**:

- `engine_type: str` - Always "piper" (replaces "coqui"/"kokoro"/"orpheus")
- `default_voice: str` - Default voice ID (e.g., "en_US-lessac-medium")
- `available_voices: List[VoiceProfile]` - List of installed voice models
- `model_path: str` - Directory path where ONNX models are stored
- `onnx_providers: List[str]` - ONNX runtime providers (["CPUExecutionProvider"])
- `thread_count: int` - Number of threads for inference (3 for Pi 5)
- `sample_rate: int` - Audio output sample rate (22050 Hz default)
- `streaming_enabled: bool` - Enable real-time audio streaming (true)

**Validation Rules**:

- `default_voice` must exist in `available_voices` list
- `model_path` must be accessible directory with read permissions
- `thread_count` must be between 1-4 for Pi 5 deployments
- `sample_rate` must be supported rate (16000, 22050, or 44100)

**State Transitions**:

- Initialization → Models Loading → Ready
- Ready → Voice Switching → Ready
- Ready → Error → Fallback Mode

### Voice Profile

**Purpose**: Represents individual Piper voice characteristics and metadata

**Fields**:

- `voice_id: str` - Unique voice identifier (e.g., "en_US-lessac-medium")
- `display_name: str` - Human-readable name (e.g., "US English (Lessac)")
- `language: str` - Language code (e.g., "en-US", "en-GB")
- `gender: str` - Voice gender ("male", "female", "neutral")
- `quality: str` - Quality level ("low", "medium", "high")
- `model_file: str` - ONNX model filename (e.g., "en_US-lessac-medium.onnx")
- `config_file: str` - Voice configuration JSON filename
- `file_size_mb: float` - Model file size in megabytes
- `sample_rate: int` - Native sample rate for this voice
- `is_loaded: bool` - Whether model is currently loaded in memory

**Validation Rules**:

- `voice_id` must match model filename prefix
- `model_file` and `config_file` must exist in model directory
- `language` must be valid ISO 639-1 code
- `gender` must be one of allowed values
- `quality` determines expected file size ranges

**Relationships**:

- Multiple VoiceProfile entities per TTS Engine Configuration
- One-to-one mapping between VoiceProfile and physical ONNX model files

### Audio Output Stream

**Purpose**: Generated audio data with processing metadata for streaming delivery

**Fields**:

- `audio_data: bytes` - Raw audio samples (PCM format)
- `sample_rate: int` - Audio sample rate (inherited from voice)
- `channels: int` - Number of audio channels (1 for mono)
- `duration_ms: float` - Audio segment duration in milliseconds
- `chunk_index: int` - Sequence number for streaming chunks
- `is_final_chunk: bool` - Indicates last chunk in sequence
- `voice_id: str` - Voice used for generation
- `processing_time_ms: float` - TTS generation time
- `timestamp: datetime` - Generation timestamp

**Validation Rules**:

- `audio_data` must not be empty unless error occurred
- `sample_rate` must match voice profile specification
- `chunk_index` must be sequential starting from 0
- `processing_time_ms` must be positive value

**State Transitions**:

- Created → Streaming → Completed
- Created → Error (if generation fails)

### TTS Request

**Purpose**: Text input with voice selection and processing context for TTS generation

**Fields**:

- `request_id: str` - Unique identifier for tracking
- `text: str` - Input text for synthesis (max 2000 characters)
- `voice_id: str` - Selected voice for generation
- `user_context: Optional[str]` - User session or preference context
- `priority: int` - Processing priority (1=high, 3=normal, 5=low)
- `streaming: bool` - Enable streaming output (default true)
- `created_at: datetime` - Request timestamp
- `status: RequestStatus` - Current processing state
- `estimated_duration_ms: Optional[float]` - Expected audio duration

**Validation Rules**:

- `text` must not be empty and under character limit
- `voice_id` must reference available voice profile
- `priority` must be between 1-5
- `request_id` must be unique across active requests

**Request Status Values**:

- `PENDING` - Queued for processing
- `PROCESSING` - Currently generating audio
- `STREAMING` - Delivering audio chunks
- `COMPLETED` - Successfully finished
- `FAILED` - Generation error occurred
- `CANCELLED` - User cancelled request

## Entity Relationships

```
TTS Engine Configuration (1)
    ↓ has many
Voice Profile (3+)
    ↓ used by
TTS Request (N)
    ↓ produces
Audio Output Stream (N chunks)
```

## Migration Mapping

**Legacy RealtimeTTS to Piper Voice Mapping**:

| Legacy Engine | Piper Voice ID      | Display Name           |
| ------------- | ------------------- | ---------------------- |
| coqui         | en_US-lessac-medium | US English (Lessac)    |
| kokoro        | en_US-amy-medium    | US English (Amy)       |
| orpheus       | en_GB-alan-medium   | British English (Alan) |
| default       | en_US-lessac-medium | US English (Lessac)    |

**Configuration Migration**:

```yaml
# Old format (RealtimeTTS)
tts:
  engine: "kokoro"
  voice: "default"

# New format (Piper)
tts:
  engine: "piper"
  voice_id: "en_US-amy-medium"
  model_path: "src/models/piper"
```

## Data Storage

**Configuration Files**:

- `config/tts_config.json` - TTS engine configuration
- `config/voice_profiles.json` - Available voice metadata
- `src/models/piper/*.onnx` - Voice model files
- `src/models/piper/*.json` - Voice configuration files

**In-Memory Caching**:

- Loaded ONNX models (up to 3 simultaneously)
- Voice profile metadata (loaded at startup)
- Active TTS requests queue (max 10 pending)
- Recent audio chunks (5-second sliding window for streaming)

**Persistence Requirements**:

- Voice model files persist across restarts
- User voice preferences saved to configuration
- TTS processing metrics logged for monitoring
- Error states and failures logged for debugging

This data model maintains compatibility with existing audio pipeline while enabling the transition from RealtimeTTS engines to Piper TTS with improved performance and offline capabilities.
