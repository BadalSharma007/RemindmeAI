"""Circuit Breaker pattern for external API fault tolerance.

States:
  CLOSED    — normal operation; failures counted
  OPEN      — fast-fail; no calls allowed; transitions to HALF_OPEN after recovery_timeout
  HALF_OPEN — one probe call allowed; success → CLOSED, failure → OPEN
"""
from __future__ import annotations

import asyncio
import functools
import logging
import threading
import time
from enum import Enum
from typing import Any, Callable, Type

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerOpen(Exception):
    """Raised when a call is attempted while the circuit is OPEN."""

    def __init__(self, name: str, reset_at: float) -> None:
        self.name = name
        self.reset_at = reset_at
        remaining = max(0.0, reset_at - time.monotonic())
        super().__init__(
            f"Circuit '{name}' is OPEN. Retry in {remaining:.1f}s."
        )


class CircuitBreaker:
    """Thread-safe, async-compatible circuit breaker.

    Parameters
    ----------
    name:
        Human-readable identifier (used in logs and exceptions).
    failure_threshold:
        Number of consecutive failures before the circuit opens.
    recovery_timeout:
        Seconds to wait in OPEN before transitioning to HALF_OPEN.
    expected_exception:
        Exception type (or tuple of types) that counts as a failure.
        Any other exception passes through without counting.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Type[Exception] | tuple[Type[Exception], ...] = Exception,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._opened_at: float | None = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def state(self) -> CircuitState:
        with self._lock:
            self._maybe_transition_to_half_open()
            return self._state

    def call(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """Execute *func* synchronously through the circuit breaker."""
        self._before_call()
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as exc:
            self._on_failure(exc)
            raise

    async def call_async(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """Execute *func* (coroutine) through the circuit breaker."""
        self._before_call()
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as exc:
            self._on_failure(exc)
            raise

    def reset(self) -> None:
        """Manually force the circuit back to CLOSED (useful in tests)."""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._opened_at = None

    # ------------------------------------------------------------------
    # Internal state machine
    # ------------------------------------------------------------------

    def _maybe_transition_to_half_open(self) -> None:
        """Called under lock. Transitions OPEN → HALF_OPEN when timeout expires."""
        if (
            self._state is CircuitState.OPEN
            and self._opened_at is not None
            and time.monotonic() - self._opened_at >= self.recovery_timeout
        ):
            self._state = CircuitState.HALF_OPEN
            logger.info("Circuit '%s' → HALF_OPEN (probe allowed)", self.name)

    def _before_call(self) -> None:
        with self._lock:
            self._maybe_transition_to_half_open()
            if self._state is CircuitState.OPEN:
                assert self._opened_at is not None
                raise CircuitBreakerOpen(
                    self.name, self._opened_at + self.recovery_timeout
                )

    def _on_success(self) -> None:
        with self._lock:
            if self._state in (CircuitState.HALF_OPEN, CircuitState.OPEN):
                logger.info("Circuit '%s' → CLOSED (probe succeeded)", self.name)
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._opened_at = None

    def _on_failure(self, exc: Exception) -> None:
        if not isinstance(exc, self.expected_exception):
            return  # Unexpected exception; don't count against the circuit
        with self._lock:
            if self._state is CircuitState.HALF_OPEN:
                # Probe failed → re-open
                self._state = CircuitState.OPEN
                self._opened_at = time.monotonic()
                logger.warning(
                    "Circuit '%s' → OPEN (probe failed: %s)", self.name, exc
                )
                return

            self._failure_count += 1
            if self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN
                self._opened_at = time.monotonic()
                logger.warning(
                    "Circuit '%s' → OPEN after %d failures (last: %s)",
                    self.name,
                    self._failure_count,
                    exc,
                )


# ---------------------------------------------------------------------------
# Decorator factory
# ---------------------------------------------------------------------------

def circuit(
    name: str | None = None,
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    expected_exception: Type[Exception] | tuple[Type[Exception], ...] = Exception,
) -> Callable:
    """Decorator that wraps a sync or async function with a CircuitBreaker.

    Usage::

        @circuit(name="gmail-api", failure_threshold=3, recovery_timeout=30)
        async def fetch_gmail_messages(token: str) -> list:
            ...

    The same ``CircuitBreaker`` instance is reused across all calls to the
    decorated function (stored on the wrapper as ``wrapped_func.circuit_breaker``).
    """

    def decorator(func: Callable) -> Callable:
        breaker = CircuitBreaker(
            name=name or func.__qualname__,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            expected_exception=expected_exception,
        )

        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                return await breaker.call_async(func, *args, **kwargs)

            async_wrapper.circuit_breaker = breaker  # type: ignore[attr-defined]
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                return breaker.call(func, *args, **kwargs)

            sync_wrapper.circuit_breaker = breaker  # type: ignore[attr-defined]
            return sync_wrapper

    return decorator
