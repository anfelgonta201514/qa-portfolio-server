"""Capa mínima e intercambiable para llamar a un proveedor de IA.

Regla del proyecto (CLAUDE.md, "Enfoque de IA del portafolio"): el portafolio no
se casa con un proveedor. Cada proveedor es una clase pequeña que implementa
`generate()`; elegir uno u otro es configuración (variables del .env), no
reescribir los demos.

Variables de entorno:
    AI_PROVIDER   nombre registrado en PROVIDERS ("" o "none" = modo en vivo apagado)
    AI_MODEL      modelo a usar con ese proveedor
    AI_API_KEY    clave del proveedor (SECRETO: solo en el .env del servidor, nunca en el repo)

El primer proveedor, Groq, se eligió verificando sus páginas oficiales, no de
memoria (QAP-14; comparativa y fuentes en docs/proveedores-ia.md). Registrarlo NO
activa nada: el modo en vivo sigue apagado hasta poner AI_PROVIDER en el .env y
conectar un endpoint, así que los demos muestran los ejemplos pregenerados.

`FakeProvider` (para pruebas) vive en app/tests/fakes.py y NO está registrado:
no se puede activar por variable de entorno en producción.
"""
import json
import logging
import urllib.error
import urllib.request
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


class GroqProvider(Provider):
    """Groq, vía su API compatible con chat completions (solo librería estándar, sin dependencias).

    Todo lo de aquí sale de la documentación oficial de Groq (leída el 2026-10-07):
      - POST https://api.groq.com/openai/v1/chat/completions, `Authorization: Bearer <clave>`.
      - El tope de salida es `max_completion_tokens`; `max_tokens` está obsoleto.
      - El texto está en choices[0].message.content y los tokens en usage.{prompt,completion}_tokens.
      - 429 = límite de cuota; el cuerpo de error es {"error": {"message", "type"}}.
      - Los modelos `openai/gpt-oss-*` razonan: `reasoning_effort` low|medium|high (medium por
        defecto) e `include_reasoning` (true por defecto). Se pide esfuerzo `low` y sin el texto
        del razonamiento. La documentación NO dice si los tokens de razonamiento cuentan contra
        el tope de salida: si lo consumen, `content` puede venir vacío y el servicio responde
        con el ejemplo pregenerado (reason="empty_response").

    La clave solo viaja en la cabecera: nunca se registra ni aparece en un mensaje de error, y de
    los errores del servidor se usa solo el código HTTP (el cuerpo podría repetir la entrada).
    """

    name = "groq"
    URL = "https://api.groq.com/openai/v1/chat/completions"
    TEMPERATURE = 0.3
    REASONING_MODELS = ("openai/gpt-oss-",)

    def __init__(self, model: str, api_key: str):
        super().__init__(model)
        self._api_key = api_key

    def _body(self, system: str, user: str, max_tokens: int) -> dict:
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_completion_tokens": max_tokens,
            "temperature": self.TEMPERATURE,
        }
        if self.model.startswith(self.REASONING_MODELS):
            body["reasoning_effort"] = "low"
            body["include_reasoning"] = False
        return body

    def generate(self, system: str, user: str, *, max_tokens: int, timeout: float) -> Completion:
        request = urllib.request.Request(
            self.URL,
            data=json.dumps(self._body(system, user, max_tokens)).encode("utf-8"),
            headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                raise ProviderQuotaExceeded("groq: límite de cuota (429)") from None
            raise ProviderError(f"groq: HTTP {exc.code}") from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise ProviderError("groq: no se pudo conectar o se agotó el tiempo de espera") from None
        except ValueError:
            raise ProviderError("groq: respuesta que no es JSON") from None

        try:
            content = payload["choices"][0]["message"].get("content")
        except (KeyError, IndexError, TypeError, AttributeError):
            raise ProviderError("groq: respuesta con una forma inesperada") from None

        usage = payload.get("usage") if isinstance(payload, dict) else None
        usage = usage if isinstance(usage, dict) else {}
        return Completion(
            text=content or "",
            provider=self.name,
            model=self.model,
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
        )


# nombre -> fábrica(model, api_key) -> Provider.
PROVIDERS: dict[str, Callable[[str, Optional[str]], Provider]] = {
    "groq": lambda model, api_key: GroqProvider(model, api_key),
}


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
