"""
Custom exception hierarchy for RealtimeVoiceChat Phase 1 Foundation.

Provides base exceptions for:
- Validation errors
- Health check failures
- Monitoring errors
- Security violations
"""


class RealtimeVoiceChatException(Exception):
    """Base exception for all RealtimeVoiceChat errors."""
    
    def __init__(self, message: str, code: str = "INTERNAL_ERROR", **context):
        """Initialize exception with message and error code.
        
        Args:
            message: Human-readable error description
            code: Machine-readable error code (SCREAMING_SNAKE_CASE)
            **context: Additional context for logging/debugging
        """
        self.message = message
        self.code = code
        self.context = context
        super().__init__(message)
    
    def to_dict(self) -> dict:
        """Convert exception to dictionary for API responses."""
        return {
            "type": "error",
            "data": {
                "code": self.code,
                "message": self.message,
                **{k: v for k, v in self.context.items() if k != "message"}
            }
        }


class ValidationError(RealtimeVoiceChatException):
    """Raised when input validation fails."""
    
    def __init__(self, message: str, field: str = None, **context):
        """Initialize validation error.
        
        Args:
            message: Description of validation failure
            field: The field that failed validation (e.g., "data.text")
            **context: Additional context
        """
        code = context.pop("code", "VALIDATION_ERROR")
        if field:
            context["field"] = field
        super().__init__(message, code=code, **context)


class HealthCheckError(RealtimeVoiceChatException):
    """Raised when a health check fails."""
    
    def __init__(self, component: str, message: str, **context):
        """Initialize health check error.
        
        Args:
            component: The component that failed (audio/llm/tts/system)
            message: Description of the failure
            **context: Additional context
        """
        super().__init__(
            message,
            code="HEALTH_CHECK_FAILED",
            component=component,
            **context
        )


class MonitoringError(RealtimeVoiceChatException):
    """Raised when metrics collection fails."""
    
    def __init__(self, metric: str, message: str, **context):
        """Initialize monitoring error.
        
        Args:
            metric: The metric that failed to collect
            message: Description of the failure
            **context: Additional context
        """
        super().__init__(
            message,
            code="MONITORING_ERROR",
            metric=metric,
            **context
        )


class SecurityViolation(RealtimeVoiceChatException):
    """Raised when a security policy is violated."""
    
    def __init__(self, message: str, violation_type: str, **context):
        """Initialize security violation.
        
        Args:
            message: Description of the violation
            violation_type: Type of violation (injection/size/rate_limit)
            **context: Additional context
        """
        super().__init__(
            message,
            code="SECURITY_VIOLATION",
            violation_type=violation_type,
            **context
        )
