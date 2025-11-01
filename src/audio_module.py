import asyncio
import json
import logging
import os
import struct
import threading
import time
from collections import namedtuple
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from queue import Queue
from typing import AsyncGenerator, Callable, Dict, Generator, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# Try to import Piper TTS for the new implementation
try:
    import piper
    HAS_PIPER = True
    logger.info("Piper TTS library available")
except ImportError as e:
    HAS_PIPER = False
    logger.warning(f"Piper TTS not available ({e})")

# Try to import RealtimeTTS, fall back to simple version
try:
    from RealtimeTTS import (CoquiEngine, KokoroEngine, OrpheusEngine,
                             OrpheusVoice, TextToAudioStream)
    from huggingface_hub import hf_hub_download
    logger.info("Using full RealtimeTTS audio processor")
    HAS_REALTIMETTS = True
except ImportError as e:
    logger.warning(f"RealtimeTTS not available ({e}), using simple TTS processor")
    from tts_simple import (CoquiEngine, KokoroEngine, OrpheusEngine,
                            OrpheusVoice, TextToAudioStream)
    # Define a dummy hf_hub_download for compatibility
    def hf_hub_download(*args, **kwargs):
        logger.warning("huggingface_hub not available, skipping model download")
        return None
    HAS_REALTIMETTS = False

# Piper TTS Data Classes (T011, T012, T018, T019)
@dataclass
class VoiceProfile:
    """Represents individual Piper voice characteristics and metadata"""
    voice_id: str
    display_name: str
    language: str
    gender: str
    quality: str
    model_file: str
    config_file: str
    file_size_mb: float
    sample_rate: int
    is_loaded: bool = False

@dataclass
class TTSEngineConfig:
    """Manages Piper-specific settings and voice configurations"""
    engine_type: str = "piper"
    default_voice: str = "en_US-lessac-medium"
    available_voices: List[VoiceProfile] = None
    model_path: str = "src/models/piper"
    onnx_providers: List[str] = None
    thread_count: int = 3
    sample_rate: int = 22050
    streaming_enabled: bool = True
    
    def __post_init__(self):
        if self.available_voices is None:
            self.available_voices = []
        if self.onnx_providers is None:
            self.onnx_providers = ["CPUExecutionProvider"]

@dataclass
class AudioOutputStream:
    """Generated audio data with processing metadata for streaming delivery"""
    audio_data: bytes
    sample_rate: int
    channels: int = 1
    duration_ms: float = 0.0
    chunk_index: int = 0
    is_final_chunk: bool = False
    voice_id: str = ""
    processing_time_ms: float = 0.0
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

@dataclass
class TTSRequest:
    """Text input with voice selection and processing context for TTS generation"""
    request_id: str
    text: str
    voice_id: str
    user_context: Optional[str] = None
    priority: int = 3
    streaming: bool = True
    created_at: datetime = None
    status: str = "PENDING"
    estimated_duration_ms: Optional[float] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

# Default configuration constants
START_ENGINE = "kokoro"
Silence = namedtuple("Silence", ("comma", "sentence", "default"))
ENGINE_SILENCES = {
    "coqui":   Silence(comma=0.3, sentence=0.6, default=0.3),
    "kokoro":  Silence(comma=0.3, sentence=0.6, default=0.3),
    "orpheus": Silence(comma=0.3, sentence=0.6, default=0.3),
}
# Stream chunk sizes influence latency vs. throughput trade-offs
QUICK_ANSWER_STREAM_CHUNK_SIZE = 8
FINAL_ANSWER_STREAM_CHUNK_SIZE = 30

# Coqui model download helper functions
def create_directory(path: str) -> None:
    """
    Creates a directory at the specified path if it doesn't already exist.

    Args:
        path: The directory path to create.
    """
    if not os.path.exists(path):
        os.makedirs(path)

def ensure_lasinya_models(models_root: str = "models", model_name: str = "Lasinya") -> None:
    """
    Ensures the Coqui XTTS Lasinya model files are present locally.

    Checks for required model files (config.json, vocab.json, etc.) within
    the specified directory structure. If any file is missing, it downloads
    it from the 'KoljaB/XTTS_Lasinya' Hugging Face Hub repository.

    Args:
        models_root: The root directory where models are stored.
        model_name: The specific name of the model subdirectory.
    """
    base = os.path.join(models_root, model_name)
    create_directory(base)
    files = ["config.json", "vocab.json", "speakers_xtts.pth", "model.pth"]
    for fn in files:
        local_file = os.path.join(base, fn)
        if not os.path.exists(local_file):
            # Not using logger here as it might not be configured yet during module import/init
            print(f"👄⏬ Downloading {fn} to {base}")
            hf_hub_download(
                repo_id="KoljaB/XTTS_Lasinya",
                filename=fn,
                local_dir=base
            )

# Voice migration mapping from RealtimeTTS to Piper (T014)
VOICE_MIGRATION_MAP = {
    "coqui": "en_US-lessac-medium",
    "kokoro": "en_US-amy-medium",
    "orpheus": "en_GB-alan-medium",
    "default": "en_US-lessac-medium"
}

