"""Validación de los datos de un proyecto, compartida por la API y por el formulario del panel (QAP-20).

Existe para que la entrada inválida reciba un 400 con un mensaje claro EN LUGAR de llegar a la base de datos: en SQLite
(pruebas) un título de 500 caracteres se guarda, pero en PostgreSQL la columna es VARCHAR(120) y daría un error 500.
Los límites de abajo reflejan las columnas de models.Project; si cambian allí, cambian aquí.
"""
TITLE_MAX = 120
STACK_MAX = 255      # el stack se guarda unido por comas en una sola columna VARCHAR(255)
REPO_URL_MAX = 255

_REQUIRED = ("title", "description", "tech_stack")
_UNSET = object()


def _text(data, key, max_len, errors):
    value = data[key]
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{key}: debe ser un texto no vacío")
        return _UNSET
    value = value.strip()
    if max_len is not None and len(value) > max_len:
        errors.append(f"{key}: máximo {max_len} caracteres")
        return _UNSET
    return value


def _stack(value, errors):
    if isinstance(value, str):
        items = [part.strip() for part in value.split(",")]
    elif isinstance(value, list) and all(isinstance(item, str) for item in value):
        items = [item.strip() for item in value]
        if any("," in item for item in items):
            errors.append("tech_stack: ningún elemento puede contener comas")
            return _UNSET
    else:
        errors.append("tech_stack: debe ser una lista de textos o un texto separado por comas")
        return _UNSET
    items = [item for item in items if item]
    if not items:
        errors.append("tech_stack: debe tener al menos un elemento")
        return _UNSET
    joined = ",".join(items)
    if len(joined) > STACK_MAX:
        errors.append(f"tech_stack: máximo {STACK_MAX} caracteres en total")
        return _UNSET
    return joined


def _repo_url(value, errors):
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        errors.append("repo_url: debe ser un texto o null")
        return _UNSET
    value = value.strip()
    if len(value) > REPO_URL_MAX:
        errors.append(f"repo_url: máximo {REPO_URL_MAX} caracteres")
        return _UNSET
    if not value.lower().startswith(("http://", "https://")):
        errors.append("repo_url: debe empezar por http:// o https://")   # el sitio público lo usa como enlace
        return _UNSET
    return value


def _week(value, errors):
    if value is None or value == "":
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        errors.append("week: debe ser un entero mayor o igual que 1, o null")
        return _UNSET
    return value


def parse_project(data: dict, *, partial: bool = False):
    """Devuelve (campos_limpios, errores). Con partial=True solo se validan las claves presentes (PUT)."""
    errors: list = []
    clean: dict = {}
    if not partial:
        for key in _REQUIRED:
            if key not in data:
                errors.append(f"{key}: es obligatorio")
    if "title" in data:
        clean["title"] = _text(data, "title", TITLE_MAX, errors)
    if "description" in data:
        clean["description"] = _text(data, "description", None, errors)
    if "tech_stack" in data:
        clean["tech_stack"] = _stack(data["tech_stack"], errors)
    if "repo_url" in data:
        clean["repo_url"] = _repo_url(data["repo_url"], errors)
    if "week" in data:
        clean["week"] = _week(data["week"], errors)
    clean = {key: value for key, value in clean.items() if value is not _UNSET}
    return clean, errors
