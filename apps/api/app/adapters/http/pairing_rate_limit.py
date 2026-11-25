"""Bounded process-local rate limiter for pairing-code redemption attempts."""

from collections import OrderedDict, deque
from collections.abc import Callable
from threading import Lock
from time import monotonic


class PairingRateLimiter:
    def __init__(
        self,
        max_attempts: int = 10,
        window_seconds: float = 60,
        max_clients: int = 4096,
        clock: Callable[[], float] | None = None,
    ) -> None:
        if max_attempts < 1 or window_seconds <= 0 or max_clients < 1:
            raise ValueError("Pairing rate-limit settings must be positive")
        self._max_attempts = max_attempts
        self._window_seconds = window_seconds
        self._max_clients = max_clients
        self._clock = clock or monotonic
        self._attempts: OrderedDict[str, deque[float]] = OrderedDict()
        self._lock = Lock()

    @property
    def tracked_client_count(self) -> int:
        with self._lock:
            return len(self._attempts)

    def allow(self, client_key: str) -> bool:
        now = self._clock()
        with self._lock:
            if client_key not in self._attempts and len(self._attempts) >= self._max_clients:
                self._attempts.popitem(last=False)
            attempts = self._attempts.setdefault(client_key, deque())
            self._attempts.move_to_end(client_key)
            while attempts and now - attempts[0] >= self._window_seconds:
                attempts.popleft()
            if len(attempts) >= self._max_attempts:
                return False
            attempts.append(now)
            return True
