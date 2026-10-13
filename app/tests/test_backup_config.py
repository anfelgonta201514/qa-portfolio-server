"""Pruebas de la configuración del backup de PostgreSQL (semana 14).

Docker y systemd no se pueden arrancar aquí, así que se leen como texto los scripts y las unidades y se comprueba
que dicen lo que deben. Lo que NO prueban: que pg_dump funcione ni que la restauración dé una base correcta (eso lo
demuestra `deploy/restore-test.sh` en el servidor) ni que el timer dispare (eso lo ve `systemctl list-timers`).
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DEPLOY = ROOT / "deploy"
BACKUP = (DEPLOY / "backup-db.sh").read_text(encoding="utf-8")
RESTORE = (DEPLOY / "restore-test.sh").read_text(encoding="utf-8")
SERVICE = (DEPLOY / "qa-portfolio-backup.service").read_text(encoding="utf-8")
TIMER = (DEPLOY / "qa-portfolio-backup.timer").read_text(encoding="utf-8")


def _code(text):
    """El script sin líneas de comentario (los comentarios pueden nombrar cosas que el código no hace)."""
    return "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("#"))


@pytest.mark.parametrize("script", [BACKUP, RESTORE], ids=["backup-db", "restore-test"])
def test_scripts_fail_fast(script):
    assert re.search(r"^set -euo pipefail$", script, flags=re.M)


@pytest.mark.parametrize("script", [BACKUP, RESTORE], ids=["backup-db", "restore-test"])
def test_scripts_use_lf_line_endings(script):
    # Con CRLF bash falla en el servidor ("$'\r': command not found"); .gitattributes ya lo fuerza, esto lo vigila.
    assert "\r" not in script


@pytest.mark.parametrize("script", [BACKUP, RESTORE], ids=["backup-db", "restore-test"])
def test_scripts_contain_no_secret_values(script):
    code = _code(script)
    assert not re.search(r"PGPASSWORD|POSTGRES_PASSWORD|password\s*=", code, flags=re.I)
    assert "source .env" not in code and ". .env" not in code, "no hace falta leer el .env: el contenedor ya tiene las credenciales"


def test_backup_dumps_from_inside_the_postgres_container_without_a_tty():
    code = _code(BACKUP)
    assert "docker compose exec -T postgres" in code
    assert "pg_dump" in code
    # Las credenciales las expande el shell del contenedor (comillas simples), no el del anfitrión.
    assert re.search(r"sh -c 'pg_dump -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\"", code)


def test_backup_is_written_to_a_partial_file_and_only_renamed_after_verification():
    code = _code(BACKUP)
    assert ".partial" in code
    assert code.index("gzip -t") < code.index('mv "$partial" "$final"')
    assert code.index("database dump complete") < code.index('mv "$partial" "$final"')


def test_a_failed_backup_leaves_no_partial_file_behind():
    assert re.search(r"trap 'rm -f \"\$partial\"' EXIT", BACKUP)


def test_backup_files_are_private_to_the_owner():
    assert re.search(r"^umask 077$", BACKUP, flags=re.M)


def test_rotation_keeps_seven_daily_and_four_weekly_by_default():
    assert 'KEEP_DAILY="${KEEP_DAILY:-7}"' in BACKUP
    assert 'KEEP_WEEKLY="${KEEP_WEEKLY:-4}"' in BACKUP
    assert re.search(r'date -u \+%u\)" = "7"', BACKUP), "la copia semanal es la del domingo"


def test_rotation_survives_an_empty_folder_under_pipefail():
    # Regresión hallada en la prueba real: weekly/ vacío (lunes a sábado) hacía que `ls` devolviera 2 y, con pipefail,
    # el script abortaba ya hecho el backup, dejando el servicio de systemd en "failed".
    code = _code(BACKUP)
    assert re.search(r'\{ ls -1t "\$dir"/db-\*\.sql\.gz 2>/dev/null \|\| true; \} \|', code)


def test_rotation_only_touches_files_that_the_script_itself_creates():
    assert "db-*.sql.gz" in BACKUP
    assert not re.search(r"rm\s+-rf?\s", _code(BACKUP)), "nada de rm recursivo en el script de backup"


def test_restore_test_never_targets_the_real_database():
    code = _code(RESTORE)
    assert "restore_check_" in code
    assert re.search(r'DROP DATABASE IF EXISTS \\"\$tmpdb\\"', code), "solo borra la base temporal"
    assert not re.search(r'DROP DATABASE[^\n]*\$real|DROP DATABASE[^\n]*POSTGRES_DB', code)
    assert '"$tmpdb" != "$real"' in code


def test_restore_test_cleans_up_even_when_it_fails():
    assert re.search(r"trap cleanup EXIT", RESTORE)


def test_service_runs_the_backup_script_as_the_deploy_user():
    assert "ExecStart=/bin/bash /home/ubuntu/qa-portfolio-server/deploy/backup-db.sh" in SERVICE
    assert re.search(r"^User=ubuntu$", SERVICE, flags=re.M)
    assert re.search(r"^Type=oneshot$", SERVICE, flags=re.M)
    assert "Requires=docker.service" in SERVICE


def test_timer_is_daily_and_catches_up_after_downtime():
    assert re.search(r"^OnCalendar=\*-\*-\* \d{2}:\d{2}:00 UTC$", TIMER, flags=re.M), "diario y con zona horaria explícita"
    assert re.search(r"^Persistent=true$", TIMER, flags=re.M)
    assert re.search(r"^WantedBy=timers\.target$", TIMER, flags=re.M)


def test_timer_and_service_share_the_same_unit_name():
    # systemd asocia el .timer con el .service del mismo nombre si no se indica otra cosa.
    assert (DEPLOY / "qa-portfolio-backup.timer").exists() and (DEPLOY / "qa-portfolio-backup.service").exists()
    assert "Unit=" not in TIMER


# ---------- scripts/pull-backups.ps1: baja los dumps a otro equipo (solo lectura sobre el servidor)

PULL = (ROOT / "scripts" / "pull-backups.ps1").read_text(encoding="utf-8")


def test_pull_script_carries_no_server_data():
    # El repo es público: la IP y la clave se leen de SERVER_INFO.local.md (gitignorado), nunca van en el script.
    assert not re.search(r"\b\d{1,3}(\.\d{1,3}){3}\b", PULL), "no debe haber ninguna IP escrita"
    assert "SERVER_INFO.local.md" in PULL
    assert "BEGIN" not in PULL and "PRIVATE KEY" not in PULL


def test_pull_script_is_ascii_only_because_powershell_5_reads_utf8_without_bom_as_ansi():
    assert PULL.isascii()


def test_pull_script_refuses_to_trust_an_unknown_host_key():
    assert "StrictHostKeyChecking=yes" in PULL
    assert "IdentitiesOnly=yes" in PULL and "BatchMode=yes" in PULL


def test_pull_script_never_deletes_anything():
    # Sin el bloque de ayuda <# ... #> (dice "del servidor", que no es el alias `del`) ni los comentarios de línea.
    code = re.sub(r"<#.*?#>", "", PULL, flags=re.S)
    code = "\n".join(l for l in code.splitlines() if not l.lstrip().startswith("#"))
    assert not re.search(r"Remove-Item|\brm\b|^\s*del\s|\brmdir\b|Clear-Content", code, flags=re.I | re.M)
    # -Force solo en New-Item (crear carpetas), nunca para borrar
    assert re.findall(r"-Force", code) == ["-Force"] and "New-Item -ItemType Directory -Force" in code


def test_pull_script_refuses_destinations_inside_a_git_repo_and_the_restricted_keys():
    assert re.search(r"Test-Path -LiteralPath \(Join-Path \$probe '\.git'\)", PULL)
    assert "dentro de un repositorio git" in PULL
    assert "qa_portfolio_(logs|deploy)" in PULL, "las claves con comando forzado no sirven para scp"


def test_pull_script_verifies_every_downloaded_dump_and_fails_on_a_corrupt_one():
    assert "GZipStream" in PULL and "Test-GzipFile" in PULL
    assert re.search(r"if \(\$bad -gt 0\) \{ Fail", PULL)


def test_every_documented_way_to_run_the_pull_script_bypasses_the_default_execution_policy():
    # Regresión: con la política por defecto de Windows ("scripts deshabilitados") `powershell -File x.ps1` falla.
    # Mis pruebas locales usaban -ExecutionPolicy Bypass y lo ocultaron; los comandos documentados deben llevarlo.
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    invocations = re.findall(r"^\s*(powershell\b.*scripts.pull-backups\.ps1.*)$", readme + "\n" + PULL, flags=re.M)
    assert len(invocations) >= 4, "el README y el script documentan dos comandos cada uno"
    for line in invocations:
        assert "-ExecutionPolicy Bypass" in line, line


def test_footer_check_leaves_margin_for_the_lines_pg_dump_writes_after_it():
    # Hallazgo: el pie de pg_dump quedaba en la 5.ª línea desde el final (después vienen "--", una vacía,
    # "\unrestrict <token>" y otra vacía) y el script miraba solo las últimas 5: sin margen. Un pg_dump que añadiera
    # una línea más haría que un backup bueno se diera por cortado.
    n = int(re.search(r"tail -n (\d+) \| grep -q \"PostgreSQL database dump complete\"", BACKUP).group(1))
    trailing_today = ["--", "", chr(92) + "unrestrict abc123", ""]  # lo que escribe pg_dump 16 tras el pie
    dump_end = ["-- PostgreSQL database dump complete"] + trailing_today
    assert dump_end[-n:][0] == dump_end[0], "el pie debe caer dentro de las últimas N líneas"
    extra = ["", "-- futura línea 1", "-- futura línea 2", "-- futura línea 3"]
    assert (dump_end + extra)[-n:].count("-- PostgreSQL database dump complete") == 1, f"N={n} no deja margen"
    assert n >= 20
