"""
Thread lifecycle management utilities for graceful cleanup.

This module provides the ManagedThread class, a context manager wrapper
for threading.Thread that ensures proper cleanup with stop signals.
"""

import logging
import threading
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class ManagedThread:
    """
    Context manager wrapper for threading.Thread with graceful stop signaling.
    
    This class wraps a standard threading.Thread and adds:
    - Stop signaling via threading.Event
    - Graceful join with timeout
    - Context manager support for automatic cleanup
    - Exception handling and logging
    
    Usage:
        def worker_function(thread: ManagedThread):
            while not thread.should_stop():
                # Do work...
                pass
        
        with ManagedThread(target=worker_function) as thread:
            # Thread runs in background
            pass
        # Thread automatically stopped and joined on exit
    
    Attributes:
        _thread: The underlying threading.Thread instance
        _stop_event: threading.Event for signaling stop
        _target: The target function to run
        _args: Positional arguments for target
        _kwargs: Keyword arguments for target
        _name: Optional thread name for logging
    """
    
    def __init__(
        self,
        target: Callable,
        args: tuple = (),
        kwargs: Optional[dict] = None,
        name: Optional[str] = None,
        daemon: bool = True
    ):
        """
        Initialize a ManagedThread.
        
        Args:
            target: The callable to run in the thread. Should accept the
                   ManagedThread instance as first argument (or check should_stop()).
            args: Positional arguments to pass to target (after self).
            kwargs: Keyword arguments to pass to target.
            name: Optional name for the thread (for logging).
            daemon: Whether the thread should be a daemon thread.
        """
        self._stop_event = threading.Event()
        self._target = target
        self._args = args
        self._kwargs = kwargs or {}
        self._name = name or f"ManagedThread-{id(self)}"
        
        # Create the underlying thread
        self._thread = threading.Thread(
            target=self._run_with_error_handling,
            name=self._name,
            daemon=daemon
        )
        
        logger.info(f"🧵 ManagedThread '{self._name}' initialized")
    
    def _run_with_error_handling(self) -> None:
        """
        Internal wrapper that runs the target function with error handling.
        
        Catches and logs any exceptions that occur in the target function.
        """
        try:
            logger.info(f"🧵▶️  ManagedThread '{self._name}' started")
            # Pass self as first argument so target can check should_stop()
            self._target(self, *self._args, **self._kwargs)
            logger.info(f"🧵✅ ManagedThread '{self._name}' completed normally")
        except Exception as e:
            logger.error(
                f"🧵❌ ManagedThread '{self._name}' encountered error: {e}",
                exc_info=True
            )
    
    def start(self) -> None:
        """
        Start the managed thread.
        
        This must be called explicitly if not using the context manager.
        """
        if self._thread.is_alive():
            logger.warning(f"🧵⚠️  ManagedThread '{self._name}' already running")
            return
        
        self._thread.start()
        logger.info(f"🧵🚀 ManagedThread '{self._name}' start() called")
    
    def stop(self) -> None:
        """
        Signal the thread to stop by setting the stop event.
        
        This does not forcefully terminate the thread. The thread's target
        function must check should_stop() periodically and exit gracefully.
        
        This method is idempotent - calling it multiple times is safe.
        """
        if not self._stop_event.is_set():
            logger.info(f"🧵🛑 ManagedThread '{self._name}' stop() called")
            self._stop_event.set()
        else:
            logger.debug(f"🧵⚠️  ManagedThread '{self._name}' stop() called but already stopped")
    
    def should_stop(self) -> bool:
        """
        Check if the thread should stop.
        
        The thread's target function should call this periodically and
        exit gracefully when it returns True.
        
        Returns:
            True if stop has been signaled, False otherwise.
        """
        return self._stop_event.is_set()
    
    def join(self, timeout: float = 5.0) -> bool:
        """
        Wait for the thread to complete.
        
        Args:
            timeout: Maximum time to wait in seconds (default: 5.0).
        
        Returns:
            True if the thread completed within timeout, False if timeout occurred.
        """
        if not self._thread.is_alive():
            logger.debug(f"🧵✅ ManagedThread '{self._name}' already completed")
            return True
        
        logger.info(f"🧵⏳ Joining ManagedThread '{self._name}' (timeout={timeout}s)")
        self._thread.join(timeout=timeout)
        
        if self._thread.is_alive():
            logger.warning(
                f"🧵⚠️  ManagedThread '{self._name}' did not complete within {timeout}s timeout"
            )
            return False
        else:
            logger.info(f"🧵✅ ManagedThread '{self._name}' joined successfully")
            return True
    
    def is_alive(self) -> bool:
        """
        Check if the thread is currently running.
        
        Returns:
            True if the thread is alive, False otherwise.
        """
        return self._thread.is_alive()
    
    def __enter__(self) -> 'ManagedThread':
        """
        Enter the context manager.
        
        Automatically starts the thread.
        
        Returns:
            self for use in 'with' statements.
        """
        self.start()
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """
        Exit the context manager.
        
        Automatically stops and joins the thread. If the thread doesn't
        complete within the timeout, a warning is logged.
        
        Args:
            exc_type: Exception type if an exception occurred.
            exc_val: Exception value if an exception occurred.
            exc_tb: Exception traceback if an exception occurred.
        """
        logger.info(f"🧵🚪 ManagedThread '{self._name}' exiting context manager")
        self.stop()
        joined = self.join(timeout=5.0)
        
        if not joined:
            logger.error(
                f"🧵❌ ManagedThread '{self._name}' failed to join within timeout. "
                f"Thread may be orphaned."
            )
