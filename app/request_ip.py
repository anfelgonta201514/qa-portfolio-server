"""Dirección del visitante, la misma regla para el límite de login (QAP-20) y para los demos en vivo (QAP-18)."""
from flask import request


def client_ip() -> str:
    """IP real del visitante.

    Nginx fija X-Real-IP con la dirección real (`proxy_set_header X-Real-IP $remote_addr`) y Flask solo recibe tráfico de
    Nginx (el puerto 8000 no está publicado). Nunca X-Forwarded-For: un cliente puede añadirle lo que quiera y así
    esquivar cualquier límite. Se usa como CLAVE de límites en memoria; no se registra en ningún log.
    """
    return (request.headers.get("X-Real-IP") or request.remote_addr or "desconocida").strip()[:64]
