"""Límites de uso de los demos en vivo: por visitante y tope diario global.

Aunque el proveedor sea gratis, hacen falta: sin límite por visitante, una sola
persona agota la cuota diaria entera y el demo queda muerto para los demás; y si
algún día el proveedor es de pago, el tope diario es lo que acota el gasto.

Diseño:
- Ventana deslizante por visitante: máximo N peticiones en los últimos W segundos.
- Tope diario global (día UTC): máximo D peticiones al proveedor entre todos.
- Decisión ATÓMICA (candado): con muchos hilos a la vez nunca se permite más de lo debido.
- Una petición rechazada no consume cuota. Un visitante nuevo rechazado no crea entrada,
  así que la memoria queda acotada por el tope diario.
- El reloj es inyectable para probar sin esperar.

Limitación conocida: el estado vive EN MEMORIA de un proceso. Funciona porque Gunicorn
corre con un solo worker (ver app/Dockerfile; hay una prueba que lo vigila). Si algún día
hay varios workers, cada uno tendría su propio contador y habría que mover esto a
Postgres. Un reinicio o deploy también pone los contadores en cero.
"""
import math
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Callable, Deque, Dict, Optional

SECONDS_PER_DAY = 86400


@dataclass(frozen=True)
class LimitDecision:
    allowed: bool
    reason: Optional[str] = None       # "visitor" | "daily" cuando allowed=False
    retry_after: int = 0               # segundos hasta que vuelva a haber cupo


class DemoLimiter:
    def __init__(self, per_visitor: int, window_seconds: int, daily_cap: int,
                 clock: Callable[[], float] = time.time):
        if per_visitor < 1 or window_seconds < 1 or daily_cap < 1:
            raise ValueError("los límites deben ser enteros positivos")
        self.per_visitor = per_visitor
        self.window = window_seconds
        self.daily_cap = daily_cap
        self._clock = clock
        self._lock = threading.Lock()
        self._visits: Dict[str, Deque[float]] = {}
        self._day = self._day_of(self._clock())
        self._today = 0

    @staticmethod
    def _day_of(ts: float) -> int:
        return int(ts // SECONDS_PER_DAY)  # día UTC

    def _roll_day(self, now: float) -> None:
        day = self._day_of(now)
        if day != self._day:
            self._day = day
            self._today = 0

    def check_and_consume(self, visitor_id: str) -> LimitDecision:
        """Decide y, si permite, consume cupo. Atómico."""
        with self._lock:
            now = self._clock()
            self._roll_day(now)

            if self._today >= self.daily_cap:
                next_midnight = (self._day + 1) * SECONDS_PER_DAY
                return LimitDecision(False, "daily", max(1, math.ceil(next_midnight - now)))

            stamps = self._visits.get(visitor_id)
            if stamps is not None:
                while stamps and stamps[0] <= now - self.window:
                    stamps.popleft()
                if len(stamps) >= self.per_visitor:
                    return LimitDecision(False, "visitor", max(1, math.ceil(stamps[0] + self.window - now)))
            else:
                stamps = None

            # permitido: recién aquí se crea la entrada y se consume cupo
            if stamps is None:
                stamps = self._visits[visitor_id] = deque()
            stamps.append(now)
            self._today += 1
            self._prune(now)
            return LimitDecision(True)

    def _prune(self, now: float) -> None:
        """Descarta visitantes sin peticiones dentro de la ventana (acota la memoria)."""
        if len(self._visits) < 256:
            return
        for vid in [v for v, s in self._visits.items() if not s or s[-1] <= now - self.window]:
            del self._visits[vid]

    def stats(self) -> dict:
        with self._lock:
            self._roll_day(self._clock())
            return {"today": self._today, "daily_cap": self.daily_cap, "tracked_visitors": len(self._visits)}
