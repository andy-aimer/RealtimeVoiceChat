"""
Raspberry Pi 5 Specific Configuration
Optimized for ARM64 and limited resources
"""

import os
from production.production_config import ProductionConfig

class Pi5Config(ProductionConfig):
    """Pi 5 optimized configuration."""
    
    def __init__(self):
        # Set Pi-specific defaults before parent init
        self.set_pi5_defaults()
        super().__init__()
        self.apply_pi5_optimizations()
    
    def set_pi5_defaults(self):
        """Set Pi 5 specific default values."""
        # Resource constraints for Pi 5
        os.environ.setdefault('PROD_MAX_WORKERS', '2')  # Limit workers
        os.environ.setdefault('PROD_MAX_CONNECTIONS', '50')  # Reduce connections
        os.environ.setdefault('PROD_MEMORY_LIMIT', '1GB')  # Memory limit
        
        # Pi-specific paths
        os.environ.setdefault('PROD_SSL_CERT_PATH', '/home/pi/ssl/server.crt')
        os.environ.setdefault('PROD_SSL_KEY_PATH', '/home/pi/ssl/server.key')
        os.environ.setdefault('PROD_LOG_DIR', '/home/pi/logs/realtimevoicechat')
        
        # Network settings for Pi
        os.environ.setdefault('PROD_HOST', '0.0.0.0')
        os.environ.setdefault('PROD_PORT', '8000')
        os.environ.setdefault('PROD_SSL_PORT', '8443')
        
        # Performance tuning
        os.environ.setdefault('PROD_WEBSOCKET_PING_INTERVAL', '30')
        os.environ.setdefault('PROD_WEBSOCKET_PING_TIMEOUT', '10')
        os.environ.setdefault('PROD_RATE_LIMIT_PER_MINUTE', '100')
    
    def apply_pi5_optimizations(self):
        """Apply Pi 5 specific optimizations."""
        # Audio optimizations for Pi
        self.AUDIO_BUFFER_SIZE = 2048  # Larger buffer for stability
        self.AUDIO_SAMPLE_RATE = 16000  # Lower sample rate
        self.AUDIO_CHANNELS = 1  # Mono for efficiency
        
        # WebSocket optimizations
        self.WEBSOCKET_COMPRESSION = True  # Enable compression
        self.WEBSOCKET_MAX_MESSAGE_SIZE = 1024 * 512  # 512KB limit
        
        # Processing optimizations
        self.MAX_CONCURRENT_SESSIONS = 10  # Limit concurrent sessions
        self.THERMAL_THROTTLE_TEMP = 70  # Lower thermal threshold
        
        # Memory optimizations
        self.ENABLE_MEMORY_MONITORING = True
        self.MEMORY_WARNING_THRESHOLD = 0.8  # 80% memory warning

# Create global instance
pi5_config = Pi5Config()