class PiperTTSEngine:
    """
    Piper TTS engine integration for offline text-to-speech synthesis.
    
    This class manages Piper TTS voice models, handles text-to-audio synthesis,
    and provides streaming audio generation capabilities. It replaces the
    RealtimeTTS engines (Coqui, Kokoro, Orpheus) with a single, offline-first
    TTS solution optimized for Raspberry Pi 5 and other edge devices.
    
    Tasks: T009, T010, T013, T015, T016, T017, T020
    """
    
    def __init__(self, model_path: str = "src/models/piper", config_path: str = "config/tts_config.json"):
        """
        Initialize the Piper TTS engine with configuration.
        
        Args:
            model_path: Directory path where ONNX voice models are stored
            config_path: Path to TTS configuration JSON file
        """
        self.model_path = Path(model_path)
        self.config_path = Path(config_path)
        self.voices: Dict[str, any] = {}  # Will hold loaded Piper voice objects
        self.voice_profiles: Dict[str, VoiceProfile] = {}
        self.current_voice_id: Optional[str] = None
        self.config: Optional[TTSEngineConfig] = None
        
        logger.info(f"🎤 Initializing PiperTTSEngine with model_path={model_path}")
        
    async def initialize(self) -> None:
        """
        Load configuration and available voice models.
        
        Tasks: T010, T015
        """
        try:
            # Load configuration (T015)
            self.config = self._load_configuration()
            
            # Discover and load voice models (T010)
            await self._load_voice_profiles()
            
            # Set default voice
            if self.voice_profiles:
                default_voice = self.config.default_voice
                if default_voice in self.voice_profiles:
                    self.current_voice_id = default_voice
                    logger.info(f"🎤 Set default voice to: {default_voice}")
                else:
                    # Use first available voice as fallback
                    self.current_voice_id = list(self.voice_profiles.keys())[0]
                    logger.warning(f"🎤 Default voice '{default_voice}' not found, using: {self.current_voice_id}")
            else:
                raise RuntimeError("No Piper voice models found in model directory")
                
            logger.info(f"🎤 PiperTTSEngine initialized with {len(self.voice_profiles)} voices")
            
        except Exception as e:
            logger.error(f"🎤 Failed to initialize PiperTTSEngine: {e}", exc_info=True)
            raise
    
    def _load_configuration(self) -> TTSEngineConfig:
        """
        Load TTS configuration from JSON file or create default.
        
        Task: T015
        """
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    config_data = json.load(f)
                    
                # Handle voice migration if old engine names present
                if 'engine' in config_data and config_data['engine'] in VOICE_MIGRATION_MAP:
                    old_engine = config_data['engine']
                    config_data['default_voice'] = VOICE_MIGRATION_MAP[old_engine]
                    logger.info(f"🎤 Migrated voice preference from '{old_engine}' to '{config_data['default_voice']}'")
                
                # Extract relevant fields for TTSEngineConfig
                return TTSEngineConfig(
                    default_voice=config_data.get('default_voice', 'en_US-lessac-medium'),
                    model_path=config_data.get('model_path', str(self.model_path)),
                    thread_count=config_data.get('thread_count', 3),
                    sample_rate=config_data.get('sample_rate', 22050),
                    streaming_enabled=config_data.get('streaming_enabled', True)
                )
            except Exception as e:
                logger.warning(f"🎤 Failed to load config from {self.config_path}: {e}, using defaults")
                return TTSEngineConfig()
        else:
            logger.info(f"🎤 No config file found at {self.config_path}, using defaults")
            return TTSEngineConfig()
    
    async def _load_voice_profiles(self) -> None:
        """
        Discover and load voice models from the model directory.
        
        Task: T010
        """
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model directory not found: {self.model_path}")
        
        # Scan for .onnx model files
        onnx_files = list(self.model_path.glob("*.onnx"))
        logger.info(f"🎤 Found {len(onnx_files)} ONNX model files")
        
        for onnx_file in onnx_files:
            voice_id = onnx_file.stem  # e.g., "en_US-lessac-medium"
            config_file = onnx_file.with_suffix('.onnx.json')
            
            if not config_file.exists():
                logger.warning(f"🎤 Config file missing for {voice_id}, skipping")
                continue
            
            try:
                # Load voice metadata from config JSON
                with open(config_file, 'r') as f:
                    voice_config = json.load(f)
                
                # Parse voice metadata
                display_name = self._generate_display_name(voice_id)
                language = voice_config.get('language', {}).get('code', 'en-US')
                
                # Determine gender from voice name patterns (heuristic)
                gender = self._infer_gender(voice_id, voice_config)
                
                # Quality is in the voice_id (low/medium/high)
                quality = "medium"
                if "-low" in voice_id:
                    quality = "low"
                elif "-high" in voice_id:
                    quality = "high"
                
                # Get file size
                file_size_mb = onnx_file.stat().st_size / (1024 * 1024)
                
                # Get sample rate from config
                sample_rate = voice_config.get('audio', {}).get('sample_rate', 22050)
                
                # Create voice profile
                profile = VoiceProfile(
                    voice_id=voice_id,
                    display_name=display_name,
                    language=language,
                    gender=gender,
                    quality=quality,
                    model_file=str(onnx_file),
                    config_file=str(config_file),
                    file_size_mb=file_size_mb,
                    sample_rate=sample_rate,
                    is_loaded=False
                )
                
                self.voice_profiles[voice_id] = profile
                logger.info(f"🎤 Loaded voice profile: {display_name} ({voice_id})")
                
            except Exception as e:
                logger.error(f"🎤 Failed to load voice {voice_id}: {e}", exc_info=True)
    
    def _generate_display_name(self, voice_id: str) -> str:
        """Generate human-readable display name from voice ID"""
        # Parse voice_id like "en_US-lessac-medium"
        parts = voice_id.replace('_', '-').split('-')
        if len(parts) >= 2:
            locale = parts[0:2]  # ['en', 'US']
            name = parts[2] if len(parts) > 2 else "voice"
            
            # Format locale
            if locale[0] == 'en':
                if locale[1] == 'US':
                    region = "US English"
                elif locale[1] == 'GB':
                    region = "British English"
                else:
                    region = f"{locale[1]} English"
            else:
                region = f"{locale[0]}-{locale[1]}"
            
            # Capitalize name
            name = name.capitalize()
            
            return f"{region} ({name})"
        return voice_id
    
    def _infer_gender(self, voice_id: str, voice_config: dict) -> str:
        """Infer gender from voice name or config (heuristic)"""
        voice_lower = voice_id.lower()
        
        # Common male voice names
        if any(name in voice_lower for name in ['alan', 'joe', 'john', 'danny', 'ryan']):
            return "male"
        
        # Common female voice names
        if any(name in voice_lower for name in ['amy', 'lessac', 'kathleen', 'jenny', 'sara']):
            return "female"
        
        # Check config for hints
        if 'speaker_name' in voice_config:
            speaker = voice_config['speaker_name'].lower()
            if any(name in speaker for name in ['male', 'man', 'boy']):
                return "male"
            if any(name in speaker for name in ['female', 'woman', 'girl']):
                return "female"
        
        return "neutral"
    
    def synthesize(self, text: str, voice_id: Optional[str] = None) -> bytes:
        """
        Synchronous text-to-audio synthesis.
        
        Args:
            text: Text to synthesize
            voice_id: Optional voice ID to use (uses current_voice_id if None)
            
        Returns:
            Raw audio bytes (WAV format PCM)
            
        Task: T016
        """
        if not HAS_PIPER:
            raise RuntimeError("Piper TTS library not available")
        
        start_time = time.time()
        
        try:
            # Select voice
            target_voice_id = voice_id or self.current_voice_id
            if target_voice_id not in self.voice_profiles:
                raise ValueError(f"Voice '{target_voice_id}' not available")
            
            # Load voice if not already loaded
            if target_voice_id not in self.voices:
                self._load_voice_model(target_voice_id)
            
            voice = self.voices[target_voice_id]
            
            # Synthesize audio
            logger.debug(f"🎤 Synthesizing: '{text[:50]}...' with voice {target_voice_id}")
            
            # Piper returns a generator of AudioChunk objects, collect all audio bytes
            audio_chunks = []
            for audio_chunk in voice.synthesize(text):
                # AudioChunk has audio_int16_bytes property
                audio_chunks.append(audio_chunk.audio_int16_bytes)
            
            # Combine all chunks
            audio_bytes = b''.join(audio_chunks)
            
            processing_time = (time.time() - start_time) * 1000
            logger.info(f"🎤 Synthesis complete in {processing_time:.2f}ms for {len(text)} chars")
            
            return audio_bytes
            
        except Exception as e:
            logger.error(f"🎤 Synthesis failed: {e}", exc_info=True)
            raise
    
    async def synthesize_streaming(
        self, 
        text: str, 
        voice_id: Optional[str] = None
    ) -> AsyncGenerator[AudioOutputStream, None]:
        """
        Streaming text-to-audio synthesis with chunk delivery.
        
        Args:
            text: Text to synthesize
            voice_id: Optional voice ID to use
            
        Yields:
            AudioOutputStream objects containing audio chunks
            
        Tasks: T017, T020
        """
        if not HAS_PIPER:
            raise RuntimeError("Piper TTS library not available")
        
        start_time = time.time()
        chunk_index = 0
        
        try:
            # Select voice
            target_voice_id = voice_id or self.current_voice_id
            if target_voice_id not in self.voice_profiles:
                raise ValueError(f"Voice '{target_voice_id}' not available")
            
            # Load voice if needed
            if target_voice_id not in self.voices:
                self._load_voice_model(target_voice_id)
            
            voice = self.voices[target_voice_id]
            profile = self.voice_profiles[target_voice_id]
            
            logger.debug(f"🎤 Streaming synthesis: '{text[:50]}...' with voice {target_voice_id}")
            
            # Use Piper's synthesis (returns generator of AudioChunk objects)
            for piper_chunk in voice.synthesize(text):
                # Get audio bytes from AudioChunk
                audio_bytes = piper_chunk.audio_int16_bytes
                
                # Calculate chunk metadata
                samples = len(audio_bytes) // 2  # 16-bit audio = 2 bytes per sample
                duration_ms = (samples / profile.sample_rate) * 1000
                
                # Create output stream object
                output = AudioOutputStream(
                    audio_data=audio_bytes,
                    sample_rate=profile.sample_rate,
                    channels=1,
                    duration_ms=duration_ms,
                    chunk_index=chunk_index,
                    is_final_chunk=False,
                    voice_id=target_voice_id,
                    processing_time_ms=(time.time() - start_time) * 1000
                )
                
                yield output
                chunk_index += 1
            
            # Mark final chunk
            if chunk_index > 0:
                # Send final marker chunk (empty audio with final flag)
                final_output = AudioOutputStream(
                    audio_data=b'',
                    sample_rate=profile.sample_rate,
                    channels=1,
                    duration_ms=0.0,
                    chunk_index=chunk_index,
                    is_final_chunk=True,
                    voice_id=target_voice_id,
                    processing_time_ms=(time.time() - start_time) * 1000
                )
                yield final_output
            
            total_time = (time.time() - start_time) * 1000
            logger.info(f"🎤 Streaming synthesis complete: {chunk_index} chunks in {total_time:.2f}ms")
            
        except Exception as e:
            logger.error(f"🎤 Streaming synthesis failed: {e}", exc_info=True)
            raise
    
    def _load_voice_model(self, voice_id: str) -> None:
        """
        Load a voice model into memory.
        
        Task: T010
        """
        if voice_id not in self.voice_profiles:
            raise ValueError(f"Voice profile '{voice_id}' not found")
        
        profile = self.voice_profiles[voice_id]
        
        try:
            logger.info(f"🎤 Loading voice model: {voice_id}")
            
            # Load Piper voice
            voice = piper.PiperVoice.load(
                profile.model_file,
                config_path=profile.config_file,
                use_cuda=False  # CPU only for Pi 5 compatibility
            )
            
            self.voices[voice_id] = voice
            profile.is_loaded = True
            
            logger.info(f"🎤 Voice model loaded: {profile.display_name}")
            
        except Exception as e:
            logger.error(f"🎤 Failed to load voice model {voice_id}: {e}", exc_info=True)
            raise
    
    def get_available_voices(self) -> List[VoiceProfile]:
        """
        Get list of available voice profiles.
        
        Returns:
            List of VoiceProfile objects
        """
        return list(self.voice_profiles.values())
    
    def set_voice(self, voice_id: str) -> None:
        """
        Set the current voice for synthesis.
        
        Args:
            voice_id: Voice ID to set as current
        """
        if voice_id not in self.voice_profiles:
            raise ValueError(f"Voice '{voice_id}' not available")
        
        self.current_voice_id = voice_id
        logger.info(f"🎤 Current voice set to: {voice_id}")

