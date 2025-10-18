#!/usr/bin/env python3
"""
Minimal FastAPI server for testing monitoring endpoints only.
Loads only the health checks and metrics without heavy TTS/STT dependencies.
"""

import sys
import os

# Add code directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'code'))

from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse
import asyncio
from datetime import datetime, timezone
import uvicorn

# Import our monitoring modules
from health_checks import (
    check_audio_processor,
    check_llm_backend,
    check_tts_engine,
    check_system_resources,
    COMPONENT_TIMEOUT
)
from metrics import get_metrics
from exceptions import HealthCheckError, MonitoringError

app = FastAPI(title="RealtimeVoiceChat Monitoring Test")

# Cache for health check results
_health_cache = {"timestamp": None, "result": None}
HEALTH_CACHE_TTL = 30  # 30 seconds


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Monitoring Test Server", "endpoints": ["/health", "/metrics"]}


@app.get("/health")
async def health_check():
    """
    Health check endpoint that checks all system components.
    Results are cached for 30 seconds to minimize overhead.
    """
    global _health_cache
    
    # Check if we have a valid cached result
    now = datetime.now(timezone.utc)
    if _health_cache["timestamp"] is not None:
        cache_age = (now - _health_cache["timestamp"]).total_seconds()
        if cache_age < HEALTH_CACHE_TTL:
            return _health_cache["result"]
    
    # Perform health checks in parallel with timeout
    try:
        # Run all checks concurrently with overall timeout
        checks = asyncio.gather(
            check_audio_processor(),
            check_llm_backend(),
            check_tts_engine(),
            check_system_resources(),
            return_exceptions=True
        )
        
        results = await asyncio.wait_for(checks, timeout=10.0)
        
        # Process results
        components = {}
        overall_status = "healthy"
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                component_name = ["audio", "llm", "tts", "system"][i]
                components[component_name] = {
                    "status": "unhealthy",
                    "error": str(result)
                }
                overall_status = "unhealthy"
            else:
                comp_name = result.get("component", f"component_{i}")
                comp_status = result.get("status", "unknown")
                components[comp_name] = {
                    "status": comp_status,
                    "details": result.get("details")
                }
                
                # Update overall status based on component status
                if comp_status == "unhealthy" and overall_status != "unhealthy":
                    overall_status = "unhealthy"
                elif comp_status == "degraded" and overall_status == "healthy":
                    overall_status = "degraded"
        
        response_data = {
            "status": overall_status,
            "timestamp": now.isoformat(),
            "components": components
        }
        
        # Cache the result
        _health_cache["timestamp"] = now
        _health_cache["result"] = JSONResponse(
            content=response_data,
            status_code=200 if overall_status == "healthy" else 503
        )
        
        return _health_cache["result"]
        
    except asyncio.TimeoutError:
        return JSONResponse(
            content={
                "status": "error",
                "message": "Health check timed out after 10 seconds",
                "timestamp": now.isoformat()
            },
            status_code=500
        )
    except Exception as e:
        return JSONResponse(
            content={
                "status": "error",
                "message": f"Health check failed: {str(e)}",
                "timestamp": now.isoformat()
            },
            status_code=500
        )


@app.get("/metrics")
async def metrics_endpoint():
    """
    Metrics endpoint that returns Prometheus-format metrics.
    """
    try:
        metrics_text = get_metrics()
        return Response(
            content=metrics_text,
            media_type="text/plain; version=0.0.4"
        )
    except Exception as e:
        raise MonitoringError(
            metric="all",
            message=f"Failed to collect metrics: {str(e)}"
        )


@app.on_event("startup")
async def startup_event():
    """Log startup message."""
    print("=" * 60)
    print("MONITORING TEST SERVER STARTED")
    print("=" * 60)
    print(f"Time: {datetime.now(timezone.utc).isoformat()}")
    print("Available endpoints:")
    print("  - GET /         (root info)")
    print("  - GET /health   (health checks)")
    print("  - GET /metrics  (Prometheus metrics)")
    print("=" * 60)


if __name__ == "__main__":
    # Run the server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
