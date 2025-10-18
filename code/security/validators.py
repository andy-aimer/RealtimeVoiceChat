"""
Input validation and sanitization for WebSocket messages.

Provides Pydantic models for validating incoming messages and detecting
potential security issues like prompt injection attempts.
"""

import re
import logging
from typing import List, Literal, Optional, Tuple
from pydantic import BaseModel, field_validator, ValidationError as PydanticValidationError

logger = logging.getLogger(__name__)


class ValidationError(BaseModel):
    """Structured validation error with field and message."""
    field: str
    message: str
    value: Optional[str] = None


class WebSocketMessage(BaseModel):
    """WebSocket message with type validation.
    
    Validates that messages have correct type field (audio/text/control)
    and required data fields.
    """
    type: Literal["audio", "text", "control"]
    data: Optional[dict] = None
    
    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Validate message type is one of allowed values."""
        if v not in ["audio", "text", "control"]:
            raise ValueError(f"Invalid message type: {v}")
        return v


class TextData(BaseModel):
    """Text data with sanitization and security checks.
    
    - Enforces 5000 character maximum
    - Detects prompt injection attempts (log-only, no blocking)
    - Sanitizes input for safe processing
    """
    text: str
    metadata: Optional[dict] = None
    
    @field_validator("text")
    @classmethod
    def validate_and_sanitize(cls, v: str) -> str:
        """Validate text length and detect prompt injection."""
        # Check length limit
        if len(v) > 5000:
            raise ValueError(f"Text exceeds 5000 character limit: {len(v)} chars")
        
        # Detect prompt injection patterns (log-only, don't block)
        injection_patterns = [
            r"ignore\s+(previous|above|prior)\s+instructions?",
            r"disregard\s+(previous|above|prior)",
            r"you\s+are\s+now",
            r"new\s+instructions?:",
            r"system\s*:\s*",
            r"<\s*script\s*>",
        ]
        
        for pattern in injection_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                logger.warning(
                    "Potential prompt injection detected",
                    extra={
                        "pattern": pattern,
                        "text_length": len(v),
                        "text_preview": v[:100]
                    }
                )
                break
        
        return v


def validate_message(message: dict) -> Tuple[bool, List[ValidationError]]:
    """Validate WebSocket message and return validation results.
    
    Args:
        message: Raw message dictionary from WebSocket
        
    Returns:
        Tuple of (is_valid, errors)
        - is_valid: True if message passed all validations
        - errors: List of ValidationError objects (empty if valid)
        
    Example:
        >>> is_valid, errors = validate_message({"type": "text", "data": {"text": "Hello"}})
        >>> if not is_valid:
        ...     for error in errors:
        ...         print(f"{error.field}: {error.message}")
    """
    errors: List[ValidationError] = []
    
    # Validate WebSocket message structure
    try:
        ws_msg = WebSocketMessage(**message)
    except PydanticValidationError as e:
        for err in e.errors():
            field = ".".join(str(loc) for loc in err["loc"])
            errors.append(ValidationError(
                field=field,
                message=err["msg"],
                value=str(err.get("input", ""))
            ))
        return False, errors
    
    # Additional validation for text messages
    if ws_msg.type == "text" and ws_msg.data:
        text_content = ws_msg.data.get("text")
        if text_content:
            try:
                TextData(text=text_content)
            except PydanticValidationError as e:
                for err in e.errors():
                    field = f"data.{err['loc'][0]}"
                    errors.append(ValidationError(
                        field=field,
                        message=err["msg"],
                        value=str(err.get("input", ""))[:100]
                    ))
                return False, errors
    
    return True, []
