"""
Structured JSON logging middleware for Phase 1 Foundation.

Provides:
- JSON-formatted log output
- Required fields: timestamp (ISO 8601), level, logger, message
- Optional fields: component, session_id, context
- Fallback to plain text if JSON serialization fails
"""
import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs logs in JSON format."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.
        
        Args:
            record: The log record to format
            
        Returns:
            JSON string with required and optional fields
        """
        try:
            # Build base log structure with required fields
            log_data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage() or "No message provided"
            }
            
            # Add optional context fields if present
            context = {}
            
            if hasattr(record, 'component'):
                context['component'] = record.component
            
            if hasattr(record, 'session_id'):
                context['session_id'] = record.session_id
            
            if hasattr(record, 'context') and record.context:
                context.update(record.context)
            
            # Only add context object if we have optional fields
            if context:
                log_data['context'] = context
            
            return json.dumps(log_data)
        
        except Exception as e:
            # Fallback to plain text if JSON serialization fails
            timestamp = datetime.now(timezone.utc).isoformat()
            return f"{timestamp} {record.levelname} {record.name} - {record.getMessage()} (JSON serialization failed: {e})"


def setup_structured_logging(
    level: str = "INFO",
    log_file: Optional[str] = None
) -> None:
    """Set up structured JSON logging for the application.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path to write logs to
    """
    # Create JSON formatter
    json_formatter = JSONFormatter()
    
    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(json_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(json_formatter)
        root_logger.addHandler(file_handler)


def log_with_context(
    logger: logging.Logger,
    level: str,
    message: str,
    component: Optional[str] = None,
    session_id: Optional[str] = None,
    **extra_context: Any
) -> None:
    """Log a message with optional context fields.
    
    Args:
        logger: The logger instance to use
        level: Log level (debug, info, warning, error, critical)
        message: The log message
        component: Optional component name
        session_id: Optional session ID
        **extra_context: Additional context fields
    """
    extra = {}
    
    if component:
        extra['component'] = component
    
    if session_id:
        extra['session_id'] = session_id
    
    if extra_context:
        extra['context'] = extra_context
    
    # Get the log method dynamically
    log_method = getattr(logger, level.lower())
    log_method(message, extra=extra)
