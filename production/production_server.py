"""
Production Server with Security Enhancements
Implements security recommendations from Phase 2 P4 audit
"""

import asyncio
import json
import time
import logging
import secrets
from typing import Dict, Set, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import jwt
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from production.production_config import production_config

# Configure structured logging
logging.basicConfig(
    level=getattr(logging, production_config.LOG_LEVEL),
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)

# Security
security = HTTPBearer(auto_error=False)

class SecurityManager:
    """Handles authentication, rate limiting, and input validation."""
    
    def __init__(self):
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.failed_attempts: Dict[str, int] = {}
        self.blocked_ips: Set[str] = set()
        
    def create_access_token(self, data: dict) -> str:
        """Create JWT access token."""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=production_config.AUTH_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, production_config.AUTH_SECRET_KEY, algorithm=production_config.AUTH_ALGORITHM)
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token."""
        try:
            payload = jwt.decode(token, production_config.AUTH_SECRET_KEY, algorithms=[production_config.AUTH_ALGORITHM])
            return payload
        except jwt.PyJWTError:
            return None
    
    def validate_input(self, data: Any) -> bool:
        """Validate and sanitize input data."""
        if isinstance(data, str):
            # Check for XSS patterns
            dangerous_patterns = ['<script', 'javascript:', 'onload=', 'onerror=', 'eval(']
            data_lower = data.lower()
            for pattern in dangerous_patterns:
                if pattern in data_lower:
                    logger.warning(f"Potential XSS attempt detected: {pattern}")
                    return False
            
            # Check message size
            if len(data) > production_config.WS_MAX_SIZE:
                logger.warning(f"Message too large: {len(data)} bytes")
                return False
        
        return True
    
    def check_rate_limit(self, client_ip: str) -> bool:
        """Check if client is rate limited."""
        if not production_config.RATE_LIMIT_ENABLED:
            return True
        
        if client_ip in self.blocked_ips:
            return False
        
        # Simple rate limiting logic
        current_time = time.time()
        # Reset failed attempts every hour
        if current_time % 3600 < 60:
            self.failed_attempts.clear()
        
        return self.failed_attempts.get(client_ip, 0) < 5
    
    def record_failed_attempt(self, client_ip: str):
        """Record failed authentication attempt."""
        self.failed_attempts[client_ip] = self.failed_attempts.get(client_ip, 0) + 1
        if self.failed_attempts[client_ip] >= 5:
            self.blocked_ips.add(client_ip)
            logger.warning(f"IP blocked due to repeated failures: {client_ip}")

class ProductionWebSocketManager:
    """Enhanced WebSocket manager with security and monitoring."""
    
    def __init__(self):
        self.connections: Dict[str, WebSocket] = {}
        self.session_data: Dict[str, Dict[str, Any]] = {}
        self.connection_timestamps: Dict[str, float] = {}
        
    async def connect(self, websocket: WebSocket, session_id: str) -> bool:
        """Establish WebSocket connection with validation."""
        # Check concurrent connection limits
        if len(self.connections) >= production_config.SESSION_MAX_CONCURRENT:
            logger.warning(f"Connection limit reached: {len(self.connections)}")
            await websocket.close(code=1013, reason="Server overloaded")
            return False
        
        await websocket.accept()
        self.connections[session_id] = websocket
        self.connection_timestamps[session_id] = time.time()
        self.session_data[session_id] = {
            'created': time.time(),
            'last_activity': time.time(),
            'message_count': 0
        }
        
        logger.info(f"WebSocket connected: {session_id}, Total: {len(self.connections)}")
        return True
    
    async def disconnect(self, session_id: str):
        """Clean up WebSocket connection."""
        if session_id in self.connections:
            del self.connections[session_id]
        if session_id in self.session_data:
            del self.session_data[session_id]
        if session_id in self.connection_timestamps:
            del self.connection_timestamps[session_id]
        
        logger.info(f"WebSocket disconnected: {session_id}, Remaining: {len(self.connections)}")
    
    async def send_personal_message(self, message: str, session_id: str):
        """Send message to specific session with validation."""
        if session_id not in self.connections:
            logger.warning(f"Attempt to send to non-existent session: {session_id}")
            return False
        
        try:
            websocket = self.connections[session_id]
            await websocket.send_text(message)
            
            # Update session activity
            if session_id in self.session_data:
                self.session_data[session_id]['last_activity'] = time.time()
                self.session_data[session_id]['message_count'] += 1
            
            return True
        except Exception as e:
            logger.error(f"Error sending message to {session_id}: {e}")
            await self.disconnect(session_id)
            return False
    
    async def cleanup_expired_sessions(self):
        """Clean up expired sessions."""
        current_time = time.time()
        expired_sessions = []
        
        for session_id, data in self.session_data.items():
            if current_time - data['last_activity'] > production_config.SESSION_TIMEOUT:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            if session_id in self.connections:
                try:
                    await self.connections[session_id].close(code=1001, reason="Session expired")
                except:
                    pass
            await self.disconnect(session_id)
        
        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        current_time = time.time()
        active_sessions = 0
        total_messages = 0
        
        for data in self.session_data.values():
            if current_time - data['last_activity'] < 300:  # Active in last 5 minutes
                active_sessions += 1
            total_messages += data['message_count']
        
        return {
            'total_connections': len(self.connections),
            'active_sessions': active_sessions,
            'total_messages': total_messages,
            'uptime': current_time - start_time
        }

# Initialize managers
security_manager = SecurityManager()
websocket_manager = ProductionWebSocketManager()
start_time = time.time()

# Create FastAPI app with security middleware
app = FastAPI(
    title="RealtimeVoiceChat Production",
    description="Production-ready real-time voice chat with security enhancements",
    version="2.0.0",
    docs_url="/docs" if production_config.LOG_LEVEL == "DEBUG" else None,
    redoc_url=None
)

# Add security middleware
app.add_middleware(SlowAPIMiddleware)
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "*"] if production_config.LOG_LEVEL == "DEBUG" else ["localhost"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=production_config.CORS_ORIGINS,
    allow_credentials=production_config.CORS_CREDENTIALS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)
    
    for header, value in production_config.SECURITY_HEADERS.items():
        response.headers[header] = value
    
    return response

# Authentication dependency
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify authentication token."""
    if not production_config.AUTH_ENABLED:
        return {"user": "anonymous"}
    
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    payload = security_manager.verify_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return payload

