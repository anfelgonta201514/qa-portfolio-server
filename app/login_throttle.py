"""Límite de intentos fallidos de login por dirección (QAP-20, hallazgo H6 de docs/qe).

Ventana deslizante en memoria: tras `max_failures` fallos dentro de `window_seconds`, la dirección queda bloqueada hasta que
el fallo más viejo salga de la ventana. Un login correcto borra los fallos de esa dirección.

Decisiones y límites (no son defectos ocultos):
- Es POR DIRECCIÓN, no por usuario: bloquear por usuario dejaría que cualquiera deje fuera al administrador con solo escribir
  contraseñas malas. A cambio, un ataque repartido entre muchas direcciones no se frena.
- Vive en la memoria de UN proceso: solo vale con un único proceso de Gunicorn (como los límites de la capa de IA). Con
  varios workers cada uno tendría su propio contador y el límite real se multiplicaría. Se pierde al reiniciar.
- La memoria está acotada (`max_tracked`): al llenarse se descartan primero las direcciones aún no bloqueadas.
"""
import math
import threading
import time
from collections import deque


class LoginThrottle:
    def __init__(self, max_failures: int = 5, window_seconds: int = 600, max_tracked: int = 10_000, clock=time.monotonic):
        if max_failures < 1 or window_seconds < 1 or max_tracked < 1:
            raise ValueError("max_failures, window_seconds y max_tracked deben ser >= 1")
        self.max_failures = max_failures
        self.window = window_seconds
        self.max_tracked = max_tracked
        self._clock = clock
        self._lock = threading.Lock()
        self._failures: dict = {}
        self._last_sweep = clock()

    def _prune(self, key, now):
        dq = self._failures.get(key)
        if dq is None:
            return None
        while dq and now - dq[0] >= self.window:
            dq.popleft()
        if not dq:
            del self._failures[key]
            return None
        return dq

    def _sweep(self, now):
        for key in list(self._failures):
            self._prune(key, now)
        self._last_sweep = now

    def _evict_one(self):
        unblocked = [k for k, dq in self._failures.items() if len(dq) < self.max_failures]
        candidates = unblocked or list(self._failures)
        victim = min(candidates, key=lambda k: self._failures[k][-1])
        del self._failures[victim]

    def retry_after(self, key: str) -> int:
        """Segundos hasta que `key` pueda volver a intentarlo (0 = no está bloqueada). No consume intentos."""
        with self._lock:
            now = self._clock()
            dq = self._prune(key, now)
            if dq is None or len(dq) < self.max_failures:
                return 0
            return max(1, math.ceil(dq[0] + self.window - now))

    def record_failure(self, key: str) -> None:
        with self._lock:
            now = self._clock()
            if now - self._last_sweep >= self.window:
                self._sweep(now)
            dq = self._prune(key, now)
            if dq is None:
                dq = self._failures[key] = deque()
            dq.append(now)
            if len(self._failures) > self.max_tracked:
                self._evict_one()

    def record_success(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)

    def tracked(self) -> int:
        with self._lock:
            return len(self._failures)
