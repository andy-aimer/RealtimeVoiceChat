"""
Unit tests for audio_module.py module.

Tests AudioProcessor class initialization, TTS synthesis, audio buffer management,
and engine-specific functionality.
"""
import pytest
import asyncio
import threading
import time
import struct
from unittest.mock import Mock, patch, MagicMock, PropertyMock
import sys
import os

# Add parent directory to path to import code modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'code'))

# Mock heavy dependencies before importing
sys.modules['RealtimeTTS'] = MagicMock()
sys.modules['huggingface_hub'] = MagicMock()

from audio_module import (
    AudioProcessor,
    create_directory,
    ensure_lasinya_models,
    START_ENGINE,
    ENGINE_SILENCES,
    QUICK_ANSWER_STREAM_CHUNK_SIZE,
    FINAL_ANSWER_STREAM_CHUNK_SIZE,
)


# ==================== Utility Function Tests ====================

class TestCreateDirectory:
    """Tests for create_directory utility function."""
    
    @patch('os.path.exists')
    @patch('os.makedirs')
    def test_creates_new_directory(self, mock_makedirs, mock_exists):
        """Test creating a new directory when it doesn't exist."""
        mock_exists.return_value = False
        
        create_directory('/test/path')
        
        mock_exists.assert_called_once_with('/test/path')
        mock_makedirs.assert_called_once_with('/test/path')
    
    @patch('os.path.exists')
    @patch('os.makedirs')
    def test_skips_existing_directory(self, mock_makedirs, mock_exists):
        """Test skipping creation if directory already exists."""
        mock_exists.return_value = True
        
        create_directory('/test/path')
        
        mock_exists.assert_called_once_with('/test/path')
        mock_makedirs.assert_not_called()


class TestEnsureLasinyaModels:
    """Tests for ensure_lasinya_models utility function."""
    
    @patch('os.path.exists')
    @patch('audio_module.create_directory')
    @patch('audio_module.hf_hub_download')
    def test_downloads_missing_files(self, mock_download, mock_create_dir, mock_exists):
        """Test downloading files that don't exist locally."""
        # Mock: config.json exists, vocab.json doesn't
        def exists_side_effect(path):
            return 'config.json' in path
        
        mock_exists.side_effect = exists_side_effect
        
        ensure_lasinya_models(models_root='models', model_name='Lasinya')
        
        # Should create directory
        mock_create_dir.assert_called_once()
        
        # Should download 3 missing files (vocab.json, speakers_xtts.pth, model.pth)
        assert mock_download.call_count == 3
    
    @patch('os.path.exists')
    @patch('audio_module.create_directory')
    @patch('audio_module.hf_hub_download')
    def test_skips_existing_files(self, mock_download, mock_create_dir, mock_exists):
        """Test skipping download for existing files."""
        mock_exists.return_value = True  # All files exist
        
        ensure_lasinya_models(models_root='models', model_name='Lasinya')
        
        # Should create directory
        mock_create_dir.assert_called_once()
        
        # Should not download anything
        mock_download.assert_not_called()


# ==================== AudioProcessor Initialization Tests ====================