# Health check endpoint
@app.get("/health")
@limiter.limit("10/minute")
async def health_check(request: Request):
    """Production health check with comprehensive metrics."""
    try:
        import psutil
        
        health_data = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "system": {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent
            },
            "application": {
                "uptime_seconds": time.time() - start_time,
                "websocket_connections": len(websocket_manager.connections),
                "active_sessions": len(websocket_manager.session_data)
            },
            "security": {
                "auth_enabled": production_config.AUTH_ENABLED,
                "rate_limiting_enabled": production_config.RATE_LIMIT_ENABLED,
                "ssl_enabled": production_config.USE_SSL
            }
        }
        
        # Add thermal monitoring (if available)
        try:
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp_raw = int(f.read().strip())
                temp_celsius = temp_raw / 1000.0
                health_data["thermal"] = {
                    "temperature": temp_celsius,
                    "protection_active": temp_celsius > 85.0
                }
        except:
            health_data["thermal"] = {"temperature": -1, "protection_active": False}
        
        return health_data
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
        )

# Metrics endpoint
@app.get("/metrics")
@limiter.limit("30/minute")
async def metrics(request: Request, user=Depends(get_current_user)):
    """Prometheus-compatible metrics endpoint."""
    if not production_config.METRICS_ENABLED:
        raise HTTPException(status_code=404, detail="Metrics disabled")
    
    stats = websocket_manager.get_stats()
    
    metrics_text = f"""# HELP websocket_connections_total Total WebSocket connections
# TYPE websocket_connections_total gauge
websocket_connections_total {stats['total_connections']}

# HELP websocket_active_sessions Active WebSocket sessions
# TYPE websocket_active_sessions gauge
websocket_active_sessions {stats['active_sessions']}

# HELP websocket_messages_total Total messages processed
# TYPE websocket_messages_total counter
websocket_messages_total {stats['total_messages']}

# HELP app_uptime_seconds Application uptime in seconds
# TYPE app_uptime_seconds counter
app_uptime_seconds {stats['uptime']}
"""
    
    return JSONResponse(content=metrics_text, media_type="text/plain")

