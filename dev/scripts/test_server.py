"""
Minimal test server for Phase 2 P3 WebSocket Lifecycle manual testing.
This server only includes the WebSocket reconnection logic without the full voice processing pipeline.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Import our session management
from src.session.session_manager import SessionManager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize SessionManager
session_manager: SessionManager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global session_manager
    
    logger.info("🚀 Starting test server for WebSocket lifecycle testing")
    
    # Initialize SessionManager
    session_manager = SessionManager(
        timeout_minutes=5,      # 5 minutes
        cleanup_interval=60     # 1 minute
    )
    logger.info("✅ SessionManager initialized")
    
    # Start background cleanup task
    cleanup_task = asyncio.create_task(session_manager.start_cleanup_task())
    logger.info("✅ Background cleanup task started")
    
    yield
    
    # Cleanup on shutdown
    logger.info("🛑 Shutting down test server")
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass


# Create FastAPI app
app = FastAPI(
    title="WebSocket Lifecycle Test Server",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="src/static"), name="static")


@app.get("/")
async def root():
    """Serve the main HTML page."""
    return FileResponse("src/static/test.html")


@app.get("/test")
async def test_page():
    """Serve the WebSocket test interface."""
    return FileResponse("src/static/test.html")


@app.get("/health")
async def health():
    """Health check endpoint with session stats."""
    stats = session_manager.get_stats()
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "session_manager": stats
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, session_id: str = None):
    """WebSocket endpoint with session management."""
    await websocket.accept()
    
    # Create or restore session
    if session_id:
        logger.info(f"📥 Attempting to restore session: {session_id}")
        session = await session_manager.restore_session(session_id)
        if session:
            logger.info(f"✅ Session restored: {session_id}")
            await websocket.send_json({
                "type": "session_restored",
                "session_id": session_id
            })
        else:
            logger.info(f"⚠️  Session not found or expired: {session_id}")
            session_id = await session_manager.create_session()
            logger.info(f"✨ Created new session: {session_id}")
            await websocket.send_json({
                "type": "session_created",
                "session_id": session_id
            })
    else:
        session_id = await session_manager.create_session()
        logger.info(f"✨ Created new session: {session_id}")
        await websocket.send_json({
            "type": "session_created",
            "session_id": session_id
        })
    
    try:
        while True:
            # Receive messages from client (handle both JSON and binary)
            try:
                # Try to receive JSON message first
                data = await websocket.receive_json()
                message_type = data.get("type", "unknown")
                logger.info(f"📨 Received JSON message '{message_type}' from session {session_id}")
                
                # Touch session to keep it alive
                await session_manager.touch_session(session_id)
                
                # Echo back for testing
                await websocket.send_json({
                    "type": "echo",
                    "original": data,
                    "session_id": session_id,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
            except Exception:
                # If JSON parsing fails, handle as text or binary
                try:
                    data = await websocket.receive_text()
                    logger.info(f"📨 Received text message from session {session_id}: {data[:50]}...")
                    
                    # Touch session to keep it alive
                    await session_manager.touch_session(session_id)
                    
                    # Send acknowledgment
                    await websocket.send_json({
                        "type": "text_received",
                        "session_id": session_id,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
                except Exception:
                    # Handle binary data
                    try:
                        data = await websocket.receive_bytes()
                        logger.info(f"📨 Received binary data from session {session_id} (size: {len(data)} bytes)")
                        
                        # Touch session to keep it alive
                        await session_manager.touch_session(session_id)
                        
                        # Send acknowledgment for binary data
                        await websocket.send_json({
                            "type": "binary_received",
                            "session_id": session_id,
                            "data_size": len(data),
                            "timestamp": datetime.utcnow().isoformat()
                        })
                        
                    except Exception as e:
                        logger.error(f"❌ Failed to process message from session {session_id}: {e}")
                        break
            
    except WebSocketDisconnect:
        logger.info(f"🔌 WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"❌ WebSocket error: {e}")
    finally:
        # Session will be cleaned up by background task after timeout
        logger.info(f"👋 WebSocket connection closed: {session_id}")


if __name__ == "__main__":
    import uvicorn
    
    logger.info("=" * 60)
    logger.info("🧪 WebSocket Lifecycle Test Server")
    logger.info("=" * 60)
    logger.info("📍 Server will start on: http://localhost:8000")
    logger.info("🔗 WebSocket endpoint: ws://localhost:8000/ws")
    logger.info("💚 Health check: http://localhost:8000/health")
    logger.info("=" * 60)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
