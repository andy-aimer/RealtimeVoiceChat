"""
Simple transcription processor for production deployment
Uses faster-whisper directly without RealtimeSTT dependencies
"""
import logging
import numpy as np
from faster_whisper import WhisperModel
from typing import Optional, Callable, Any, Dict, List
import threading
import time

logger = logging.getLogger(__name__)

class SimpleTranscriptionProcessor:
    """
    Simplified transcription processor using faster-whisper directly
    For production deployment without wake word detection dependencies
    """
    
    def __init__(self, 
                 model_name: str = "base.en",
                 language: str = "en",
                 **kwargs):
        self.model_name = model_name
        self.language = language
        self.model = None
        self.is_recording = False
        self.is_listening = False
        
        # Callbacks
        self.transcription_callback = None
        self.realtime_callback = None
        
        logger.info(f"Initializing simple transcription with model: {model_name}")
        
    def set_callbacks(self, 
                     transcription_callback: Optional[Callable] = None,
                     realtime_callback: Optional[Callable] = None):
        """Set transcription callbacks"""
        self.transcription_callback = transcription_callback
        self.realtime_callback = realtime_callback
        
    def start(self):
        """Start the transcription processor"""
        try:
            if not self.model:
                logger.info(f"Loading Whisper model: {self.model_name}")
                self.model = WhisperModel(self.model_name, device="cpu")
                logger.info("Whisper model loaded successfully")
            
            self.is_listening = True
            logger.info("Simple transcription processor started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start transcription processor: {e}")
            return False
    
    def stop(self):
        """Stop the transcription processor"""
        self.is_listening = False
        self.is_recording = False
        logger.info("Simple transcription processor stopped")
    
    def transcribe_audio(self, audio_data: np.ndarray, sample_rate: int = 16000) -> str:
        """
        Transcribe audio data directly
        """
        try:
            if not self.model:
                return ""
                
            # Convert audio to format expected by faster-whisper
            # Ensure audio is float32 and normalized
            if audio_data.dtype != np.float32:
                if audio_data.dtype == np.int16:
                    audio_data = audio_data.astype(np.float32) / 32768.0
                else:
                    audio_data = audio_data.astype(np.float32)
            
            # Transcribe
            segments, info = self.model.transcribe(
                audio_data,
                language=self.language if self.language != "auto" else None,
                beam_size=3,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500)
            )
            
            # Combine segments
            text = " ".join([segment.text.strip() for segment in segments])
            return text.strip()
            
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return ""
    
    def process_audio_chunk(self, audio_chunk: bytes):
        """
        Process incoming audio chunk (placeholder for WebSocket audio)
        """
        try:
            # Convert bytes to numpy array
            audio_np = np.frombuffer(audio_chunk, dtype=np.int16)
            
            # For real-time processing, you might want to accumulate audio
            # and transcribe when silence is detected or buffer is full
            if len(audio_np) > 16000:  # At least 1 second of audio
                text = self.transcribe_audio(audio_np)
                if text and self.transcription_callback:
                    self.transcription_callback(text)
                    
        except Exception as e:
            logger.error(f"Error processing audio chunk: {e}")
    
    def transcribe_loop(self):
        """
        Main transcription loop (compatibility method for audio_in.py)
        This is called repeatedly by AudioInputProcessor
        """
        # Since we don't have a real-time streaming model like RealtimeSTT,
        # we just sleep briefly and let the audio processor handle chunks
        # The actual transcription happens in process_audio_chunk when called
        time.sleep(0.1)
        
    # Compatibility methods for existing code
    def feed_audio(self, audio_data):
        """Feed audio data (compatibility method)"""
        if isinstance(audio_data, bytes):
            self.process_audio_chunk(audio_data)
    
    def clear_audio_queue(self):
        """Clear audio queue (compatibility method)"""
        pass
    
    def shutdown(self):
        """Shutdown the processor"""
        self.stop()