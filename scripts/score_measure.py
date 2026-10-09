"""Puntuación AUTOMÁTICA de una medición de los demos de IA en vivo (QAP-17).

Uso (desde la raíz del repo):
    python scripts/score_measure.py .groq-measure/baseline-v1.json
    python scripts/score_measure.py .groq-measure/baseline-v1.json .groq-measure/results.json   # compara

Qué mide (lo que NO depende de mi juicio; la parte manual está en docs/rubrica-medicion-ia.md):
  - formato: negritas de markdown (`**`) y guiones no separables (U+2010/U+2011)
  - truncado (si la corrida lo registró), tokens y segundos
  - "señales de invención": frases concretas que se sabe que NO están en la entrada. Son un INDICIO
    (búsquedas de texto), no una prueba: una frase puede aparecer por otra razón.
  - para los tests de API: EJECUTA el código generado contra la API real y cuenta pasan/fallan.

SEGURIDAD: el código lo generó un modelo, así que es no confiable. Antes de ejecutarlo se revisa con un
análisis estático (AST): solo se permiten unas pocas importaciones, ninguna llamada peligrosa y URLs
únicamente de la API de práctica. Si no pasa la revisión, NO se ejecuta y se informa.
LÍMITE: es defensa en profundidad, NO un sandbox. Un análisis estático no puede descartar todo
(p. ej. una URL armada por concatenación en tiempo de ejecución). Por eso solo se usa con las 6
entradas propias del repo, nunca con entradas de visitantes.
Necesita `requests` y `pytest` en el intérprete que lo corre; para la parte de red hace falta conexión.
"""
import argparse
import ast
import json
import pathlib
import re
import subprocess
import sys
import tempfile
from urllib.parse import urlparse

ALLOWED_IMPORTS = {"pytest", "requests", "json", "uuid", "random", "string", "time", "datetime", "re"}
FORBIDDEN_CALLS = {"eval", "exec", "open", "compile", "__import__", "input", "breakpoint",
                   "getattr", "setattr", "delattr", "globals", "locals", "vars", "type"}
FORBIDDEN_NAMES = {"os", "sys", "subprocess", "socket", "shutil", "pathlib", "ctypes", "importlib"}
ALLOWED_HOST = "restful-booker.herokuapp.com"

# Señales de invención: frases que NO están en la entrada de ese ejemplo (indicio, no prueba).
TRAPS = {
    ("testcases", "reserva"): [r"es obligatorio", r"formato de fecha inv", r"[“\"]Confirmar[”\"]"],
    ("testcases", "login"): [r"\b256\b", r"longitud\s+(m[ií]nima|m[aá]xima)", r"demasiado\s+corta", r"\bEntrar\b"],
    ("bugs", "locator"): [r"p[aá]gina de error", r"redirig"],
    ("bugs", "allure"): [r"--help"],
}


def is_safe(code: str):
    """(True, '') si el código generado pasa la revisión estática; si no, (False, motivo)."""
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return False, f"no es Python válido ({exc.msg})"
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] not in ALLOWED_IMPORTS:
                    return False, f"importa {alias.name}"
        elif isinstance(node, ast.ImportFrom):
            if (node.module or "").split(".")[0] not in ALLOWED_IMPORTS:
                return False, f"importa de {node.module}"
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CALLS:
            return False, f"llama a {node.func.id}()"
        elif isinstance(node, ast.Name) and (node.id in FORBIDDEN_NAMES or node.id.startswith("__")):
            return False, f"usa {node.id}"
        elif isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            return False, f"accede a {node.attr}"
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) and re.match(r"https?://", node.value):
            # Se compara el host EXACTO: con startswith, "https://restful-booker.herokuapp.com.evil.example"
            # pasaría el filtro (el dominio permitido es solo el comienzo del dominio del atacante).
            parsed = urlparse(node.value)
            if parsed.scheme != "https" or parsed.hostname != ALLOWED_HOST:
                return False, f"URL no permitida: {node.value[:40]}"
    return True, ""


