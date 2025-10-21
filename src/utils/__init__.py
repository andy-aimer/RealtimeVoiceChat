"""
Utility modules for Phase 2 infrastructure improvements.

This package contains lifecycle management utilities for thread cleanup,
graceful shutdown, and resource management.

Modules:
    lifecycle: Thread lifecycle management with ManagedThread context manager
    backoff: Exponential backoff utilities for retry logic
"""

from .backoff import ExponentialBackoff

__all__ = ["ExponentialBackoff"]
