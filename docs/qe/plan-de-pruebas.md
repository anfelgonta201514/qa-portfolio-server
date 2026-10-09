# Plan de pruebas — portafolio web (`qa-portfolio-server`)

> QAP-15 · 2026-10-09 · Estructura inspirada en IEEE 829, reducida a lo que aplica a un proyecto de una persona. Complementa la [estrategia](estrategia-de-pruebas.md) (el porqué) con el qué, quién, cuánto y cuándo. Los hallazgos `H1-H8` y las historias `HU-01…HU-07` están definidos en la estrategia y en el [análisis de historias](analisis-de-historias.md).

| | |
|---|---|
| **Identificador** | PP-PORTAFOLIO-01 |
| **Versión / fecha** | 1.0 · 2026-10-09 |
| **Responsable** | Andres Gonzalez (ejecuta y decide); Claude asiste en el diseño |
| **Tickets relacionados** | QAP-15 (este plan); los fixes salen como tickets nuevos |

## 1. Alcance

**Se prueba:** sitio público ES/EN, API `/api/projects`, panel `/admin`, estado del CI, página `/demos`, humo post-deploy, y la configuración de seguridad de cookies y cabeceras.

**No se prueba (y por qué):**
- **El modo en vivo de los demos:** no existe (QAP-18). Se planifica cuando exista.
- **La calidad de las respuestas de IA:** ya tiene su propia medición (`docs/rubrica-medicion-ia.md`).
- **Carga y rendimiento:** una sola instancia Always Free para un portafolio; una prueba de carga contra producción sería un riesgo en sí misma.
- **Compatibilidad entre navegadores:** el sitio es HTML renderizado en servidor sin JavaScript propio relevante; se cubre con una pasada manual (sección 8).
- **La infraestructura (Oracle, Certbot, systemd):** se vigila con el chequeo de logs (QAP-10) y la renovación automática, no con pruebas funcionales.

## 2. Enfoque

Pytest con el cliente de pruebas de Flask sobre SQLite en memoria; cada prueba crea sus datos y no comparte estado. Casos nuevos se nombran `test_[área]_[escenario]_[resultado]`. Las pruebas que toquen la red o gasten cuota quedan opt-in (`-m network`, `-m groq_live`), como hoy. Una pasada de humo contra PostgreSQL real en CI cubre las diferencias con SQLite (H5).

## 3. Casos de prueba

*Actualización QAP-20: los casos TC-API-01…10 y TC-ADM-01…08 están automatizados (98 pruebas) y TC-SEC/TC-DEP siguen como se indica; el humo contra PostgreSQL está escrito pero **sin ejecutar**.*

Estado: ✅ ya automatizado · ⬜ por automatizar · 👁 manual. Prioridad: A (protege integridad/credibilidad), M, B.

### API (HU-05)

| ID | Caso | Resultado esperado | Prio | Estado |
|---|---|---|---|---|
| TC-API-01 | `GET /api/projects` | 200, lista ordenada por `week`, `tech_stack` como lista | A | ✅ (QAP-20) |
| TC-API-02 | `GET /api/projects/<id>` existente / inexistente | 200 / 404 | M | ✅ (QAP-20) |
| TC-API-03 | `POST`, `PUT`, `DELETE` sin sesión | **No** modifican datos (hoy 302; objetivo 401, H3) | A | ✅ (QAP-20) |
| TC-API-04 | `POST` con sesión y datos válidos | 201 y el proyecto aparece en el `GET` | A | ✅ (QAP-20) |
| TC-API-05 | `POST` sin `title` o sin `description` | 400 con mensaje (hoy 500, H2) | A | ✅ (QAP-20) |
| TC-API-06 | `POST` con `week` no numérico o título de más de 120 caracteres | 400 (hoy 201 en SQLite, H5) | A | ✅ (QAP-20) |
| TC-API-07 | `POST` con JSON inválido | 400 | M | ✅ (QAP-20) |
| TC-API-08 | `PUT` con un solo campo | Cambia solo ese campo | M | ✅ (QAP-20) |
| TC-API-09 | `DELETE` existente y luego `GET` | 204 y luego 404 | M | ✅ (QAP-20) |
| TC-API-10 | `POST` con sesión y `Content-Type: text/plain` | Rechazado (hoy 201, H4) | A | ✅ (QAP-20) |

### Panel admin (HU-04, HU-05)

| ID | Caso | Resultado esperado | Prio | Estado |
|---|---|---|---|---|
| TC-ADM-01 | Login válido | Redirige al dashboard | A | ✅ (QAP-20) |
| TC-ADM-02 | Login con contraseña o usuario incorrectos | 401 y mensaje genérico (no revela cuál falló) | A | ✅ (QAP-20) |
| TC-ADM-03 | `POST /admin/login` sin token CSRF | 400 | A | ✅ (QAP-20) |
| TC-ADM-04 | Cualquier ruta de `/admin/` sin sesión | Redirige al login | A | ✅ (QAP-20) |
| TC-ADM-05 | Alta, edición y borrado desde el formulario | El cambio se ve en el dashboard y en la API | M | ✅ (QAP-20) |
| TC-ADM-06 | Alta con `week` no numérico | Error de formulario, no 500 | M | ✅ (QAP-20) |
| TC-ADM-07 | Logout | Cierra la sesión; `/admin/` vuelve a pedir login | M | ✅ (QAP-20) |
| TC-ADM-08 | Varios intentos fallidos seguidos | Se frena (H6; hoy no existe) | A | ✅ (QAP-20) |

### Sitio público y estado del CI (HU-01, HU-02, HU-03)