class AudioProcessor:
    """
    Manages Text-to-Speech (TTS) synthesis using various engines via RealtimeTTS.

    This class initializes a chosen TTS engine (Coqui, Kokoro, or Orpheus),
    configures it for streaming output, measures initial latency (TTFT),
    and provides methods to synthesize audio from text strings or generators,
    placing the resulting audio chunks into a queue. It handles dynamic
    stream parameter adjustments and manages the synthesis lifecycle, including
    optional callbacks upon receiving the first audio chunk.
    """
    def __init__(
            self,
            engine: str = START_ENGINE,
            orpheus_model: str = "orpheus-3b-0.1-ft-Q8_0-GGUF/orpheus-3b-0.1-ft-q8_0.gguf",
            piper_engine: Optional[PiperTTSEngine] = None,
        ) -> None:
        """
        Initializes the AudioProcessor with a specific TTS engine.

        Sets up the chosen engine (Coqui, Kokoro, Orpheus, Piper), downloads Coqui models
        if necessary, configures the RealtimeTTS stream, and performs an initial
        synthesis to measure Time To First Audio chunk (TTFA).

        Args:
            engine: The name of the TTS engine to use ("coqui", "kokoro", "orpheus", "piper").
            orpheus_model: The path or identifier for the Orpheus model file (used only if engine is "orpheus").
            piper_engine: Pre-initialized PiperTTSEngine instance (required if engine is "piper").
        """
        self.engine_name = engine
        self.stop_event = threading.Event()
        self.finished_event = threading.Event()
        self.audio_chunks = asyncio.Queue() # Queue for synthesized audio output
        self.orpheus_model = orpheus_model
        self.piper_engine = piper_engine

        # Handle Piper TTS engine (T021, T022)
        if engine == "piper":
            if not HAS_PIPER:
                logger.error("🎤 Piper TTS requested but library not available, falling back to simple TTS")
                engine = "kokoro"  # Fallback to kokoro
                self.engine_name = engine
            elif piper_engine is None:
                raise ValueError("piper_engine parameter required when engine='piper'")
            else:
                logger.info("🎤 Using Piper TTS engine")
                self.engine = None  # No RealtimeTTS engine
                self.stream = None  # No RealtimeTTS stream
                self.tts_inference_time = 0  # Will be measured on first synthesis
                self.on_first_audio_chunk_synthesize: Optional[Callable[[], None]] = None
                return  # Skip RealtimeTTS initialization

        self.silence = ENGINE_SILENCES.get(engine, ENGINE_SILENCES[self.engine_name])
        self.current_stream_chunk_size = QUICK_ANSWER_STREAM_CHUNK_SIZE # Initial chunk size

        # Dynamically load and configure the selected TTS engine
        if engine == "coqui":
            ensure_lasinya_models(models_root="models", model_name="Lasinya")
            self.engine = CoquiEngine(
                specific_model="Lasinya",
                local_models_path="./models",
                voice="reference_audio.wav",
                speed=1.1,
                use_deepspeed=True,
                thread_count=6,
                stream_chunk_size=self.current_stream_chunk_size,
                overlap_wav_len=1024,
                load_balancing=True,
                load_balancing_buffer_length=0.5,
                load_balancing_cut_off=0.1,
                add_sentence_filter=True,
            )
        elif engine == "kokoro":
            self.engine = KokoroEngine(
                voice="af_heart",
                default_speed=1.26,
                trim_silence=True,
                silence_threshold=0.01,
                extra_start_ms=25,
                extra_end_ms=15,
                fade_in_ms=15,
                fade_out_ms=10,
            )
        elif engine == "orpheus":
            self.engine = OrpheusEngine(
                model=self.orpheus_model,
                temperature=0.8,
                top_p=0.95,
                repetition_penalty=1.1,
                max_tokens=1200,
            )
            voice = OrpheusVoice("tara")
            self.engine.set_voice(voice)
        else:
            raise ValueError(f"Unsupported engine: {engine}")


        # Initialize the RealtimeTTS stream
        self.stream = TextToAudioStream(
            self.engine,
            muted=True, # Do not play audio directly
            playout_chunk_size=4096, # Internal chunk size for processing
            on_audio_stream_stop=self.on_audio_stream_stop,
        )

        # Ensure Coqui engine starts with the quick chunk size
        if self.engine_name == "coqui" and hasattr(self.engine, 'set_stream_chunk_size') and self.current_stream_chunk_size != QUICK_ANSWER_STREAM_CHUNK_SIZE:
            logger.info(f"👄⚙️ Setting Coqui stream chunk size to {QUICK_ANSWER_STREAM_CHUNK_SIZE} for initial setup.")
            self.engine.set_stream_chunk_size(QUICK_ANSWER_STREAM_CHUNK_SIZE)
            self.current_stream_chunk_size = QUICK_ANSWER_STREAM_CHUNK_SIZE

        # Prewarm the engine
        self.stream.feed("prewarm")
        play_kwargs = dict(
            log_synthesized_text=False, # Don't log prewarm text
            muted=True,
            fast_sentence_fragment=False,
            comma_silence_duration=self.silence.comma,
            sentence_silence_duration=self.silence.sentence,
            default_silence_duration=self.silence.default,
            force_first_fragment_after_words=999999, # Effectively disable this
        )
        self.stream.play(**play_kwargs) # Synchronous play for prewarm
        # Wait for prewarm to finish (indicated by on_audio_stream_stop)
        while self.stream.is_playing():
            time.sleep(0.01)
        self.finished_event.wait() # Wait for stop callback
        self.finished_event.clear()

        # Measure Time To First Audio (TTFA)
        start_time = time.time()
        ttfa = None
        def on_audio_chunk_ttfa(chunk: bytes):
            nonlocal ttfa
            if ttfa is None:
                ttfa = time.time() - start_time
                logger.debug(f"👄⏱️ TTFA measurement first chunk arrived, TTFA: {ttfa:.2f}s.")

        self.stream.feed("This is a test sentence to measure the time to first audio chunk.")
        play_kwargs_ttfa = dict(
            on_audio_chunk=on_audio_chunk_ttfa,
            log_synthesized_text=False, # Don't log test sentence
            muted=True,
            fast_sentence_fragment=False,
            comma_silence_duration=self.silence.comma,
            sentence_silence_duration=self.silence.sentence,
            default_silence_duration=self.silence.default,
            force_first_fragment_after_words=999999,
        )
        self.stream.play_async(**play_kwargs_ttfa)

        # Wait until the first chunk arrives or stream finishes
        while ttfa is None and (self.stream.is_playing() or not self.finished_event.is_set()):
            time.sleep(0.01)
        self.stream.stop() # Ensure stream stops cleanly

        # Wait for stop callback if it hasn't fired yet
        if not self.finished_event.is_set():
            self.finished_event.wait(timeout=2.0) # Add timeout for safety
        self.finished_event.clear()

        if ttfa is not None:
            logger.debug(f"👄⏱️ TTFA measurement complete. TTFA: {ttfa:.2f}s.")
            self.tts_inference_time = ttfa * 1000  # Store as ms
        else:
            logger.warning("👄⚠️ TTFA measurement failed (no audio chunk received).")
            self.tts_inference_time = 0

        # Callbacks to be set externally if needed
        self.on_first_audio_chunk_synthesize: Optional[Callable[[], None]] = None

    def on_audio_stream_stop(self) -> None:
        """
        Callback executed when the RealtimeTTS audio stream stops processing.

        Logs the event and sets the `finished_event` to signal completion or stop.
        """
        logger.info("👄🛑 Audio stream stopped.")
        self.finished_event.set()

    def _synthesize_piper(
            self,
            text: str,
            audio_chunks: Queue,
            stop_event: threading.Event,
            generation_string: str = "",
        ) -> bool:
        """
        Piper TTS synthesis implementation (T022, T024).
        
        Synthesizes audio using Piper TTS and puts chunks into the queue.
        Compatible with the existing AudioProcessor interface.
        """
        if not self.piper_engine:
            logger.error("🎤 Piper engine not initialized")
            return False
        
        start_time = time.time()
        first_chunk_fired = False
        
        try:
            logger.info(f"🎤▶️ {generation_string} Starting Piper synthesis. Text: {text[:50]}...")
            
            # Synchronous synthesis (Piper doesn't support true streaming in the same way)
            audio_data = self.piper_engine.synthesize(text)
            
            # Check for interruption before processing
            if stop_event.is_set():
                logger.info(f"🎤🛑 {generation_string} Piper synthesis aborted before audio delivery")
                return False
            
            # Split audio into chunks for streaming delivery (T024)
            CHUNK_SIZE = 8192  # 4096 samples * 2 bytes (16-bit audio)
            for i in range(0, len(audio_data), CHUNK_SIZE):
                if stop_event.is_set():
                    logger.info(f"🎤🛑 {generation_string} Piper synthesis interrupted")
                    return False
                
                chunk = audio_data[i:i+CHUNK_SIZE]
                try:
                    audio_chunks.put_nowait(chunk)
                    
                    # Fire callback on first chunk
                    if not first_chunk_fired and self.on_first_audio_chunk_synthesize:
                        try:
                            logger.info(f"🎤🚀 {generation_string} Firing on_first_audio_chunk_synthesize")
                            self.on_first_audio_chunk_synthesize()
                            first_chunk_fired = True
                        except Exception as e:
                            logger.error(f"🎤💥 {generation_string} Error in callback: {e}", exc_info=True)
                            
                except asyncio.QueueFull:
                    logger.warning(f"🎤⚠️ {generation_string} Audio queue full, dropping chunk")
            
            processing_time = (time.time() - start_time) * 1000
            logger.info(f"🎤✅ {generation_string} Piper synthesis complete in {processing_time:.2f}ms. Text: {text[:50]}...")
            
            # Update inference time measurement (T026)
            if not hasattr(self, 'tts_inference_time') or self.tts_inference_time == 0:
                self.tts_inference_time = processing_time
            
            return True
            
        except Exception as e:
            logger.error(f"🎤💥 {generation_string} Piper synthesis failed: {e}", exc_info=True)
            return False

    def _synthesize_generator_piper(
            self,
            generator: Generator[str, None, None],
            audio_chunks: Queue,
            stop_event: threading.Event,
            generation_string: str = "",
        ) -> bool:
        """
        Piper TTS generator synthesis implementation (T022, T024).
        
        Collects text from generator and synthesizes with Piper TTS.
        Note: Piper doesn't support true streaming synthesis from text generators,
        so we accumulate text and synthesize in chunks.
        """
        if not self.piper_engine:
            logger.error("🎤 Piper engine not initialized")
            return False
        
        start_time = time.time()
        first_chunk_fired = False
        text_buffer = []
        
        try:
            logger.info(f"🎤▶️ {generation_string} Starting Piper generator synthesis")
            
            # Accumulate text from generator
            for text_chunk in generator:
                if stop_event.is_set():
                    logger.info(f"🎤🛑 {generation_string} Piper generator synthesis interrupted during text collection")
                    return False
                
                if text_chunk:
                    text_buffer.append(text_chunk)
                    
                    # Synthesize every few chunks to reduce latency (T023, T024)
                    if len(text_buffer) >= 3:  # Accumulate 3 chunks before synthesis
                        combined_text = "".join(text_buffer)
                        text_buffer = []
                        
                        if stop_event.is_set():
                            return False
                        
                        # Synthesize accumulated text
                        audio_data = self.piper_engine.synthesize(combined_text)
                        
                        # Split and queue audio chunks
                        CHUNK_SIZE = 8192
                        for i in range(0, len(audio_data), CHUNK_SIZE):
                            if stop_event.is_set():
                                logger.info(f"🎤🛑 {generation_string} Piper generator interrupted during audio delivery")
                                return False
                            
                            chunk = audio_data[i:i+CHUNK_SIZE]
                            try:
                                audio_chunks.put_nowait(chunk)
                                
                                # Fire callback on first chunk
                                if not first_chunk_fired and self.on_first_audio_chunk_synthesize:
                                    try:
                                        logger.info(f"🎤🚀 {generation_string} Firing on_first_audio_chunk_synthesize")
                                        self.on_first_audio_chunk_synthesize()
                                        first_chunk_fired = True
                                    except Exception as e:
                                        logger.error(f"🎤💥 {generation_string} Error in callback: {e}", exc_info=True)
                                        
                            except asyncio.QueueFull:
                                logger.warning(f"🎤⚠️ {generation_string} Audio queue full, dropping chunk")
            
            # Synthesize any remaining text
            if text_buffer and not stop_event.is_set():
                combined_text = "".join(text_buffer)
                audio_data = self.piper_engine.synthesize(combined_text)
                
                CHUNK_SIZE = 8192
                for i in range(0, len(audio_data), CHUNK_SIZE):
                    if stop_event.is_set():
                        return False
                    
                    chunk = audio_data[i:i+CHUNK_SIZE]
                    try:
                        audio_chunks.put_nowait(chunk)
                        
                        if not first_chunk_fired and self.on_first_audio_chunk_synthesize:
                            try:
                                self.on_first_audio_chunk_synthesize()
                                first_chunk_fired = True
                            except Exception as e:
                                logger.error(f"🎤💥 Error in callback: {e}", exc_info=True)
                                
                    except asyncio.QueueFull:
                        logger.warning(f"🎤⚠️ Audio queue full, dropping chunk")
            
            processing_time = (time.time() - start_time) * 1000
            logger.info(f"🎤✅ {generation_string} Piper generator synthesis complete in {processing_time:.2f}ms")
            
            return True
            
        except Exception as e:
            logger.error(f"🎤💥 {generation_string} Piper generator synthesis failed: {e}", exc_info=True)
            return False

    def synthesize(
            self,
            text: str,
            audio_chunks: Queue, 
            stop_event: threading.Event,
            generation_string: str = "",
        ) -> bool:
        """
        Synthesizes audio from a complete text string and puts chunks into a queue.

        Feeds the entire text string to the TTS engine. As audio chunks are generated,
        they are potentially buffered initially for smoother streaming and then put
        into the provided queue. Synthesis can be interrupted via the stop_event.
        Skips initial silent chunks if using the Orpheus engine. Triggers the
        `on_first_audio_chunk_synthesize` callback when the first valid audio chunk is queued.

        Args:
            text: The text string to synthesize.
            audio_chunks: The queue to put the resulting audio chunks (bytes) into.
                          This should typically be the instance's `self.audio_chunks`.
            stop_event: A threading.Event to signal interruption of the synthesis.
                        This should typically be the instance's `self.stop_event`.
            generation_string: An optional identifier string for logging purposes.

        Returns:
            True if synthesis completed fully, False if interrupted by stop_event.
        """
        # Handle Piper TTS engine (T022, T024)
        if self.engine_name == "piper":
            return self._synthesize_piper(text, audio_chunks, stop_event, generation_string)
        
        if self.engine_name == "coqui" and hasattr(self.engine, 'set_stream_chunk_size') and self.current_stream_chunk_size != QUICK_ANSWER_STREAM_CHUNK_SIZE:
            logger.info(f"👄⚙️ {generation_string} Setting Coqui stream chunk size to {QUICK_ANSWER_STREAM_CHUNK_SIZE} for quick synthesis.")
            self.engine.set_stream_chunk_size(QUICK_ANSWER_STREAM_CHUNK_SIZE)
            self.current_stream_chunk_size = QUICK_ANSWER_STREAM_CHUNK_SIZE

        self.stream.feed(text)
        self.finished_event.clear() # Reset finished event before starting

        # Buffering state variables
        buffer: list[bytes] = []
        good_streak: int = 0
        buffering: bool = True
        buf_dur: float = 0.0
        SR, BPS = 24000, 2 # Assumed Sample Rate and Bytes Per Sample (16-bit)
        start = time.time()
        self._quick_prev_chunk_time: float = 0.0 # Track time of previous chunk

        def on_audio_chunk(chunk: bytes):
            nonlocal buffer, good_streak, buffering, buf_dur, start
            # Check for interruption signal
            if stop_event.is_set():
                logger.info(f"👄🛑 {generation_string} Quick audio stream interrupted by stop_event. Text: {text[:50]}...")
                # We should not put more chunks, let the main loop handle stream stop
                return

            now = time.time()
            samples = len(chunk) // BPS
            play_duration = samples / SR # Duration of the current chunk

            # --- Orpheus specific: Skip initial silence ---
            if on_audio_chunk.first_call and self.engine_name == "orpheus":
                if not hasattr(on_audio_chunk, "silent_chunks_count"):
                    # Initialize silence detection state
                    on_audio_chunk.silent_chunks_count = 0
                    on_audio_chunk.silent_chunks_time = 0.0
                    on_audio_chunk.silence_threshold = 200 # Amplitude threshold for silence

                try:
                    # Analyze chunk for silence
                    fmt = f"{samples}h" # Format for 16-bit signed integers
                    pcm_data = struct.unpack(fmt, chunk)
                    avg_amplitude = np.abs(np.array(pcm_data)).mean()

                    if avg_amplitude < on_audio_chunk.silence_threshold:
                        on_audio_chunk.silent_chunks_count += 1
                        on_audio_chunk.silent_chunks_time += play_duration
                        logger.debug(f"👄⏭️ {generation_string} Quick Skipping silent chunk {on_audio_chunk.silent_chunks_count} (avg_amp: {avg_amplitude:.2f})")
                        return # Skip this chunk
                    elif on_audio_chunk.silent_chunks_count > 0:
                        # First non-silent chunk after silence
                        logger.info(f"👄⏭️ {generation_string} Quick Skipped {on_audio_chunk.silent_chunks_count} silent chunks, saved {on_audio_chunk.silent_chunks_time*1000:.2f}ms")
                        # Proceed to process this non-silent chunk
                except Exception as e:
                    logger.warning(f"👄⚠️ {generation_string} Quick Error analyzing audio chunk for silence: {e}")
                    # Proceed assuming not silent on error

            # --- Timing and Logging ---
            if on_audio_chunk.first_call:
                on_audio_chunk.first_call = False
                self._quick_prev_chunk_time = now
                ttfa_actual = now - start
                logger.info(f"👄🚀 {generation_string} Quick audio start. TTFA: {ttfa_actual:.2f}s. Text: {text[:50]}...")
            else:
                gap = now - self._quick_prev_chunk_time
                self._quick_prev_chunk_time = now
                if gap <= play_duration * 1.1: # Allow small tolerance
                    # logger.debug(f"👄✅ {generation_string} Quick chunk ok (gap={gap:.3f}s ≤ {play_duration:.3f}s). Text: {text[:50]}...")
                    good_streak += 1
                else:
                    logger.warning(f"👄❌ {generation_string} Quick chunk slow (gap={gap:.3f}s > {play_duration:.3f}s). Text: {text[:50]}...")
                    good_streak = 0 # Reset streak on slow chunk

            put_occurred_this_call = False # Track if put happened in this specific call

            # --- Buffering Logic ---
            buffer.append(chunk) # Always append the received chunk first
            buf_dur += play_duration # Update buffer duration

            if buffering:
                # Check conditions to flush buffer and stop buffering
                if good_streak >= 2 or buf_dur >= 0.5: # Flush if stable or buffer > 0.5s
                    logger.info(f"👄➡️ {generation_string} Quick Flushing buffer (streak={good_streak}, dur={buf_dur:.2f}s).")
                    for c in buffer:
                        try:
                            audio_chunks.put_nowait(c)
                            put_occurred_this_call = True
                        except asyncio.QueueFull:
                            logger.warning(f"👄⚠️ {generation_string} Quick audio queue full, dropping chunk.")
                    buffer.clear()
                    buf_dur = 0.0 # Reset buffer duration
                    buffering = False # Stop buffering mode
            else: # Not buffering, put chunk directly
                try:
                    audio_chunks.put_nowait(chunk)
                    put_occurred_this_call = True
                except asyncio.QueueFull:
                    logger.warning(f"👄⚠️ {generation_string} Quick audio queue full, dropping chunk.")


            # --- First Chunk Callback ---
            if put_occurred_this_call and not on_audio_chunk.callback_fired:
                if self.on_first_audio_chunk_synthesize:
                    try:
                        logger.info(f"👄🚀 {generation_string} Quick Firing on_first_audio_chunk_synthesize.")
                        self.on_first_audio_chunk_synthesize()
                    except Exception as e:
                        logger.error(f"👄💥 {generation_string} Quick Error in on_first_audio_chunk_synthesize callback: {e}", exc_info=True)
                # Ensure callback fires only once per synthesize call
                on_audio_chunk.callback_fired = True

        # Initialize callback state for this run
        on_audio_chunk.first_call = True
        on_audio_chunk.callback_fired = False

        play_kwargs = dict(
            log_synthesized_text=True, # Log the text being synthesized
            on_audio_chunk=on_audio_chunk,
            muted=True, # We handle audio via the queue
            fast_sentence_fragment=False, # Standard processing
            comma_silence_duration=self.silence.comma,
            sentence_silence_duration=self.silence.sentence,
            default_silence_duration=self.silence.default,
            force_first_fragment_after_words=999999, # Don't force early fragments
        )

        logger.info(f"👄▶️ {generation_string} Quick Starting synthesis. Text: {text[:50]}...")
        self.stream.play_async(**play_kwargs)

        # Wait loop for completion or interruption
        while self.stream.is_playing() or not self.finished_event.is_set():
            if stop_event.is_set():
                self.stream.stop()
                logger.info(f"👄🛑 {generation_string} Quick answer synthesis aborted by stop_event. Text: {text[:50]}...")
                # Drain remaining buffer if any? Decided against it to stop faster.
                buffer.clear()
                # Wait briefly for stop confirmation? The finished_event handles this.
                self.finished_event.wait(timeout=1.0) # Wait for stream stop confirmation
                return False # Indicate interruption
            time.sleep(0.01)

        # # If loop exited normally, check if buffer still has content (stream finished before flush)
        if buffering and buffer and not stop_event.is_set():
            logger.info(f"👄➡️ {generation_string} Quick Flushing remaining buffer after stream finished.")
            for c in buffer:
                 try:
                    audio_chunks.put_nowait(c)
                 except asyncio.QueueFull:
                    logger.warning(f"👄⚠️ {generation_string} Quick audio queue full on final flush, dropping chunk.")
            buffer.clear()

        logger.info(f"👄✅ {generation_string} Quick answer synthesis complete. Text: {text[:50]}...")
        return True # Indicate successful completion

    def synthesize_generator(
            self,
            generator: Generator[str, None, None],
            audio_chunks: Queue, # Should match self.audio_chunks type
            stop_event: threading.Event,
            generation_string: str = "",
        ) -> bool:
        """
        Synthesizes audio from a generator yielding text chunks and puts audio into a queue.

        Feeds text chunks yielded by the generator to the TTS engine. As audio chunks
        are generated, they are potentially buffered initially and then put into the
        provided queue. Synthesis can be interrupted via the stop_event.
        Skips initial silent chunks if using the Orpheus engine. Sets specific playback
        parameters when using the Orpheus engine. Triggers the
       `on_first_audio_chunk_synthesize` callback when the first valid audio chunk is queued.


        Args:
            generator: A generator yielding text chunks (strings) to synthesize.
            audio_chunks: The queue to put the resulting audio chunks (bytes) into.
                          This should typically be the instance's `self.audio_chunks`.
            stop_event: A threading.Event to signal interruption of the synthesis.
                        This should typically be the instance's `self.stop_event`.
            generation_string: An optional identifier string for logging purposes.

        Returns:
            True if synthesis completed fully, False if interrupted by stop_event.
        """
        # Handle Piper TTS engine (T022, T024)
        if self.engine_name == "piper":
            return self._synthesize_generator_piper(generator, audio_chunks, stop_event, generation_string)
        
        if self.engine_name == "coqui" and hasattr(self.engine, 'set_stream_chunk_size') and self.current_stream_chunk_size != FINAL_ANSWER_STREAM_CHUNK_SIZE:
            logger.info(f"👄⚙️ {generation_string} Setting Coqui stream chunk size to {FINAL_ANSWER_STREAM_CHUNK_SIZE} for generator synthesis.")
            self.engine.set_stream_chunk_size(FINAL_ANSWER_STREAM_CHUNK_SIZE)
            self.current_stream_chunk_size = FINAL_ANSWER_STREAM_CHUNK_SIZE

        # Feed the generator to the stream
        self.stream.feed(generator)
        self.finished_event.clear() # Reset finished event

        # Buffering state variables
        buffer: list[bytes] = []
        good_streak: int = 0
        buffering: bool = True
        buf_dur: float = 0.0
        SR, BPS = 24000, 2 # Assumed Sample Rate and Bytes Per Sample
        start = time.time()
        self._final_prev_chunk_time: float = 0.0 # Separate timer for generator synthesis

        def on_audio_chunk(chunk: bytes):
            nonlocal buffer, good_streak, buffering, buf_dur, start
            if stop_event.is_set():
                logger.info(f"👄🛑 {generation_string} Final audio stream interrupted by stop_event.")
                return

            now = time.time()
            samples = len(chunk) // BPS
            play_duration = samples / SR

            # --- Orpheus specific: Skip initial silence ---
            if on_audio_chunk.first_call and self.engine_name == "orpheus":
                if not hasattr(on_audio_chunk, "silent_chunks_count"):
                    on_audio_chunk.silent_chunks_count = 0
                    on_audio_chunk.silent_chunks_time = 0.0
                    # Lower threshold potentially for final answers? Or keep consistent? Using 100 as in original code.
                    on_audio_chunk.silence_threshold = 100

                try:
                    fmt = f"{samples}h"
                    pcm_data = struct.unpack(fmt, chunk)
                    avg_amplitude = np.abs(np.array(pcm_data)).mean()

                    if avg_amplitude < on_audio_chunk.silence_threshold:
                        on_audio_chunk.silent_chunks_count += 1
                        on_audio_chunk.silent_chunks_time += play_duration
                        logger.debug(f"👄⏭️ {generation_string} Final Skipping silent chunk {on_audio_chunk.silent_chunks_count} (avg_amp: {avg_amplitude:.2f})")
                        return # Skip
                    elif on_audio_chunk.silent_chunks_count > 0:
                        logger.info(f"👄⏭️ {generation_string} Final Skipped {on_audio_chunk.silent_chunks_count} silent chunks, saved {on_audio_chunk.silent_chunks_time*1000:.2f}ms")
                except Exception as e:
                    logger.warning(f"👄⚠️ {generation_string} Final Error analyzing audio chunk for silence: {e}")

            # --- Timing and Logging ---
            if on_audio_chunk.first_call:
                on_audio_chunk.first_call = False
                self._final_prev_chunk_time = now
                ttfa_actual = now-start
                logger.info(f"👄🚀 {generation_string} Final audio start. TTFA: {ttfa_actual:.2f}s.")
            else:
                gap = now - self._final_prev_chunk_time
                self._final_prev_chunk_time = now
                if gap <= play_duration * 1.1:
                    # logger.debug(f"👄✅ {generation_string} Final chunk ok (gap={gap:.3f}s ≤ {play_duration:.3f}s).")
                    good_streak += 1
                else:
                    logger.warning(f"👄❌ {generation_string} Final chunk slow (gap={gap:.3f}s > {play_duration:.3f}s).")
                    good_streak = 0

            put_occurred_this_call = False

            # --- Buffering Logic ---
            buffer.append(chunk)
            buf_dur += play_duration
            if buffering:
                if good_streak >= 2 or buf_dur >= 0.5: # Same flush logic as synthesize
                    logger.info(f"👄➡️ {generation_string} Final Flushing buffer (streak={good_streak}, dur={buf_dur:.2f}s).")
                    for c in buffer:
                        try:
                           audio_chunks.put_nowait(c)
                           put_occurred_this_call = True
                        except asyncio.QueueFull:
                            logger.warning(f"👄⚠️ {generation_string} Final audio queue full, dropping chunk.")
                    buffer.clear()
                    buf_dur = 0.0
                    buffering = False
            else: # Not buffering
                try:
                    audio_chunks.put_nowait(chunk)
                    put_occurred_this_call = True
                except asyncio.QueueFull:
                    logger.warning(f"👄⚠️ {generation_string} Final audio queue full, dropping chunk.")


            # --- First Chunk Callback --- (Using the same callback as synthesize)
            if put_occurred_this_call and not on_audio_chunk.callback_fired:
                if self.on_first_audio_chunk_synthesize:
                    try:
                        logger.info(f"👄🚀 {generation_string} Final Firing on_first_audio_chunk_synthesize.")
                        self.on_first_audio_chunk_synthesize()
                    except Exception as e:
                        logger.error(f"👄💥 {generation_string} Final Error in on_first_audio_chunk_synthesize callback: {e}", exc_info=True)
                on_audio_chunk.callback_fired = True

        # Initialize callback state
        on_audio_chunk.first_call = True
        on_audio_chunk.callback_fired = False

        play_kwargs = dict(
            log_synthesized_text=True, # Log text from generator
            on_audio_chunk=on_audio_chunk,
            muted=True,
            fast_sentence_fragment=False,
            comma_silence_duration=self.silence.comma,
            sentence_silence_duration=self.silence.sentence,
            default_silence_duration=self.silence.default,
            force_first_fragment_after_words=999999,
        )

        # Add Orpheus specific parameters for generator streaming
        if self.engine_name == "orpheus":
            # These encourage waiting for more text before synthesizing, potentially better for generators
            play_kwargs["minimum_sentence_length"] = 200
            play_kwargs["minimum_first_fragment_length"] = 200

        logger.info(f"👄▶️ {generation_string} Final Starting synthesis from generator.")
        self.stream.play_async(**play_kwargs)

        # Wait loop for completion or interruption
        while self.stream.is_playing() or not self.finished_event.is_set():
            if stop_event.is_set():
                self.stream.stop()
                logger.info(f"👄🛑 {generation_string} Final answer synthesis aborted by stop_event.")
                buffer.clear()
                self.finished_event.wait(timeout=1.0) # Wait for stream stop confirmation
                return False # Indicate interruption
            time.sleep(0.01)

        # Flush remaining buffer if stream finished before flush condition met
        if buffering and buffer and not stop_event.is_set():
            logger.info(f"👄➡️ {generation_string} Final Flushing remaining buffer after stream finished.")
            for c in buffer:
                try:
                   audio_chunks.put_nowait(c)
                except asyncio.QueueFull:
                   logger.warning(f"👄⚠️ {generation_string} Final audio queue full on final flush, dropping chunk.")
            buffer.clear()

        logger.info(f"👄✅ {generation_string} Final answer synthesis complete.")
        return True # Indicate successful completion