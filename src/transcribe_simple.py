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
                 language: str = "en",
                 model_name: str = "base.en",
                 **kwargs):
        self.language = language
        self.model_name = model_name
        self.model = None
        self.is_recording = False
        self.is_listening = False
        
        # Audio buffer for accumulating chunks
        self.audio_buffer = []
        self.buffer_duration = 0  # in samples
        self.min_buffer_samples = 16000 * 2  # 2 seconds minimum before transcribing
        self.max_buffer_samples = 16000 * 30  # 30 seconds maximum
        
        # Speech detection state
        self.speech_buffer = []  # Accumulated speech across multiple transcriptions
        self.silence_counter = 0  # Count consecutive silent buffers
        self.silence_threshold = 2  # Number of silent buffers before finalizing
        self.has_speech = False  # Track if we've seen any speech
        
        # Callbacks (matching RealtimeSTT interface)
        self.transcription_callback = None
        self.realtime_callback = None
        self.full_transcription_callback = None
        self.realtime_transcription_callback = None
        self.potential_sentence_end = None
        self.potential_full_transcription_callback = None
        self.potential_full_transcription_abort_callback = None
        self.before_final_sentence = None
        self.on_tts_allowed_to_synthesize = None
        
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
            
            # Check audio RMS level for debugging
            rms = np.sqrt(np.mean(audio_data**2))
            logger.debug(f"🎤📊 Audio RMS level: {rms:.6f}")
            
            # Transcribe with less aggressive VAD
            segments, info = self.model.transcribe(
                audio_data,
                language=self.language if self.language != "auto" else None,
                beam_size=5,
                vad_filter=True,
                vad_parameters=dict(
                    threshold=0.3,  # Lower threshold (more sensitive)
                    min_speech_duration_ms=100,  # Shorter minimum speech
                    min_silence_duration_ms=1000,  # Longer before cutting
                    speech_pad_ms=200  # More padding around speech
                )
            )
            
            # Combine segments
            text = " ".join([segment.text.strip() for segment in segments])
            return text.strip()
            
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return ""
    
    def process_audio_chunk(self, audio_chunk: bytes):
        """
        Process incoming audio chunk with speech/silence detection
        Accumulates speech across multiple chunks and only finalizes when silence is detected
        """
        try:
            # Convert bytes to numpy array
            audio_np = np.frombuffer(audio_chunk, dtype=np.int16)
            
            # Add to buffer
            self.audio_buffer.append(audio_np)
            self.buffer_duration += len(audio_np)
            
            # Transcribe when we have enough audio
            if self.buffer_duration >= self.min_buffer_samples:
                logger.info(f"🎤 Transcribing buffer with {self.buffer_duration} samples ({self.buffer_duration/16000:.1f}s)")
                
                # Concatenate all buffered audio
                full_audio = np.concatenate(self.audio_buffer)
                
                # Transcribe
                text = self.transcribe_audio(full_audio)
                
                if text:
                    # Speech detected! Add to speech buffer
                    logger.info(f"🎤✅ Transcribed chunk: {text}")
                    self.speech_buffer.append(text)
                    self.has_speech = True
                    self.silence_counter = 0  # Reset silence counter
                    
                    # Send partial transcription to UI
                    full_text = " ".join(self.speech_buffer)
                    if self.realtime_transcription_callback:
                        self.realtime_transcription_callback(full_text)
                else:
                    # Silence detected
                    logger.debug("🎤 No speech in buffer")
                    if self.has_speech:
                        self.silence_counter += 1
                        logger.debug(f"🎤🔇 Silence counter: {self.silence_counter}/{self.silence_threshold}")
                        
                        # If we've seen enough silence, finalize the transcription
                        if self.silence_counter >= self.silence_threshold:
                            full_text = " ".join(self.speech_buffer).strip()
                            logger.info(f"🎤🏁 Final transcription: {full_text}")
                            
                            # Call final transcription callback
                            if self.full_transcription_callback:
                                self.full_transcription_callback(full_text)
                            if self.transcription_callback:
                                self.transcription_callback(full_text)
                            
                            # Reset speech buffer
                            self.speech_buffer = []
                            self.has_speech = False
                            self.silence_counter = 0
                
                # Clear audio buffer after each transcription attempt
                self.audio_buffer = []
                self.buffer_duration = 0
            
            # Prevent buffer from growing too large
            elif self.buffer_duration >= self.max_buffer_samples:
                logger.warning(f"🎤⚠️ Buffer too large ({self.buffer_duration} samples), forcing transcription")
                full_audio = np.concatenate(self.audio_buffer)
                text = self.transcribe_audio(full_audio)
                if text:
                    self.speech_buffer.append(text)
                self.audio_buffer = []
                self.buffer_duration = 0
                    
        except Exception as e:
            logger.error(f"Error processing audio chunk: {e}", exc_info=True)
    
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
    def feed_audio(self, audio_bytes, audio_array=None):
        """
        Feed audio data (compatibility method)
        Args:
            audio_bytes: Audio data as bytes
            audio_array: Optional audio data as numpy array (ignored for now)
        """
        if isinstance(audio_bytes, bytes):
            self.process_audio_chunk(audio_bytes)
    
    def clear_audio_queue(self):
        """Clear audio queue (compatibility method)"""
        self.audio_buffer = []
        self.buffer_duration = 0
        self.speech_buffer = []
        self.silence_counter = 0
        self.has_speech = False
        logger.debug("🎤 Audio and speech buffers cleared")
    
    def shutdown(self):
        """Shutdown the processor"""
        self.stop()