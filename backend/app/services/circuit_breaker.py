"""
Circuit Breaker for Firecrawl - Prevents cost explosion when Firecrawl is failing.

Pattern:
- Track consecutive failures
- Open circuit after N failures
- Auto-recover after cooldown period
"""

import time
from enum import Enum
from dataclasses import dataclass
from threading import Lock

from app.logger import logger


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 5  # Open after N consecutive failures
    cooldown_seconds: int = 60  # Wait before trying again
    half_open_max_calls: int = 3  # Test with N calls in half-open state


class FirecrawlCircuitBreaker:
    """Circuit breaker for Firecrawl API calls."""
    
    def __init__(self, config: CircuitBreakerConfig = None):
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.consecutive_failures = 0
        self.last_failure_time = 0
        self.half_open_calls = 0
        self._lock = Lock()
    
    def can_call(self) -> tuple[bool, str]:
        """Check if Firecrawl call is allowed.
        
        Returns:
            Tuple of (allowed, reason)
        """
        with self._lock:
            if self.state == CircuitState.CLOSED:
                return True, "circuit_closed"
            
            elif self.state == CircuitState.OPEN:
                # Check if cooldown period has passed
                if time.time() - self.last_failure_time >= self.config.cooldown_seconds:
                    logger.info("Circuit breaker: transitioning to HALF_OPEN")
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_calls = 0
                    return True, "circuit_half_open"
                else:
                    remaining = int(self.config.cooldown_seconds - (time.time() - self.last_failure_time))
                    return False, f"circuit_open_cooldown_{remaining}s"
            
            elif self.state == CircuitState.HALF_OPEN:
                if self.half_open_calls < self.config.half_open_max_calls:
                    self.half_open_calls += 1
                    return True, "circuit_half_open_testing"
                else:
                    return False, "circuit_half_open_max_calls"
            
            return False, "circuit_unknown_state"
    
    def record_success(self):
        """Record successful Firecrawl call."""
        with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                logger.info("Circuit breaker: recovered, transitioning to CLOSED")
                self.state = CircuitState.CLOSED
                self.consecutive_failures = 0
                self.half_open_calls = 0
            elif self.state == CircuitState.CLOSED:
                # Reset failure counter on success
                if self.consecutive_failures > 0:
                    logger.info(f"Circuit breaker: reset failure count (was {self.consecutive_failures})")
                    self.consecutive_failures = 0
    
    def record_failure(self):
        """Record failed Firecrawl call."""
        with self._lock:
            self.consecutive_failures += 1
            self.last_failure_time = time.time()
            
            if self.state == CircuitState.HALF_OPEN:
                logger.warning("Circuit breaker: failed in HALF_OPEN, reopening circuit")
                self.state = CircuitState.OPEN
                self.half_open_calls = 0
            
            elif self.state == CircuitState.CLOSED:
                if self.consecutive_failures >= self.config.failure_threshold:
                    logger.error(
                        f"🚨 Circuit breaker: OPENED after {self.consecutive_failures} failures "
                        f"(cooldown: {self.config.cooldown_seconds}s)"
                    )
                    self.state = CircuitState.OPEN
                else:
                    logger.warning(
                        f"Circuit breaker: failure {self.consecutive_failures}/{self.config.failure_threshold}"
                    )
    
    def get_status(self) -> dict:
        """Get circuit breaker status."""
        with self._lock:
            return {
                "state": self.state.value,
                "consecutive_failures": self.consecutive_failures,
                "failure_threshold": self.config.failure_threshold,
                "cooldown_seconds": self.config.cooldown_seconds,
                "time_since_last_failure": int(time.time() - self.last_failure_time) if self.last_failure_time > 0 else None
            }


# Global circuit breaker instance
_circuit_breaker: FirecrawlCircuitBreaker | None = None


def get_circuit_breaker() -> FirecrawlCircuitBreaker:
    """Get global circuit breaker instance (singleton)."""
    global _circuit_breaker
    if _circuit_breaker is None:
        _circuit_breaker = FirecrawlCircuitBreaker()
    return _circuit_breaker
