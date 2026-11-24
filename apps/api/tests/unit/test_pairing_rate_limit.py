from app.adapters.http.pairing_rate_limit import PairingRateLimiter


class FakeClock:
    def __init__(self) -> None:
        self.value = 100.0

    def __call__(self) -> float:
        return self.value


def test_pairing_rate_limit_resets_after_window() -> None:
    clock = FakeClock()
    limiter = PairingRateLimiter(max_attempts=2, window_seconds=10, clock=clock)

    assert limiter.allow("127.0.0.1") is True
    assert limiter.allow("127.0.0.1") is True
    assert limiter.allow("127.0.0.1") is False

    clock.value += 10
    assert limiter.allow("127.0.0.1") is True


def test_pairing_rate_limit_bounds_tracked_clients() -> None:
    limiter = PairingRateLimiter(max_attempts=1, window_seconds=60, max_clients=2)

    assert limiter.allow("client-1") is True
    assert limiter.allow("client-2") is True
    assert limiter.allow("client-3") is True
    assert limiter.tracked_client_count == 2
