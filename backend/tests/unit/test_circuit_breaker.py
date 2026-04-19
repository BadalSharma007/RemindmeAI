"""Unit tests for app.services.resilience.circuit_breaker — no external deps."""
from __future__ import annotations

import asyncio
import time

import pytest

from app.services.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpen,
    CircuitState,
    circuit,
)


# ---------------------------------------------------------------------------
# Tests — CLOSED state (normal operation)
# ---------------------------------------------------------------------------

def test_initial_state_is_closed():
    cb = CircuitBreaker("test-init", failure_threshold=3)
    assert cb.state is CircuitState.CLOSED


def test_success_does_not_open_circuit():
    cb = CircuitBreaker("test-success", failure_threshold=3)

    def ok():
        return 42

    assert cb.call(ok) == 42
    assert cb.state is CircuitState.CLOSED


def test_failures_below_threshold_stay_closed():
    cb = CircuitBreaker("test-below", failure_threshold=3)

    def bad():
        raise ValueError("boom")

    for _ in range(2):
        with pytest.raises(ValueError):
            cb.call(bad)

    assert cb.state is CircuitState.CLOSED


# ---------------------------------------------------------------------------
# Tests — OPEN state
# ---------------------------------------------------------------------------

def test_opens_after_threshold_failures():
    cb = CircuitBreaker("test-open", failure_threshold=3)

    def bad():
        raise ValueError("boom")

    for _ in range(3):
        with pytest.raises(ValueError):
            cb.call(bad)

    assert cb.state is CircuitState.OPEN


def test_open_circuit_raises_circuit_breaker_open():
    cb = CircuitBreaker("test-fast-fail", failure_threshold=2)

    def bad():
        raise RuntimeError("fail")

    for _ in range(2):
        with pytest.raises(RuntimeError):
            cb.call(bad)

    with pytest.raises(CircuitBreakerOpen):
        cb.call(lambda: None)


# ---------------------------------------------------------------------------
# Tests — HALF_OPEN / recovery
# ---------------------------------------------------------------------------

def test_transitions_to_half_open_after_timeout():
    cb = CircuitBreaker("test-half-open", failure_threshold=2, recovery_timeout=0.05)

    def bad():
        raise RuntimeError("fail")

    for _ in range(2):
        with pytest.raises(RuntimeError):
            cb.call(bad)

    assert cb.state is CircuitState.OPEN
    time.sleep(0.06)
    assert cb.state is CircuitState.HALF_OPEN


def test_successful_probe_closes_circuit():
    cb = CircuitBreaker("test-recover", failure_threshold=2, recovery_timeout=0.05)

    def bad():
        raise RuntimeError("fail")

    for _ in range(2):
        with pytest.raises(RuntimeError):
            cb.call(bad)

    time.sleep(0.06)
    cb.call(lambda: "ok")  # probe succeeds
    assert cb.state is CircuitState.CLOSED


# ---------------------------------------------------------------------------
# Tests — async decorator
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_circuit_decorator_async():
    call_count = 0

    @circuit(name="test-async-deco", failure_threshold=2, recovery_timeout=60)
    async def flaky():
        nonlocal call_count
        call_count += 1
        raise IOError("network error")

    for _ in range(2):
        with pytest.raises(IOError):
            await flaky()

    with pytest.raises(CircuitBreakerOpen):
        await flaky()

    assert call_count == 2  # third call was blocked


# ---------------------------------------------------------------------------
# Tests — reset
# ---------------------------------------------------------------------------

def test_reset_returns_to_closed():
    cb = CircuitBreaker("test-reset", failure_threshold=2)

    def bad():
        raise ValueError("x")

    for _ in range(2):
        with pytest.raises(ValueError):
            cb.call(bad)

    assert cb.state is CircuitState.OPEN
    cb.reset()
    assert cb.state is CircuitState.CLOSED
