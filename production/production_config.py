"""
Production Configuration for RealtimeVoiceChat
Implements security recommendations from Phase 2 P4 audit
"""

import os
import ssl
from typing import Optional, Dict, Any
from pathlib import Path

class ProductionConfig:
    """Production-grade configuration with security hardening."""
    
    def __init__(self):
        self.load_environment_variables()
        # Skip validation in test mode
        if not os.getenv('PROD_TEST_MODE', '').lower() == 'true':
            self.validate_configuration()
    
    def load_environment_variables(self):
        """Load configuration from environment variables."""
        
        # Server Configuration
        self.HOST = os.getenv('PROD_HOST', '0.0.0.0')
        self.PORT = int(os.getenv('PROD_PORT', '8000'))
        self.SSL_PORT = int(os.getenv('PROD_SSL_PORT', '8443'))
        
        # SSL/TLS Configuration
        self.USE_SSL = os.getenv('PROD_USE_SSL', 'true').lower() == 'true'
        self.SSL_CERT_PATH = os.getenv('PROD_SSL_CERT_PATH', '/etc/ssl/certs/server.crt')
        self.SSL_KEY_PATH = os.getenv('PROD_SSL_KEY_PATH', '/etc/ssl/private/server.key')
        
        # Security Configuration
        self.RATE_LIMIT_ENABLED = os.getenv('PROD_RATE_LIMIT_ENABLED', 'true').lower() == 'true'
        self.RATE_LIMIT_REQUESTS = int(os.getenv('PROD_RATE_LIMIT_REQUESTS', '100'))
        self.RATE_LIMIT_WINDOW = int(os.getenv('PROD_RATE_LIMIT_WINDOW', '60'))  # seconds
        
        # Authentication Configuration
        self.AUTH_ENABLED = os.getenv('PROD_AUTH_ENABLED', 'false').lower() == 'true'
        self.AUTH_SECRET_KEY = os.getenv('PROD_AUTH_SECRET_KEY', 'change-me-in-production')
        self.AUTH_ALGORITHM = os.getenv('PROD_AUTH_ALGORITHM', 'HS256')
        self.AUTH_TOKEN_EXPIRE_MINUTES = int(os.getenv('PROD_AUTH_TOKEN_EXPIRE_MINUTES', '30'))
        
        # CORS Configuration
        self.CORS_ORIGINS = os.getenv('PROD_CORS_ORIGINS', 'https://localhost:8443').split(',')
        self.CORS_CREDENTIALS = os.getenv('PROD_CORS_CREDENTIALS', 'true').lower() == 'true'
        
        # WebSocket Configuration
        self.WS_MAX_SIZE = int(os.getenv('PROD_WS_MAX_SIZE', '1048576'))  # 1MB
        self.WS_PING_INTERVAL = int(os.getenv('PROD_WS_PING_INTERVAL', '30'))
        self.WS_PING_TIMEOUT = int(os.getenv('PROD_WS_PING_TIMEOUT', '10'))
        self.WS_CLOSE_TIMEOUT = int(os.getenv('PROD_WS_CLOSE_TIMEOUT', '10'))
        
        # Session Configuration
        self.SESSION_TIMEOUT = int(os.getenv('PROD_SESSION_TIMEOUT', '300'))  # 5 minutes
        self.SESSION_MAX_CONCURRENT = int(os.getenv('PROD_SESSION_MAX_CONCURRENT', '100'))
        
        # Monitoring Configuration
        self.MONITOR_HOST = os.getenv('PROD_MONITOR_HOST', '127.0.0.1')  # Internal only
        self.MONITOR_PORT = int(os.getenv('PROD_MONITOR_PORT', '8001'))
        self.METRICS_ENABLED = os.getenv('PROD_METRICS_ENABLED', 'true').lower() == 'true'
        
        # Logging Configuration
        self.LOG_LEVEL = os.getenv('PROD_LOG_LEVEL', 'INFO')
        self.LOG_FORMAT = os.getenv('PROD_LOG_FORMAT', 'json')
        self.LOG_FILE = os.getenv('PROD_LOG_FILE', '/var/log/realtimevoicechat/app.log')
        
        # Performance Configuration
        self.WORKERS = int(os.getenv('PROD_WORKERS', '2'))
        self.WORKER_CLASS = os.getenv('PROD_WORKER_CLASS', 'uvicorn.workers.UvicornWorker')
        self.WORKER_CONNECTIONS = int(os.getenv('PROD_WORKER_CONNECTIONS', '1000'))
        
        # Security Headers
        self.SECURITY_HEADERS = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'Content-Security-Policy': self._get_csp_header(),
            'Referrer-Policy': 'strict-origin-when-cross-origin'
        }
    
    def _get_csp_header(self) -> str:
        """Generate Content Security Policy header."""
        csp_parts = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline'",  # Needed for WebSocket inline scripts
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data:",
            "connect-src 'self' ws: wss:",  # WebSocket connections
            "media-src 'self'",
            "object-src 'none'",
            "base-uri 'self'",
            "form-action 'self'"
        ]
        return "; ".join(csp_parts)
    
    def validate_configuration(self):
        """Validate production configuration."""
        errors = []
        
        # SSL Certificate validation
        if self.USE_SSL:
            if not os.path.exists(self.SSL_CERT_PATH):
                errors.append(f"SSL certificate not found: {self.SSL_CERT_PATH}")
            if not os.path.exists(self.SSL_KEY_PATH):
                errors.append(f"SSL private key not found: {self.SSL_KEY_PATH}")
        
        # Authentication validation
        if self.AUTH_ENABLED:
            if self.AUTH_SECRET_KEY == 'change-me-in-production':
                errors.append("AUTH_SECRET_KEY must be changed for production")
            if len(self.AUTH_SECRET_KEY) < 32:
                errors.append("AUTH_SECRET_KEY must be at least 32 characters")
        
        # Rate limiting validation
        if self.RATE_LIMIT_REQUESTS <= 0:
            errors.append("RATE_LIMIT_REQUESTS must be positive")
        
        # Log directory validation
        log_dir = Path(self.LOG_FILE).parent
        if not log_dir.exists():
            try:
                log_dir.mkdir(parents=True, exist_ok=True)
            except PermissionError:
                errors.append(f"Cannot create log directory: {log_dir}")
        
        if errors:
            raise ValueError(f"Production configuration errors: {'; '.join(errors)}")
    
    def get_ssl_context(self) -> Optional[ssl.SSLContext]:
        """Create SSL context for HTTPS/WSS."""
        if not self.USE_SSL:
            return None
        
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(self.SSL_CERT_PATH, self.SSL_KEY_PATH)
        
        # Security hardening
        context.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS')
        context.options |= ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3 | ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1
        
        return context
    
    def get_uvicorn_config(self) -> Dict[str, Any]:
        """Get Uvicorn server configuration."""
        config = {
            'host': self.HOST,
            'port': self.SSL_PORT if self.USE_SSL else self.PORT,
            'workers': self.WORKERS,
            'log_level': self.LOG_LEVEL.lower(),
            'access_log': True,
            'server_header': False,  # Don't reveal server info
            'date_header': False
        }
        
        if self.USE_SSL:
            config.update({
                'ssl_keyfile': self.SSL_KEY_PATH,
                'ssl_certfile': self.SSL_CERT_PATH,
                'ssl_version': ssl.PROTOCOL_TLS_SERVER,
                'ssl_cert_reqs': ssl.CERT_NONE,
                'ssl_ca_certs': None,
                'ssl_ciphers': 'TLSv1.2'
            })
        
        return config
    
    def get_gunicorn_config(self) -> Dict[str, Any]:
        """Get Gunicorn configuration for production deployment."""
        config = {
            'bind': f"{self.HOST}:{self.SSL_PORT if self.USE_SSL else self.PORT}",
            'workers': self.WORKERS,
            'worker_class': self.WORKER_CLASS,
            'worker_connections': self.WORKER_CONNECTIONS,
            'max_requests': 1000,
            'max_requests_jitter': 100,
            'timeout': 30,
            'keepalive': 2,
            'preload_app': True,
            'user': 'www-data',
            'group': 'www-data',
            'tmp_upload_dir': None,
            'logconfig_dict': self._get_logging_config(),
            'capture_output': True,
            'enable_stdio_inheritance': True
        }
        
        if self.USE_SSL:
            config.update({
                'keyfile': self.SSL_KEY_PATH,
                'certfile': self.SSL_CERT_PATH,
                'ssl_version': ssl.PROTOCOL_TLS_SERVER,
                'ciphers': 'TLSv1.2'
            })
        
        return config
    
    def _get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration."""
        return {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'json': {
                    'format': '%(asctime)s %(name)s %(levelname)s %(message)s',
                    'class': 'pythonjsonlogger.jsonlogger.JsonFormatter'
                },
                'standard': {
                    'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
                }
            },
            'handlers': {
                'default': {
                    'level': self.LOG_LEVEL,
                    'formatter': self.LOG_FORMAT,
                    'class': 'logging.StreamHandler',
                    'stream': 'ext://sys.stdout'
                },
                'file': {
                    'level': self.LOG_LEVEL,
                    'formatter': self.LOG_FORMAT,
                    'class': 'logging.handlers.RotatingFileHandler',
                    'filename': self.LOG_FILE,
                    'maxBytes': 10485760,  # 10MB
                    'backupCount': 5
                }
            },
            'loggers': {
                'gunicorn.error': {
                    'level': self.LOG_LEVEL,
                    'handlers': ['default', 'file'],
                    'propagate': False
                },
                'gunicorn.access': {
                    'level': self.LOG_LEVEL,
                    'handlers': ['default', 'file'],
                    'propagate': False
                },
                'uvicorn.error': {
                    'level': self.LOG_LEVEL,
                    'handlers': ['default', 'file'],
                    'propagate': False
                },
                'uvicorn.access': {
                    'level': self.LOG_LEVEL,
                    'handlers': ['default', 'file'],
                    'propagate': False
                }
            },
            'root': {
                'level': self.LOG_LEVEL,
                'handlers': ['default', 'file']
            }
        }
    
    def export_env_template(self, filepath: str = '.env.production'):
        """Export environment variables template."""
        template = f"""# Production Configuration for RealtimeVoiceChat
