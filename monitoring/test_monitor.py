"""
Real-Time Test Monitoring Dashboard
Phase 2 P4 - Polish & Validation

This module provides a web-based dashboard for monitoring test execution,
coverage analysis, and performance metrics in real-time.
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
import psutil
import subprocess
import threading
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestMonitor:
    """Real-time test execution monitor with WebSocket broadcasting."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.current_test = None
        self.test_results = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "current_test": None,
            "start_time": None,
            "end_time": None,
            "duration": 0,
            "coverage": 0.0,
            "memory_usage": 0,
            "test_details": []
        }
        self.system_metrics = {
            "cpu_percent": 0.0,
            "memory_percent": 0.0,
            "memory_mb": 0,
            "process_count": 0
        }
        self.is_running = False
        
    async def connect(self, websocket: WebSocket):
        """Connect a new WebSocket client."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"New monitoring client connected. Total: {len(self.active_connections)}")
        
        # Send current state to new connection
        await self.broadcast_update()
        
    def disconnect(self, websocket: WebSocket):
        """Disconnect a WebSocket client."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"Monitoring client disconnected. Total: {len(self.active_connections)}")
    
    async def broadcast_update(self):
        """Broadcast current state to all connected clients."""
        if not self.active_connections:
            return
            
        # Update system metrics
        self.update_system_metrics()
        
        message = {
            "type": "test_update",
            "timestamp": datetime.now().isoformat(),
            "test_results": self.test_results,
            "system_metrics": self.system_metrics
        }
        
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to client: {e}")
                disconnected.append(connection)
        
        # Remove disconnected clients
        for conn in disconnected:
            self.disconnect(conn)
    
    def update_system_metrics(self):
        """Update system performance metrics."""
        try:
            # CPU and memory usage
            self.system_metrics["cpu_percent"] = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            self.system_metrics["memory_percent"] = memory.percent
            self.system_metrics["memory_mb"] = round(memory.used / (1024 * 1024), 1)
            
            # Process information
            current_process = psutil.Process()
            self.system_metrics["process_memory_mb"] = round(
                current_process.memory_info().rss / (1024 * 1024), 1
            )
            
        except Exception as e:
            logger.error(f"Failed to update system metrics: {e}")
    
    def start_test_run(self, test_command: str, total_tests: int = 103):
        """Start a new test run."""
        self.test_results.update({
            "total_tests": total_tests,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "current_test": "Starting test suite...",
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "duration": 0,
            "test_command": test_command,
            "test_details": []
        })
        self.is_running = True
    
    def update_test_progress(self, test_name: str, status: str, duration: float = 0):
        """Update progress for a specific test."""
        self.test_results["current_test"] = test_name
        
        if status == "PASSED":
            self.test_results["passed"] += 1
        elif status == "FAILED":
            self.test_results["failed"] += 1
        elif status == "SKIPPED":
            self.test_results["skipped"] += 1
        
        # Add test detail
        self.test_results["test_details"].append({
            "name": test_name,
            "status": status,
            "duration": duration,
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep only last 20 test details to avoid memory bloat
        if len(self.test_results["test_details"]) > 20:
            self.test_results["test_details"] = self.test_results["test_details"][-20:]
    
    def finish_test_run(self, coverage_percent: float = 0.0):
        """Mark test run as complete."""
        self.test_results.update({
            "end_time": datetime.now().isoformat(),
            "current_test": "Test run complete",
            "coverage": coverage_percent
        })
        
        if self.test_results["start_time"]:
            start = datetime.fromisoformat(self.test_results["start_time"])
            end = datetime.fromisoformat(self.test_results["end_time"])
            self.test_results["duration"] = (end - start).total_seconds()
        
        self.is_running = False
    
    def update_coverage(self, coverage_percent: float):
        """Update test coverage percentage."""
        self.test_results["coverage"] = coverage_percent

# Global monitor instance
monitor = TestMonitor()

# FastAPI app
app = FastAPI(title="Test Monitor Dashboard")

# Mount static files - use absolute path
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.on_event("startup")
async def startup_event():
    """Start background tasks when the app starts."""
    asyncio.create_task(start_metrics_updater())

@app.get("/")
async def dashboard():
    """Serve the monitoring dashboard."""
    dashboard_path = Path(__file__).parent / "dashboard.html"
    return FileResponse(str(dashboard_path))

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "active_connections": len(monitor.active_connections),
        "is_running": monitor.is_running,
        "timestamp": datetime.now().isoformat()
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await monitor.connect(websocket)
    try:
        while True:
            # Keep connection alive and listen for client messages
            data = await websocket.receive_text()
            
            # Handle client commands if needed
            if data == "ping":
                await websocket.send_text("pong")
                
    except WebSocketDisconnect:
        monitor.disconnect(websocket)

@app.post("/api/start-tests")
async def start_tests():
    """Start test execution."""
    # This will be called by the test runner
    monitor.start_test_run("pytest with coverage", 103)
    await monitor.broadcast_update()
    return {"status": "started"}

@app.post("/api/test-update")
async def test_update(update: dict):
    """Receive test progress updates."""
    if "test_name" in update:
        monitor.update_test_progress(
            update["test_name"],
            update.get("status", "RUNNING"),
            update.get("duration", 0)
        )
    
    if "coverage" in update:
        monitor.update_coverage(update["coverage"])
    
    await monitor.broadcast_update()
    return {"status": "updated"}

@app.post("/api/finish-tests")
async def finish_tests(result: dict):
    """Mark test run as complete."""
    monitor.finish_test_run(result.get("coverage", 0.0))
    await monitor.broadcast_update()
    return {"status": "finished"}

async def start_metrics_updater():
    """Background task to update metrics periodically."""
    while True:
        if monitor.active_connections:
            await monitor.broadcast_update()
        await asyncio.sleep(2)  # Update every 2 seconds

def run_server():
    """Run the FastAPI server with proper event loop handling."""
    logger.info("🖥️  Starting Test Monitor Dashboard")
    logger.info("📊 Dashboard: http://localhost:8001")
    logger.info("🔗 WebSocket: ws://localhost:8001/ws")
    logger.info("💚 Health: http://localhost:8001/health")
    
    # Configure uvicorn to handle the event loop
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=8001,
        log_level="info"
    )
    server = uvicorn.Server(config)
    
    # Start the server which will create its own event loop
    server.run()

if __name__ == "__main__":
    run_server()