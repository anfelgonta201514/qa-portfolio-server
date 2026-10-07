"""Pruebas de DemoLimiter: lo que protege la cuota (y el dinero) de los demos en vivo.

Correr:  python -m pytest app/tests -q
"""
import threading
import time

import pytest

from ai_limits import DemoLimiter
from fakes import Clock


@pytest.fixture
def slow_consume(monkeypatch):
    """Agranda la ventana entre COMPROBAR el límite y CONSUMIR el cupo.

    Sin candado, con esto muchos hilos pasan la comprobación antes de que ninguno consuma,
    y el límite se supera. Con el candado correcto no cambia nada (solo tarda unos ms más).
    """
    import ai_limits
    from collections import deque

    class SlowDeque(deque):
        def append(self, item):
            time.sleep(0.0005)
            super().append(item)

    monkeypatch.setattr(ai_limits, "deque", SlowDeque)


def make(per_visitor=3, window=60, daily=100, clock=None):
    clock = clock or Clock()
    return DemoLimiter(per_visitor, window, daily, clock=clock), clock


# ---------- por visitante

def test_allows_up_to_the_limit_then_blocks_with_retry_after():
    limiter, clock = make(per_visitor=3, window=60)
    for _ in range(3):
        assert limiter.check_and_consume("a").allowed
    blocked = limiter.check_and_consume("a")
    assert not blocked.allowed
    assert blocked.reason == "visitor"
    assert 1 <= blocked.retry_after <= 60


def test_visitor_is_allowed_again_when_the_window_slides_past():
    limiter, clock = make(per_visitor=2, window=60)
    assert limiter.check_and_consume("a").allowed
    assert limiter.check_and_consume("a").allowed
    assert not limiter.check_and_consume("a").allowed
    clock.advance(61)
    assert limiter.check_and_consume("a").allowed


def test_window_is_sliding_not_fixed():
    limiter, clock = make(per_visitor=2, window=60)
    limiter.check_and_consume("a")          # t=0
    clock.advance(40)
    limiter.check_and_consume("a")          # t=40
    clock.advance(25)                       # t=65: la de t=0 ya salió, la de t=40 no
    assert limiter.check_and_consume("a").allowed
    assert not limiter.check_and_consume("a").allowed


def test_visitors_are_independent():
    limiter, _ = make(per_visitor=1)
    assert limiter.check_and_consume("a").allowed
    assert not limiter.check_and_consume("a").allowed
    assert limiter.check_and_consume("b").allowed


# ---------- tope diario

def test_daily_cap_blocks_everyone_even_fresh_visitors():
    limiter, _ = make(per_visitor=5, daily=3)
    for visitor in "abc":
        assert limiter.check_and_consume(visitor).allowed
    blocked = limiter.check_and_consume("nuevo")
    assert not blocked.allowed
    assert blocked.reason == "daily"


def test_daily_cap_resets_at_the_next_utc_midnight():
    limiter, clock = make(per_visitor=5, daily=1)   # el reloj arranca a las 08:00 UTC
    assert limiter.check_and_consume("a").allowed
    blocked = limiter.check_and_consume("b")
    assert blocked.reason == "daily"
    assert blocked.retry_after == pytest.approx(16 * 3600, abs=2)   # faltan ~16 h para medianoche
    clock.advance(16 * 3600 + 1)
    assert limiter.check_and_consume("b").allowed


def test_a_refused_request_does_not_consume_quota():
    limiter, _ = make(per_visitor=1, daily=10)
    limiter.check_and_consume("a")
    for _ in range(50):
        assert not limiter.check_and_consume("a").allowed     # rechazadas por visitante
    assert limiter.stats()["today"] == 1                      # solo la permitida cuenta


def test_visitor_limit_is_checked_without_burning_daily_quota_of_others():
    limiter, _ = make(per_visitor=1, daily=2)
    assert limiter.check_and_consume("a").allowed
    assert not limiter.check_and_consume("a").allowed         # no debe gastar el cupo diario
    assert limiter.check_and_consume("b").allowed             # sigue habiendo cupo para otro


# ---------- concurrencia: nunca se permite más de lo debido

def test_concurrent_requests_from_one_visitor_never_exceed_the_limit(slow_consume):
    limiter = DemoLimiter(5, 600, 1000)
    allowed = []
    barrier = threading.Barrier(100)

    def worker():
        barrier.wait()
        allowed.append(limiter.check_and_consume("a").allowed)

    threads = [threading.Thread(target=worker) for _ in range(100)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert sum(allowed) == 5


def test_concurrent_requests_from_many_visitors_never_exceed_the_daily_cap(slow_consume):
    limiter = DemoLimiter(5, 600, 20)
    allowed = []
    barrier = threading.Barrier(200)

    def worker(i):
        barrier.wait()
        allowed.append(limiter.check_and_consume(f"v{i}").allowed)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(200)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert sum(allowed) == 20
    assert limiter.stats()["today"] == 20


# ---------- memoria acotada

def test_memory_is_bounded_by_the_daily_cap_even_with_thousands_of_visitors():
    limiter, _ = make(per_visitor=5, daily=50)
    for i in range(10_000):
        limiter.check_and_consume(f"ip-{i}")
    assert limiter.stats()["tracked_visitors"] <= 50


def test_expired_visitors_are_pruned():
    limiter, clock = make(per_visitor=5, window=60, daily=10_000)
    for i in range(400):
        limiter.check_and_consume(f"ip-{i}")
    clock.advance(120)                                        # todas las ventanas vencieron
    limiter.check_and_consume("otro")                         # dispara la poda
    assert limiter.stats()["tracked_visitors"] < 10


# ---------- configuración inválida

@pytest.mark.parametrize("args", [(0, 60, 10), (1, 0, 10), (1, 60, 0), (-1, 60, 10)])
def test_invalid_limits_are_rejected(args):
    with pytest.raises(ValueError):
        DemoLimiter(*args)