# Copy this file to .env and customize for your deployment

# Server Configuration
PROD_HOST={self.HOST}
PROD_PORT={self.PORT}
PROD_SSL_PORT={self.SSL_PORT}

# SSL/TLS Configuration
PROD_USE_SSL={str(self.USE_SSL).lower()}
PROD_SSL_CERT_PATH={self.SSL_CERT_PATH}
PROD_SSL_KEY_PATH={self.SSL_KEY_PATH}

# Security Configuration
PROD_RATE_LIMIT_ENABLED={str(self.RATE_LIMIT_ENABLED).lower()}
PROD_RATE_LIMIT_REQUESTS={self.RATE_LIMIT_REQUESTS}
PROD_RATE_LIMIT_WINDOW={self.RATE_LIMIT_WINDOW}

# Authentication Configuration (optional)
PROD_AUTH_ENABLED={str(self.AUTH_ENABLED).lower()}
PROD_AUTH_SECRET_KEY={self.AUTH_SECRET_KEY}
PROD_AUTH_ALGORITHM={self.AUTH_ALGORITHM}
PROD_AUTH_TOKEN_EXPIRE_MINUTES={self.AUTH_TOKEN_EXPIRE_MINUTES}

# CORS Configuration
PROD_CORS_ORIGINS={','.join(self.CORS_ORIGINS)}
PROD_CORS_CREDENTIALS={str(self.CORS_CREDENTIALS).lower()}