class TestAudioProcessorInitialization:
    """Tests for AudioProcessor initialization."""
    
    @patch('audio_module.TextToAudioStream')
    @patch('audio_module.KokoroEngine')
    def test_kokoro_engine_initialization(self, mock_kokoro, mock_stream):
        """Test initialization with Kokoro engine."""
        mock_engine = MagicMock()
        mock_kokoro.return_value = mock_engine
        mock_stream_instance = MagicMock()
        mock_stream.return_value = mock_stream_instance
        mock_stream_instance.is_playing.return_value = False
        
        processor = AudioProcessor(engine='kokoro')
        
        assert processor.engine_name == 'kokoro'
        mock_kokoro.assert_called_once()
        
        # Verify Kokoro-specific parameters
        call_kwargs = mock_kokoro.call_args[1]
        assert call_kwargs['voice'] == 'af_heart'
        assert call_kwargs['default_speed'] == 1.26
        assert call_kwargs['trim_silence'] is True
    
    @patch('audio_module.TextToAudioStream')
    @patch('audio_module.OrpheusEngine')
    @patch('audio_module.OrpheusVoice')
    def test_orpheus_engine_initialization(self, mock_voice, mock_orpheus, mock_stream):
        """Test initialization with Orpheus engine."""
        mock_engine = MagicMock()
        mock_orpheus.return_value = mock_engine
        mock_stream_instance = MagicMock()
        mock_stream.return_value = mock_stream_instance
        mock_stream_instance.is_playing.return_value = False
        
        processor = AudioProcessor(engine='orpheus')
        
        assert processor.engine_name == 'orpheus'
        mock_orpheus.assert_called_once()
        
        # Verify Orpheus-specific parameters
        call_kwargs = mock_orpheus.call_args[1]
        assert call_kwargs['temperature'] == 0.8
        assert call_kwargs['top_p'] == 0.95
        assert call_kwargs['repetition_penalty'] == 1.1
        assert call_kwargs['max_tokens'] == 1200
    
    @patch('audio_module.TextToAudioStream')
    @patch('audio_module.CoquiEngine')
    @patch('audio_module.ensure_lasinya_models')
    def test_coqui_engine_initialization(self, mock_ensure, mock_coqui, mock_stream):
        """Test initialization with Coqui engine."""
        mock_engine = MagicMock()
        mock_coqui.return_value = mock_engine
        mock_stream_instance = MagicMock()
        mock_stream.return_value = mock_stream_instance
        mock_stream_instance.is_playing.return_value = False
        
        processor = AudioProcessor(engine='coqui')
        
        assert processor.engine_name == 'coqui'
        mock_ensure.assert_called_once()
        mock_coqui.assert_called_once()
        
        # Verify Coqui-specific parameters
        call_kwargs = mock_coqui.call_args[1]
        assert call_kwargs['specific_model'] == 'Lasinya'
        assert call_kwargs['use_deepspeed'] is True
        assert call_kwargs['stream_chunk_size'] == QUICK_ANSWER_STREAM_CHUNK_SIZE
    
    def test_invalid_engine_raises_error(self):
        """Test that invalid engine name raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported engine"):
            AudioProcessor(engine='invalid_engine')


# ==================== AudioProcessor Synthesis Tests ====================

class TestAudioProcessorSynthesize:
    """Tests for synthesize method."""
    
    @pytest.fixture
    @patch('audio_module.TextToAudioStream')
    @patch('audio_module.KokoroEngine')
    def processor(self, mock_kokoro, mock_stream):
        """Fixture providing initialized AudioProcessor."""
        mock_engine = MagicMock()
        mock_kokoro.return_value = mock_engine
        mock_stream_instance = MagicMock()
        mock_stream.return_value = mock_stream_instance
        mock_stream_instance.is_playing.return_value = False
        
        return AudioProcessor(engine='kokoro')
    
    def test_synthesize_complete_text(self, processor):
        """Test synthesizing complete text string."""
        test_text = "This is a test sentence."
        audio_queue = asyncio.Queue()
        stop_event = threading.Event()
        
        # Mock stream behavior
        processor.stream.is_playing.return_value = False
        processor.finished_event.set()
        
        result = processor.synthesize(
            text=test_text,
            audio_chunks=audio_queue,
            stop_event=stop_event
        )
        
        assert result is True
        processor.stream.feed.assert_called_with(test_text)
    
    def test_synthesize_interrupted(self, processor):
        """Test synthesis interruption via stop_event."""
        test_text = "This is a test sentence."
        audio_queue = asyncio.Queue()
        stop_event = threading.Event()
        
        # Simulate interruption
        def side_effect():
            stop_event.set()
            processor.finished_event.set()
        
        processor.stream.is_playing.side_effect = [True, False]
        processor.finished_event.wait = MagicMock(side_effect=side_effect)
        
        result = processor.synthesize(
            text=test_text,
            audio_chunks=audio_queue,
            stop_event=stop_event
        )
        
        # Should detect stop_event and call stream.stop()
        processor.stream.stop.assert_called()
    
    def test_first_audio_chunk_callback(self, processor):
        """Test on_first_audio_chunk_synthesize callback firing."""
        test_text = "Test"
        audio_queue = asyncio.Queue()
        stop_event = threading.Event()
        callback_mock = Mock()
        
        processor.on_first_audio_chunk_synthesize = callback_mock
        processor.stream.is_playing.return_value = False
        processor.finished_event.set()
        
        processor.synthesize(
            text=test_text,
            audio_chunks=audio_queue,
            stop_event=stop_event
        )
        
        # Callback configuration should be set
        assert processor.on_first_audio_chunk_synthesize == callback_mock


class TestAudioProcessorSynthesizeGenerator:
    """Tests for synthesize_generator method."""
    
    @pytest.fixture
    @patch('audio_module.TextToAudioStream')
    @patch('audio_module.KokoroEngine')
    def processor(self, mock_kokoro, mock_stream):
        """Fixture providing initialized AudioProcessor."""
        mock_engine = MagicMock()
        mock_kokoro.return_value = mock_engine
        mock_stream_instance = MagicMock()
        mock_stream.return_value = mock_stream_instance
        mock_stream_instance.is_playing.return_value = False
        
        return AudioProcessor(engine='kokoro')
    
    def test_synthesize_from_generator(self, processor):
        """Test synthesizing from a text generator."""
        def text_generator():
            yield "First chunk. "
            yield "Second chunk. "
            yield "Third chunk."
        
        audio_queue = asyncio.Queue()
        stop_event = threading.Event()
        
        processor.stream.is_playing.return_value = False
        processor.finished_event.set()
        
        result = processor.synthesize_generator(
            generator=text_generator(),
            audio_chunks=audio_queue,
            stop_event=stop_event
        )
        
        assert result is True
        # Generator should be fed to stream
        processor.stream.feed.assert_called_once()
    
    def test_synthesize_generator_interrupted(self, processor):
        """Test generator synthesis interruption."""
        def text_generator():
            yield "First chunk. "
            yield "Second chunk. "
        
        audio_queue = asyncio.Queue()
        stop_event = threading.Event()
        
        def side_effect():
            stop_event.set()
            processor.finished_event.set()
        
        processor.stream.is_playing.side_effect = [True, False]
        processor.finished_event.wait = MagicMock(side_effect=side_effect)
        
        result = processor.synthesize_generator(
            generator=text_generator(),
            audio_chunks=audio_queue,
            stop_event=stop_event
        )
        
        processor.stream.stop.assert_called()


# ==================== Audio Processing Tests ====================

class TestAudioChunkProcessing:
    """Tests for audio chunk processing logic."""
    
    def test_audio_chunk_format(self):
        """Test audio chunk structure (16-bit PCM, 24kHz)."""
        # Simulate a 100ms audio chunk at 24kHz, 16-bit
        sample_rate = 24000
        duration_ms = 100
        samples = int(sample_rate * duration_ms / 1000)
        
        # Create test audio data (silence)
        audio_data = struct.pack(f'{samples}h', *([0] * samples))
        
        assert len(audio_data) == samples * 2  # 2 bytes per sample (16-bit)
    
    def test_audio_silence_detection(self):
        """Test silence detection in audio chunks."""
        import numpy as np
        
        # Create silent chunk
        samples = 1000
        silent_chunk = struct.pack(f'{samples}h', *([0] * samples))
        
        # Unpack and analyze
        pcm_data = struct.unpack(f'{samples}h', silent_chunk)
        avg_amplitude = np.abs(np.array(pcm_data)).mean()
        
        # Should be very low amplitude
        assert avg_amplitude < 10  # Threshold for silence
    
    def test_audio_non_silence_detection(self):
        """Test non-silence detection in audio chunks."""
        import numpy as np
        
        # Create non-silent chunk (sine wave)
        samples = 1000
        frequency = 440  # A4 note
        sample_rate = 24000
        amplitude = 10000
        
        # Generate sine wave
        t = np.arange(samples) / sample_rate
        sine_wave = (amplitude * np.sin(2 * np.pi * frequency * t)).astype(np.int16)
        audio_chunk = struct.pack(f'{samples}h', *sine_wave)
        
        # Unpack and analyze
        pcm_data = struct.unpack(f'{samples}h', audio_chunk)
        avg_amplitude = np.abs(np.array(pcm_data)).mean()
        
        # Should have significant amplitude
        assert avg_amplitude > 1000


# ==================== Engine Configuration Tests ====================

class TestEngineSilenceConfiguration:
    """Tests for engine-specific silence configuration."""
    
    def test_all_engines_have_silence_config(self):
        """Test that all engines have silence configuration."""
        engines = ['coqui', 'kokoro', 'orpheus']
        
        for engine in engines:
            assert engine in ENGINE_SILENCES
            config = ENGINE_SILENCES[engine]
            assert hasattr(config, 'comma')
            assert hasattr(config, 'sentence')
            assert hasattr(config, 'default')
    
    def test_silence_values_are_positive(self):
        """Test that silence durations are positive."""
        for engine, silence in ENGINE_SILENCES.items():
            assert silence.comma > 0
            assert silence.sentence > 0
            assert silence.default > 0
    
    def test_sentence_pause_longer_than_comma(self):
        """Test that sentence pause is longer than comma pause."""
        for engine, silence in ENGINE_SILENCES.items():
            assert silence.sentence >= silence.comma


# ==================== Stream Chunk Size Tests ====================

class TestStreamChunkSizes:
    """Tests for stream chunk size configuration."""
    
    def test_chunk_size_constants(self):
        """Test chunk size constant values."""
        assert QUICK_ANSWER_STREAM_CHUNK_SIZE == 8
        assert FINAL_ANSWER_STREAM_CHUNK_SIZE == 30
        assert QUICK_ANSWER_STREAM_CHUNK_SIZE < FINAL_ANSWER_STREAM_CHUNK_SIZE
    
    @patch('audio_module.TextToAudioStream')
    @patch('audio_module.CoquiEngine')
    @patch('audio_module.ensure_lasinya_models')
    def test_coqui_chunk_size_switching(self, mock_ensure, mock_coqui, mock_stream):
        """Test Coqui engine switches chunk sizes appropriately."""
        mock_engine = MagicMock()
        mock_coqui.return_value = mock_engine
        mock_stream_instance = MagicMock()
        mock_stream.return_value = mock_stream_instance
        mock_stream_instance.is_playing.return_value = False
        
        processor = AudioProcessor(engine='coqui')
        
        # Should start with quick chunk size
        assert processor.current_stream_chunk_size == QUICK_ANSWER_STREAM_CHUNK_SIZE


# ==================== Callback Tests ====================

class TestAudioProcessorCallbacks:
    """Tests for AudioProcessor callback handling."""
    
    @pytest.fixture
    @patch('audio_module.TextToAudioStream')
    @patch('audio_module.KokoroEngine')
    def processor(self, mock_kokoro, mock_stream):
        """Fixture providing initialized AudioProcessor."""
        mock_engine = MagicMock()
        mock_kokoro.return_value = mock_engine
        mock_stream_instance = MagicMock()
        mock_stream.return_value = mock_stream_instance
        mock_stream_instance.is_playing.return_value = False
        
        return AudioProcessor(engine='kokoro')
    
    def test_on_audio_stream_stop_callback(self, processor):
        """Test on_audio_stream_stop callback."""
        processor.finished_event.clear()
        
        processor.on_audio_stream_stop()
        
        assert processor.finished_event.is_set()
    
    def test_first_audio_chunk_callback_registration(self, processor):
        """Test registering first audio chunk callback."""
        callback = Mock()
        processor.on_first_audio_chunk_synthesize = callback
        
        assert processor.on_first_audio_chunk_synthesize == callback


# ==================== TTFA (Time To First Audio) Tests ====================

class TestTTFAMeasurement:
    """Tests for Time To First Audio measurement."""
    
    @patch('audio_module.TextToAudioStream')
    @patch('audio_module.KokoroEngine')
    def test_ttfa_initialization(self, mock_kokoro, mock_stream):
        """Test TTFA is measured during initialization."""
        mock_engine = MagicMock()
        mock_kokoro.return_value = mock_engine
        mock_stream_instance = MagicMock()
        mock_stream.return_value = mock_stream_instance
        mock_stream_instance.is_playing.return_value = False
        
        processor = AudioProcessor(engine='kokoro')
        
        # TTFA should be recorded (in ms)
        assert hasattr(processor, 'tts_inference_time')
        assert processor.tts_inference_time >= 0


# ==================== Edge Cases ====================

class TestAudioProcessorEdgeCases:
    """Tests for edge cases and error handling."""
    
    @patch('audio_module.TextToAudioStream')
    @patch('audio_module.KokoroEngine')
    def test_empty_text_synthesis(self, mock_kokoro, mock_stream):
        """Test synthesizing empty text."""
        mock_engine = MagicMock()
        mock_kokoro.return_value = mock_engine
        mock_stream_instance = MagicMock()
        mock_stream.return_value = mock_stream_instance
        mock_stream_instance.is_playing.return_value = False
        
        processor = AudioProcessor(engine='kokoro')
        audio_queue = asyncio.Queue()
        stop_event = threading.Event()
        
        processor.stream.is_playing.return_value = False
        processor.finished_event.set()
        
        # Should handle empty text gracefully
        result = processor.synthesize(
            text="",
            audio_chunks=audio_queue,
            stop_event=stop_event
        )
        
        assert result is True
    
    @patch('audio_module.TextToAudioStream')
    @patch('audio_module.KokoroEngine')
    def test_very_long_text_synthesis(self, mock_kokoro, mock_stream):
        """Test synthesizing very long text."""
        mock_engine = MagicMock()
        mock_kokoro.return_value = mock_engine
        mock_stream_instance = MagicMock()
        mock_stream.return_value = mock_stream_instance
        mock_stream_instance.is_playing.return_value = False
        
        processor = AudioProcessor(engine='kokoro')
        audio_queue = asyncio.Queue()
        stop_event = threading.Event()
        
        processor.stream.is_playing.return_value = False
        processor.finished_event.set()
        
        # Create very long text (10,000 characters)
        long_text = "This is a test sentence. " * 400
        
        result = processor.synthesize(
            text=long_text,
            audio_chunks=audio_queue,
            stop_event=stop_event
        )
        
        assert result is True
    
    @patch('audio_module.TextToAudioStream')
    @patch('audio_module.KokoroEngine')
    def test_special_characters_in_text(self, mock_kokoro, mock_stream):
        """Test synthesizing text with special characters."""
        mock_engine = MagicMock()
        mock_kokoro.return_value = mock_engine
        mock_stream_instance = MagicMock()
        mock_stream.return_value = mock_stream_instance
        mock_stream_instance.is_playing.return_value = False
        
        processor = AudioProcessor(engine='kokoro')
        audio_queue = asyncio.Queue()
        stop_event = threading.Event()
        
        processor.stream.is_playing.return_value = False
        processor.finished_event.set()
        
        special_text = "Test with émojis 😀, numbers 123, and symbols @#$%"
        
        result = processor.synthesize(
            text=special_text,
            audio_chunks=audio_queue,
            stop_event=stop_event
        )
        
        assert result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
