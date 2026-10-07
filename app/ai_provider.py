"""Capa mínima e intercambiable para llamar a un proveedor de IA.

Regla del proyecto (CLAUDE.md, "Enfoque de IA del portafolio"): el portafolio no
se casa con un proveedor. Cada proveedor es una clase pequeña que implementa
`generate()`; elegir uno u otro es configuración (variables del .env), no
reescribir los demos.

Variables de entorno:
    AI_PROVIDER   nombre registrado en PROVIDERS ("" o "none" = modo en vivo apagado)
    AI_MODEL      modelo a usar con ese proveedor
    AI_API_KEY    clave del proveedor (SECRETO: solo en el .env del servidor, nunca en el repo)

Hoy PROVIDERS está VACÍO a propósito: el primer proveedor se elige verificando
sus páginas oficiales (ticket QAP-14), no de memoria. Mientras tanto el modo en
vivo está apagado y los demos muestran los ejemplos pregenerados.

`FakeProvider` (para pruebas) vive en app/tests/fakes.py y NO está registrado:
no se puede activar por variable de entorno en producción.
"""
import logging
from dataclasses import dataclass
from typing import Callable, Optional

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Completion:
    """Respuesta de un proveedor, ya normalizada."""
    text: str
    provider: str
    model: str
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None


class ProviderError(Exception):
    """El proveedor falló (red, error del servidor, respuesta inválida, timeout...)."""


class ProviderQuotaExceeded(ProviderError):
    """Se agotó la cuota o el límite de peticiones del proveedor (típicamente un 429)."""


class Provider:
    """Interfaz que cumple cada proveedor. Los errores se reportan con ProviderError."""

    name = "base"

    def __init__(self, model: str):
        self.model = model

    def generate(self, system: str, user: str, *, max_tokens: int, timeout: float) -> Completion:
        raise NotImplementedError


# nombre -> fábrica(model, api_key) -> Provider. VACÍO hasta resolver QAP-14.
PROVIDERS: dict[str, Callable[[str, Optional[str]], Provider]] = {}


def build_provider(name: Optional[str], model: Optional[str], api_key: Optional[str]) -> Optional[Provider]:
    """Crea el proveedor configurado, o None si el modo en vivo está apagado.

    Nunca lanza por una configuración errónea: un error de tipeo en el .env no debe
    tumbar el sitio. En ese caso queda apagado, con un aviso en el log (sin la clave).
    """
    name = (name or "").strip().lower()
    if name in ("", "none"):
        return None
    factory = PROVIDERS.get(name)
    if factory is None:
        log.warning("AI_PROVIDER=%r no está registrado: modo en vivo apagado", name)
        return None
    if not (model or "").strip():
        log.warning("AI_PROVIDER=%r requiere AI_MODEL: modo en vivo apagado", name)
        return None
    if not (api_key or "").strip():
        log.warning("AI_PROVIDER=%r requiere AI_API_KEY: modo en vivo apagado", name)
        return None
    return factory(model.strip(), api_key.strip())