def run_api_code(code: str, name: str):
    """Ejecuta el código en una carpeta temporal y devuelve (pasan, fallan, xfail, nota)."""
    ok, why = is_safe(code)
    if not ok:
        return None, None, None, f"NO EJECUTADO (bloqueado por seguridad: {why})"
    with tempfile.TemporaryDirectory() as tmp:
        path = pathlib.Path(tmp) / f"test_{name}.py"
        path.write_text(code, encoding="utf-8")
        try:
            r = subprocess.run(
                [sys.executable, "-m", "pytest", str(path), "-q", "-p", "no:cacheprovider",
                 "-p", "no:allure_pytest", "-p", "no:allure_pytest_bdd"],
                cwd=tmp, capture_output=True, text=True, timeout=240,
            )
        except subprocess.TimeoutExpired:
            return None, None, None, "NO EJECUTADO (tiempo agotado)"
    count = lambda word: int(m.group(1)) if (m := re.search(rf"(\d+) {word}", r.stdout)) else 0
    return count("passed"), count("failed") + count("error"), count("xfailed"), ""


def score_row(row, execute_api):
    text = row.get("text") or ""
    out = {
        "id": f"{row['demo']}/{row['example']}",
        "mode": row.get("mode"),
        "seconds": row.get("seconds"),
        "tok_in": row.get("input_tokens"),
        "tok_out": row.get("output_tokens"),
        "bold": text.count("**"),
        "nb_hyphen": text.count("‑") + text.count("‐"),
        "truncated": row.get("truncated"),
        "traps": [p for p in TRAPS.get((row["demo"], row["example"]), []) if re.search(p, text, re.I)],
        "api": None,
    }
    if row["demo"] == "apitests" and text:
        calls = len(re.findall(r"requests\.(get|post|put|patch|delete|request)\(", text))
        out["unique_data"] = bool(re.search(r"uuid|random", text))
        out["timeouts"] = calls > 0 and text.count("timeout=") >= calls
        out["not_executed_note"] = bool(re.search(r"not executed|no ejecutado|sin ejecutar", text, re.I))
        if execute_api:
            p, f, x, note = run_api_code(text, row["example"])
            out["api"] = note or f"{p} pasan, {f} fallan" + (f", {x} xfail" if x else "")
            out["api_pass"], out["api_fail"] = p, f
    return out


def load(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def table(rows):
    print(f"{'respuesta':20} {'modo':8} {'seg':>5} {'t_in':>5} {'t_out':>6} {'**':>3} {'U+2011':>6} {'cortada':>7}  señales de invención / API")
    for r in rows:
        extra = []
        if r["traps"]:
            extra.append(f"invención: {len(r['traps'])}")
        if r["api"]:
            extra.append(f"API real: {r['api']}")
        if "unique_data" in r:
            extra.append(f"datos únicos: {'sí' if r['unique_data'] else 'no'}")
            extra.append(f"timeouts: {'sí' if r['timeouts'] else 'no'}")
            extra.append(f"avisa que no se ejecutó: {'sí' if r['not_executed_note'] else 'no'}")
        trunc = {True: "SÍ", False: "no", None: "n/d"}[r["truncated"]]
        print(f"{r['id']:20} {str(r['mode']):8} {r['seconds'] or 0:>5} {r['tok_in'] or 0:>5} {r['tok_out'] or 0:>6} "
              f"{r['bold']:>3} {r['nb_hyphen']:>6} {trunc:>7}  {' | '.join(extra) or '-'}")


def totals(rows):
    return {
        "respuestas_en_vivo": sum(1 for r in rows if r["mode"] == "live"),
        "tokens_totales": sum((r["tok_in"] or 0) + (r["tok_out"] or 0) for r in rows),
        "negritas": sum(r["bold"] for r in rows),
        "guiones_no_separables": sum(r["nb_hyphen"] for r in rows),
        "señales_de_invención": sum(len(r["traps"]) for r in rows),
        "api_pasan": sum(r.get("api_pass") or 0 for r in rows),
        "api_fallan": sum(r.get("api_fail") or 0 for r in rows),
        "cortadas": sum(1 for r in rows if r["truncated"]),
    }


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+", help="uno o dos resultados (.json); con dos, se comparan")
    ap.add_argument("--no-api", action="store_true", help="no ejecutar el código de API contra la API real")
    args = ap.parse_args()

    scored = []
    for path in args.files[:2]:
        print(f"\n=== {path}")
        rows = [score_row(r, not args.no_api) for r in load(path)]
        table(rows)
        scored.append((path, totals(rows)))
        print("TOTALES:", json.dumps(scored[-1][1], ensure_ascii=False))

    if len(scored) == 2:
        (_, a), (_, b) = scored
        print("\n=== CAMBIO (segundo menos primero)")
        for key in a:
            delta = b[key] - a[key]
            print(f"{key:26} {a[key]:>7} -> {b[key]:>7}   ({delta:+d})")


if __name__ == "__main__":
    main()
