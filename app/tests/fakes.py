"""Dobles de prueba para la capa de IA. NO se importan desde código de producción."""
import threading

from ai_provider import Completion, Provider


class FakeProvider(Provider):
    """Proveedor simulado: responde lo que se le configure, o lanza lo que se le indique."""

    name = "fake"

    def __init__(self, model="fake-model", text="respuesta simulada", raises=None, input_tokens=11, output_tokens=22,
                 truncated=False):
        super().__init__(model)
        self.text = text
        self.raises = raises
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.truncated = truncated
        self.calls = []          # (system, user, max_tokens, timeout) de cada llamada
        self._lock = threading.Lock()

    def generate(self, system, user, *, max_tokens, timeout):
        with self._lock:
            self.calls.append((system, user, max_tokens, timeout))
        if self.raises is not None:
            raise self.raises
        return Completion(self.text, self.name, self.model, self.input_tokens, self.output_tokens, self.truncated)


class Clock:
    """Reloj manual para probar ventanas y cambios de día sin esperar."""

    def __init__(self, start=1_800_000_000.0):
        self.now = start

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds
