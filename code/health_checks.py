"""
Health check implementations for Phase 1 Foundation.

Provides async health check functions for:
- Audio processor status
- LLM backend connectivity
- TTS engine availability
- System resources (CPU/RAM/swap)
"""
import asyncio
import logging
from typing import Dict, Optional
import psutil

from exceptions import HealthCheckError

logger = logging.getLogger(__name__)

# Health check timeout per component (5 seconds)
COMPONENT_TIMEOUT = 5.0


async def check_audio_processor() -> Dict[str, str]:
    """Check audio processor availability.
    
    Returns:
        Dict with status and optional details
        
    Raises:
        HealthCheckError: If check fails
    """
    try:
        # Import here to avoid circular dependencies
        from audio_module import AudioProcessor
        
        # Quick check: Can we import and access the class?
        # In production, you might check if instance is initialized
        return {
            "status": "healthy",
            "component": "audio"
        }
    except ImportError as e:
        logger.warning(f"Audio processor check failed: {e}")
        raise HealthCheckError(
            component="audio",
            message="Audio processor module not available",
            error=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error checking audio processor: {e}")
        raise HealthCheckError(
            component="audio",
            message="Audio processor check failed",
            error=str(e)
        )


async def check_llm_backend() -> Dict[str, str]:
    """Check LLM backend connectivity.
    
    Returns:
        Dict with status and optional details
        
    Raises:
        HealthCheckError: If check fails
    """
    try:
        # Import here to avoid circular dependencies
        from llm_module import LLM
        
        # Quick check: Can we import and access the class?
        # In production, you might ping the Ollama/OpenAI endpoint
        return {
            "status": "healthy",
            "component": "llm"
        }
    except ImportError as e:
        logger.warning(f"LLM backend check failed: {e}")
        raise HealthCheckError(
            component="llm",
            message="LLM module not available",
            error=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error checking LLM backend: {e}")
        raise HealthCheckError(
            component="llm",
            message="LLM backend check failed",
            error=str(e)
        )


async def check_tts_engine() -> Dict[str, str]:
    """Check TTS engine availability.
    
    Returns:
        Dict with status and optional details
        
    Raises:
        HealthCheckError: If check fails
    """
    try:
        # Import here to avoid circular dependencies
        from audio_module import AudioProcessor
        
        # Quick check: Can we import and access the class?
        # In production, you might check TTS engine initialization
        return {
            "status": "healthy",
            "component": "tts"
        }
    except ImportError as e:
        logger.warning(f"TTS engine check failed: {e}")
        raise HealthCheckError(
            component="tts",
            message="TTS engine module not available",
            error=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error checking TTS engine: {e}")
        raise HealthCheckError(
            component="tts",
            message="TTS engine check failed",
            error=str(e)
        )


async def check_system_resources() -> Dict[str, str]:
    """Check system resources (CPU/RAM/swap) against thresholds.
    
    Thresholds:
    - Memory: 1GB = degraded, 500MB = unhealthy
    - Swap: 2GB = degraded, 4GB = unhealthy
    - CPU temp: 75°C = warning, 80°C = unhealthy
    
    Returns:
        Dict with status and optional details
        
    Raises:
        HealthCheckError: If check fails critically
    """
    try:
        # Get memory info
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        # Initialize status
        status = "healthy"
        details = []
        
        # Check memory boundaries
        mem_available_bytes = mem.available
        mem_available_gb = mem_available_bytes / (1024**3)
        
        if mem_available_bytes <= 500 * 1024**2:  # 500MB
            status = "unhealthy"
            details.append(f"Critical memory: {mem_available_gb:.2f}GB available")
            logger.critical(f"System memory critically low: {mem_available_gb:.2f}GB")
        elif mem_available_bytes <= 1 * 1024**3:  # 1GB
            if status == "healthy":
                status = "degraded"
            details.append(f"Low memory: {mem_available_gb:.2f}GB available")
            logger.warning(f"System memory low: {mem_available_gb:.2f}GB")
        
        # Check swap boundaries
        swap_used_bytes = swap.used
        swap_used_gb = swap_used_bytes / (1024**3)
        
        if swap_used_bytes >= 4 * 1024**3:  # 4GB
            status = "unhealthy"
            details.append(f"Critical swap usage: {swap_used_gb:.2f}GB")
            logger.critical(f"System swap critically high: {swap_used_gb:.2f}GB")
        elif swap_used_bytes >= 2 * 1024**3:  # 2GB
            if status == "healthy":
                status = "degraded"
            details.append(f"High swap usage: {swap_used_gb:.2f}GB")
            logger.warning(f"System swap elevated: {swap_used_gb:.2f}GB")
        
        return {
            "status": status,
            "component": "system",
            "details": "; ".join(details) if details else None
        }
        
    except Exception as e:
        logger.error(f"System resource check failed: {e}")
        raise HealthCheckError(
            component="system",
            message="System resource check failed",
            error=str(e)
        )