# WebSocket Configuration
PROD_WS_MAX_SIZE={self.WS_MAX_SIZE}
PROD_WS_PING_INTERVAL={self.WS_PING_INTERVAL}
PROD_WS_PING_TIMEOUT={self.WS_PING_TIMEOUT}
PROD_WS_CLOSE_TIMEOUT={self.WS_CLOSE_TIMEOUT}

# Session Configuration
PROD_SESSION_TIMEOUT={self.SESSION_TIMEOUT}
PROD_SESSION_MAX_CONCURRENT={self.SESSION_MAX_CONCURRENT}

# Monitoring Configuration
PROD_MONITOR_HOST={self.MONITOR_HOST}
PROD_MONITOR_PORT={self.MONITOR_PORT}
PROD_METRICS_ENABLED={str(self.METRICS_ENABLED).lower()}

# Logging Configuration
PROD_LOG_LEVEL={self.LOG_LEVEL}
PROD_LOG_FORMAT={self.LOG_FORMAT}
PROD_LOG_FILE={self.LOG_FILE}

# Performance Configuration
PROD_WORKERS={self.WORKERS}
PROD_WORKER_CLASS={self.WORKER_CLASS}
PROD_WORKER_CONNECTIONS={self.WORKER_CONNECTIONS}
"""
        
        with open(filepath, 'w') as f:
            f.write(template)
        
        print(f"✅ Environment template exported to: {filepath}")
        print("📝 Customize the values for your production environment")

# Global production config instance
production_config = ProductionConfig()