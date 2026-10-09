"""Pruebas unitarias del limitador de intentos de login (login_throttle.py, QAP-20 / H6). Reloj simulado: sin dormir."""
import pytest

from login_throttle import LoginThrottle


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


@pytest.fixture
def clock():
    return Clock()


def throttle(clock, **kw):
    return LoginThrottle(**{"max_failures": 3, "window_seconds": 60, "clock": clock, **kw})


def test_a_new_address_is_not_blocked(clock):
    assert throttle(clock).retry_after("1.1.1.1") == 0


def test_blocks_after_the_maximum_number_of_failures_and_not_before(clock):
    t = throttle(clock)
    for _ in range(2):
        t.record_failure("1.1.1.1")
    assert t.retry_after("1.1.1.1") == 0
    t.record_failure("1.1.1.1")
    assert t.retry_after("1.1.1.1") > 0


def test_retry_after_counts_down_until_the_oldest_failure_leaves_the_window(clock):
    t = throttle(clock)
    for _ in range(3):
        t.record_failure("1.1.1.1")
    assert t.retry_after("1.1.1.1") == 60
    clock.advance(25)
    assert t.retry_after("1.1.1.1") == 35
    clock.advance(35)
    assert t.retry_after("1.1.1.1") == 0


def test_old_failures_stop_counting(clock):
    t = throttle(clock)
    t.record_failure("1.1.1.1")
    t.record_failure("1.1.1.1")
    clock.advance(61)
    t.record_failure("1.1.1.1")
    assert t.retry_after("1.1.1.1") == 0                 # solo cuenta 1 dentro de la ventana


def test_the_block_is_lifted_when_the_window_slides_past_the_failures(clock):
    t = throttle(clock)
    for _ in range(3):
        t.record_failure("1.1.1.1")
    clock.advance(60)
    assert t.retry_after("1.1.1.1") == 0
    t.record_failure("1.1.1.1")
    assert t.retry_after("1.1.1.1") == 0                 # empieza de cero


def test_addresses_are_independent(clock):
    t = throttle(clock)
    for _ in range(3):
        t.record_failure("1.1.1.1")
    assert t.retry_after("1.1.1.1") > 0 and t.retry_after("2.2.2.2") == 0


def test_success_clears_only_that_address(clock):
    t = throttle(clock)
    for _ in range(3):
        t.record_failure("1.1.1.1")
        t.record_failure("2.2.2.2")
    t.record_success("1.1.1.1")
    assert t.retry_after("1.1.1.1") == 0 and t.retry_after("2.2.2.2") > 0


def test_checking_does_not_consume_attempts(clock):
    t = throttle(clock)
    for _ in range(50):
        t.retry_after("1.1.1.1")
    assert t.retry_after("1.1.1.1") == 0


def test_memory_is_bounded_even_if_an_attacker_rotates_addresses(clock):
    t = throttle(clock, max_tracked=100)
    for n in range(1000):
        t.record_failure(f"10.0.{n // 256}.{n % 256}")
    assert t.tracked() <= 100


def test_expired_entries_are_dropped_so_memory_does_not_grow_forever(clock):
    t = throttle(clock, max_tracked=100)
    for n in range(50):
        t.record_failure(f"10.0.0.{n}")
    clock.advance(61)
    t.record_failure("9.9.9.9")
    assert t.tracked() == 1


def test_when_full_the_entries_that_are_not_blocked_are_evicted_first(clock):
    # Una dirección ya bloqueada no se descarta para hacer sitio a direcciones con un solo fallo.
    t = throttle(clock, max_tracked=3)
    for _ in range(3):
        t.record_failure("attacker")
        clock.advance(1)
    for n in range(5):
        t.record_failure(f"other{n}")
        clock.advance(1)
    assert t.tracked() <= 3
    assert t.retry_after("attacker") > 0


@pytest.mark.parametrize("kw", [{"max_failures": 0}, {"window_seconds": 0}, {"max_tracked": 0}])
def test_invalid_settings_are_rejected(clock, kw):
    with pytest.raises(ValueError):
        throttle(clock, **kw)