# Authentication endpoint
@app.post("/auth/login")
@limiter.limit("5/minute")
async def login(request: Request):
    """Simple authentication endpoint."""
    if not production_config.AUTH_ENABLED:
        raise HTTPException(status_code=404, detail="Authentication disabled")
    
    # Simple demo authentication - replace with real auth logic
    client_ip = get_remote_address(request)
    
    if not security_manager.check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Too many failed attempts")
    
    try:
        body = await request.json()
        username = body.get("username")
        password = body.get("password")
        
        # Demo: accept any username with password "production"
        if password == "production":
            token = security_manager.create_access_token({"sub": username})
            return {"access_token": token, "token_type": "bearer"}
        else:
            security_manager.record_failed_attempt(client_ip)
            raise HTTPException(status_code=401, detail="Invalid credentials")
    
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=400, detail="Invalid request")

# WebSocket endpoint with security
@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """Production WebSocket endpoint with security validation."""
    client_ip = websocket.client.host
    
    # Rate limiting check
    if not security_manager.check_rate_limit(client_ip):
        await websocket.close(code=1008, reason="Rate limited")
        return
    
    # Input validation
    if not security_manager.validate_input(session_id):
        await websocket.close(code=1003, reason="Invalid session ID")
        return
    
    # Establish connection
    if not await websocket_manager.connect(websocket, session_id):
        return
    
    try:
        while True:
            # Receive message with timeout
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=production_config.WS_PING_TIMEOUT
                )
            except asyncio.TimeoutError:
                logger.warning(f"WebSocket timeout for session: {session_id}")
                break
            
            # Validate message
            if not security_manager.validate_input(data):
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Invalid message content"
                }))
                continue
            
            # Process message (placeholder - integrate with existing audio pipeline)
            try:
                message = json.loads(data)
                
                # Echo message for demo (replace with actual processing)
                response = {
                    "type": "response",
                    "session_id": session_id,
                    "timestamp": time.time(),
                    "message": f"Processed: {message.get('type', 'unknown')}"
                }
                
                await websocket_manager.send_personal_message(
                    json.dumps(response), session_id
                )
                
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON format"
                }))
            except Exception as e:
                logger.error(f"Message processing error: {e}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Internal server error"
                }))
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error for {session_id}: {e}")
    finally:
        await websocket_manager.disconnect(session_id)

# Static files (with security headers)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Root endpoint
@app.get("/")
async def root():
    """Serve main application page."""
    with open("static/index.html", "r") as f:
        content = f.read()
    
    # Update WebSocket URL for production
    if production_config.USE_SSL:
        content = content.replace("ws://localhost:8000", f"wss://{production_config.HOST}:{production_config.SSL_PORT}")
    
    return HTMLResponse(content=content)

# Background task for cleanup
async def background_cleanup():
    """Background task for session cleanup."""
    while True:
        try:
            await websocket_manager.cleanup_expired_sessions()
            await asyncio.sleep(60)  # Run every minute
        except Exception as e:
            logger.error(f"Cleanup task error: {e}")
            await asyncio.sleep(60)

@app.on_event("startup")
async def startup_event():
    """Application startup."""
    logger.info("Starting RealtimeVoiceChat Production Server")
    logger.info(f"SSL Enabled: {production_config.USE_SSL}")
    logger.info(f"Authentication Enabled: {production_config.AUTH_ENABLED}")
    logger.info(f"Rate Limiting Enabled: {production_config.RATE_LIMIT_ENABLED}")
    
    # Start background cleanup task
    asyncio.create_task(background_cleanup())

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown."""
    logger.info("Shutting down RealtimeVoiceChat Production Server")
    
    # Close all WebSocket connections
    for session_id in list(websocket_manager.connections.keys()):
        try:
            await websocket_manager.connections[session_id].close(code=1001, reason="Server shutdown")
        except:
            pass
        await websocket_manager.disconnect(session_id)

if __name__ == "__main__":
    # Export environment template
    production_config.export_env_template()
    
    # Get server configuration
    config = production_config.get_uvicorn_config()
    
    logger.info(f"Starting server on {config['host']}:{config['port']}")
    logger.info(f"SSL: {'enabled' if production_config.USE_SSL else 'disabled'}")
    
    uvicorn.run(app, **config)