| ID | Caso | Resultado esperado | Prio | Estado |
|---|---|---|---|---|
| TC-PUB-01 | Cada página (`/`, `/experiencia`, `/proyectos/ui-playwright`, `/demos` y sus `/en/…`) | 200 | A | ⬜ (solo `/demos` está cubierta) |
| TC-PUB-02 | Ruta inexistente | 404, sin traza | M | ⬜ |
| TC-PUB-03 | Cada página enlaza a su equivalente en el otro idioma | Enlace correcto | M | ⬜ |
| TC-PUB-04 | Estados del CI (`passing`/`failing`/`unknown`), GitHub caído, datos viejos | Nunca "passing" por omisión | A | ✅ (13 pruebas) |
| TC-PUB-05 | Demos: aviso "no en vivo", modelo declarado, sin cuadro de entrada, HTML escapado | Se cumple en ES y EN | A | ✅ (23 pruebas) |
| TC-PUB-06 | Paridad ES/EN de ejemplos y textos de los demos | Mismos identificadores | M | ✅ |

### Seguridad y despliegue (HU-06)

| ID | Caso | Resultado esperado | Prio | Estado |
|---|---|---|---|---|
| TC-SEC-01 | Cookie de sesión | `HttpOnly`, `Secure` y `SameSite=Lax` (hoy sin `Secure` ni `SameSite`, H4) | A | ✅ (QAP-21) |
| TC-SEC-02 | Cabeceras de respuesta en producción | `Strict-Transport-Security`, `X-Content-Type-Options`, `X-Frame-Options`/CSP (hoy ausentes, H7) | M | ✅ (QAP-21; en el repo con pruebas, en producción con el paso del deploy) |
| TC-DEP-01 | **Las pruebas corren antes del deploy** | Un test rojo bloquea el despliegue (hoy no, H1) | A | ⬜ |
| TC-DEP-02 | Smoke post-deploy | `/`, `/api/projects`, `/demos`, `/en/` y `/admin/login` responden | M | ⬜ (hoy 2 de 5) |
| TC-DEP-03 | HTTP redirige a HTTPS | 301 | M | ✅ (QAP-21: paso "Security headers" del deploy; verificado a mano el 2026-10-09) |

### Capa de IA (HU-07, futura)

Ya cubierta por 162 pruebas (límites con concurrencia, privacidad de la entrada, respaldo a ejemplos pregenerados). Al activar el modo en vivo se añadirán: pruebas del endpoint, del formulario, de la IP real vía `X-Real-IP` y la verificación en producción.

## 4. Criterios de aprobación

- **Una prueba pasa** cuando el resultado observado coincide con el esperado sin intervención.
- **El plan se da por cumplido** cuando: todas las pruebas prioridad A están automatizadas y en verde, no queda abierto ningún hallazgo de severidad Alta, y TC-DEP-01 está activo.
- **Hallazgos Medios** pueden quedar abiertos si están documentados con su razón.

## 5. Suspensión y reanudación

Se detiene la ejecución si falla el arranque de la app o la base (no tiene sentido seguir) o si una prueba intenta escribir en producción (error de configuración: se corrige antes de continuar). Se reanuda con la suite completa, no solo con lo que falló.

## 6. Entregables

Este plan; pruebas en `app/tests/`; cambios en `deploy.yml`; un reporte de ejecución al final (formato de [`reporte-ejecutivo.md`](reporte-ejecutivo.md)); tickets nuevos para cada fix.

## 7. Entorno

Local y CI: Python 3.x con `app/requirements.txt` + `pytest` + `requests`, SQLite en memoria. Humo de integración: servicio PostgreSQL del workflow. Producción: solo lectura y verificación de cabeceras con `curl`.

## 8. Esfuerzo estimado

**Es una estimación por analogía, no una medición:** supongo 15-20 minutos por prueba de integración sencilla (con su preparación) y más para lo que toca el workflow o el servidor. No hay datos históricos propios de este tipo de trabajo para calibrarla; el margen es amplio a propósito.

| Actividad | Horas |
|---|---|
| Puerta de pruebas en `deploy.yml` (TC-DEP-01) | 1 - 2 |
| Pruebas de la API (TC-API-01…10) | 3 - 4 |
| Pruebas del panel admin (TC-ADM-01…07) | 3 - 4 |
| Páginas públicas (TC-PUB-01…03) | 1,5 - 2 |
| Cookies y cabeceras (TC-SEC-01, 02) | 2 - 3 |
| Smoke ampliado (TC-DEP-02) | 0,5 - 1 |
| PostgreSQL en CI | 1,5 - 3 |
| Pasada manual (móvil/escritorio, ES/EN, 2 navegadores) | 1,5 |
| Reporte de ejecución | 1 |
| **Subtotal de pruebas** | **≈ 15 - 21** |
| **Fixes de los hallazgos** (H2-H7: validación, `SameSite`/`Secure`, cabeceras en Nginx, límite de intentos) | **≈ 6 - 10** |
| **Total** | **≈ 21 - 31** |

**Orden sugerido:** (1) puerta de pruebas; (2) API y admin con sus fixes; (3) seguridad; (4) lo demás. Las dos primeras dan la mayor parte del valor.

## 9. Riesgos del plan

| Riesgo | Efecto | Respuesta |
|---|---|---|
| Un fix cambia el comportamiento de la API (p. ej. 302 → 401) | Rompe algún consumidor | Hoy el único consumidor es el propio sitio; verificarlo antes |
| SQLite oculta errores que PostgreSQL sí da | Falsa confianza (H5) | Pasada de humo contra Postgres en CI |
| Añadir rate limiting en memoria con varios workers | Los límites no se comparten | Mantener un solo proceso (ya es una regla de la capa de IA) |
| El plan crece más que el sitio | Esfuerzo desproporcionado para un portafolio | Parar tras el paso (2) si el valor marginal baja |
