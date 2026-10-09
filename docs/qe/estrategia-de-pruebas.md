# Estrategia de pruebas — portafolio web (`qa-portfolio-server`)

> QAP-15 · 2026-10-09 · Generado con Claude a partir del código, las pruebas, Jira y el sitio en producción. **Qué está verificado y qué no** se marca en cada hallazgo: *ejecutado* = lo corrí; *leído* = salió de leer el código, sin ejecutarlo.

## 1. Qué se prueba y para qué

**Sistema bajo prueba:** el sitio `https://andresqe.duckdns.org` — Nginx → Gunicorn → Flask → PostgreSQL en Docker, sobre una instancia Oracle Cloud. Piezas: sitio público bilingüe (ES/EN), API `/api/projects`, panel `/admin`, estado real del CI leído de GitHub (`ci_status.py`), página de demos de IA con ejemplos pregenerados, capa de IA apagada (`ai_*.py`), y el deploy automático por GitHub Actions.

**Es un portafolio, no un producto con usuarios de pago.** Eso ordena las prioridades: lo que más daña es que el sitio **diga algo falso o se vea roto** ante un reclutador, y que alguien con acceso al panel o a la API pueda **reescribir el contenido**. Una caída de una hora duele poco; una insignia "passing" falsa duele mucho (ya ocurrió: QAP-8).

## 2. Objetivos de calidad, por prioridad

| # | Objetivo | Por qué importa aquí |
|---|---|---|
| 1 | **Honestidad del contenido** (badges de CI, "no en vivo" en los demos, modelo declarado) | La credibilidad es el producto |
| 2 | **Integridad del contenido** (solo el admin escribe) | El servidor es público |
| 3 | **Disponibilidad tras cada deploy** | El deploy es automático en cada push a `main` |
| 4 | **Paridad ES/EN** (mismas páginas, mismos ejemplos) | Dos audiencias |
| 5 | **Seguridad de la capa de IA** (límites, sin registrar entradas) | Hoy apagada; crítica el día que se active |

## 3. Cobertura actual (verificada)

*Ejecutado el 2026-10-09 en un entorno limpio con `app/requirements.txt`:* **222 pruebas pasan y 3 se omiten a propósito** (API real de Restful-booker, Groq mínima, Groq medición). Total 225.

| Componente | Pruebas | Qué cubren |
|---|---|---|
| Capa de IA (`ai_limits`, `ai_service`, `ai_provider`, limpieza y prompts) | 162 | Límites con concurrencia, privacidad, proveedor simulado, limpieza de salida |
| Herramienta de medición (`score_measure`) | 27 | Filtro de seguridad del código generado |
| Demos (`test_demos`) | 23 | Páginas, escape de HTML, paridad ES/EN, ejemplos de API ejecutados |
| Estado del CI (`test_ci_status`) | 13 | Estados, caché, GitHub caído, datos viejos |
| API `/api/projects` | 47 *(QAP-20; antes 0)* | Contrato, validación, autorización, JSON |
| Panel `/admin` (login, CRUD, logout, límite de intentos) | 37 + 14 del limitador *(QAP-20; antes 0)* | CSRF, rutas protegidas, formularios inválidos |
| Humo contra PostgreSQL real | 7 opt-in *(pasan en CI con un servicio postgres:16-alpine)* | Brecha SQLite vs. PostgreSQL |
| **Modelos, seed, resto de páginas públicas** | **0** | — |
| **Nginx, deploy, Certbot** | **0** | solo el smoke test post-deploy (`/` y `/api/projects`) |

**Lectura honesta:** la parte más nueva (IA, demos, CI) está muy probada; la parte más expuesta a un atacante (API de escritura y login) **no tiene ninguna prueba automática**.

## 4. Hallazgos de la exploración

Probados con el cliente de pruebas de Flask sobre SQLite en memoria (*ejecutado*). **Límite:** producción usa PostgreSQL, que es más estricto; lo marcado así no se confirmó allí.

| ID | Hallazgo | Evidencia | Severidad |
|---|---|---|---|
| H1 | *(En corrección: QAP-19 añade la puerta en `deploy.yml`; falta verificarla en GitHub.)* **El deploy no ejecuta las pruebas.** El único workflow (`deploy.yml`) hace SSH, despliega y verifica `/` y `/api/projects`. Un push con las 225 pruebas en rojo se despliega igual | *leído*: solo existe `.github/workflows/deploy.yml` | Alta |
| H2 | *(Corregido en QAP-20; falta verificarlo en producción.)* `POST /api/projects` sin el campo `title` responde **500** (`KeyError`), no 400 | *ejecutado*: 500 | Media |
| H3 | *(Corregido en QAP-20.)* Las escrituras de la API sin sesión responden **302 hacia el login (HTML)**, no 401 | *ejecutado*: 302 en POST, PUT y DELETE | Baja (confunde a clientes, no abre nada) |
| H4 | *(Corregido: QAP-20 rechaza con 415 todo lo que no sea JSON y QAP-21 fija `Secure`, `HttpOnly` y `SameSite=Lax` en la cookie.)* La API está **exenta de CSRF**, acepta cualquier `Content-Type` (`get_json(force=True)`) y autentica con la cookie de sesión; la cookie no declara `SameSite` ni `Secure` | *ejecutado*: con sesión, `text/plain` crea un proyecto (201); *config*: `SAMESITE=None`, `SECURE=False`, `HTTPONLY=True`. **No verificado:** que un navegador real lo permita (los navegadores modernos aplican `Lax` por defecto, lo que lo frenaría) | Media (hipótesis, no explotación) |
| H5 | *(Corregido en QAP-20 con validación previa; **confirmado contra PostgreSQL real en CI el 2026-10-09** (run 37997389897): ver `test_postgres_smoke.py`.)* La API acepta `week="abc"` y un título de 500 caracteres (201) | *ejecutado en SQLite*. En PostgreSQL la columna `title` es `VARCHAR(120)` y esperaría un error 500; **no verificado allí** | Media |
| H6 | *(Corregido en QAP-20: 429 tras 5 fallos en 10 min por dirección.)* `/admin/login` no tiene límite de intentos | *leído*: ni `admin.py` ni `nginx.conf` tienen limitador (`limit_req`); está en el backlog de la semana 14 | Media |
| H7 | *(Corregido en QAP-21 en el repositorio; falta verlo en la respuesta real tras el despliegue: lo comprueba el paso "Security headers" del deploy.)* El sitio en producción no envía cabeceras de seguridad (`Strict-Transport-Security`, `X-Frame-Options`, `X-Content-Type-Options`, CSP) | *ejecutado*: `curl -I` solo devuelve `Server: nginx/1.27.5`; *leído*: `nginx.conf` no tiene ningún `add_header`; HTTP redirige a HTTPS (301) | Media |
| H9 | *(Hallazgo nuevo durante QAP-21; corregido.)* El botón de borrar del panel usaba `onsubmit="return confirm('¿Borrar {{ título }}?')"`: un título con una comilla simple se salía de la cadena de JavaScript, y una CSP sin `'unsafe-inline'` bloquearía el atributo y borraría **sin pedir confirmación** | *ejecutado*: la plantilla escapa HTML pero no JavaScript; ahora es `data-confirm` + `static/admin.js` y hay una prueba con un título malicioso | Baja (solo el admin escribe títulos) |
| H8 | Los steps con `continue-on-error` figuran como "success" en la API de GitHub, así que el badge de CI **no refleja** un fallo del booking flow | *leído*: documentado en `ci_status.py`; es coherente con la regla del repo hermano | Informativa |

Lo que **funcionó bien** (*ejecutado*): lectura pública 200; un id inexistente 404; el login sin token CSRF 400; `/admin/` sin sesión redirige; JSON inválido 400; el sitio respondió 200 en `/`, `/en/`, `/demos`, `/api/projects` y `/admin/login` en 0,07-0,31 s (una sola muestra por URL).

## 5. Enfoque por niveles

| Nivel | Qué | Herramienta | Estado |
|---|---|---|---|
| Unitario / componente | Lógica pura (límites, limpieza, estados del CI) | pytest + dobles | Hecho |
| De integración (Flask) | Rutas, sesión, CSRF, modelos contra SQLite | pytest + `test_client` | **Falta** (H2-H5) |
| Contrato de la API | Códigos, cuerpos, errores de `/api/projects` | pytest | **Falta** |
| Seguridad básica | Cookies, cabeceras, límite de intentos | pytest + `curl -I` | **Falta** (H4, H6, H7) |
| Humo post-deploy | Sitio responde por HTTPS tras cada push | `curl` en `deploy.yml` | Hecho (2 URLs); ampliar |
| Exploratorio manual | Pantallas en móvil/escritorio, ES/EN | A mano | Sin sistematizar |
| Calidad de la IA | Rúbrica de 30 puntos con Groq real | `score_measure.py` + rúbrica | Hecho (`docs/rubrica-medicion-ia.md`) |

**Decisión de diseño:** las pruebas de integración correrán contra **SQLite**, no PostgreSQL, por velocidad y simplicidad. El costo conocido son las diferencias de rigor (H5); se cubre con **una pasada de humo contra Postgres en CI** (servicio `postgres` en el workflow) o, como mínimo, documentando la brecha.

## 6. Puertas de calidad (quality gates)

- **Antes de desplegar (propuesta, H1):** un job `test` en `deploy.yml` que ejecute `pytest app/tests` y sea requisito (`needs:`) del job de deploy. Las 3 pruebas opt-in (`network`, `groq_live`) quedan fuera por diseño.
- **Entrada a pruebas:** el código compila, `docker compose build` termina y la base arranca.
- **Salida para publicar:** 0 pruebas rojas, ningún hallazgo de severidad Alta abierto, y el smoke test post-deploy en verde.

## 7. Datos y entornos

- **Local / CI de pruebas:** SQLite en memoria; cada prueba crea su propio usuario y proyectos (sin datos compartidos).
- **Producción:** única; no encontré en el repo un entorno de staging. **Nunca se prueba la escritura contra producción**: el usuario admin real existe allí.
- **Secretos:** nunca en el chat ni en archivos; las pruebas usan valores de prueba propios.

## 8. Riesgos de la estrategia

| Riesgo | Mitigación |
|---|---|
| Un solo mantenedor (Andres) | El review de PRs con cron ya existe (QAP-3); añadir la puerta de H1 |
| Las pruebas de IA miden calidad con un solo muestreo | Ya declarado en la rúbrica; no usarlas como criterio de salida de despliegue |
| Dependencia de la API pública de GitHub para los badges (60 peticiones/h sin autenticar) | Ya mitigado: caché de 5 min, estado "sin datos" en lugar de "passing" |
| Brecha SQLite vs. PostgreSQL | Ver sección 5 |

## 9. Hoja de ruta (por orden de valor)

1. Puerta de pruebas antes del deploy (H1) — mayor valor, menor esfuerzo.
2. Pruebas de la API y del login (H2, H3, H5): protegen el único punto de escritura.
3. Cookies y cabeceras (H4, H7) y límite de intentos (H6).
4. Ampliar el smoke test a `/demos`, `/en/` y `/admin/login`.

Detalle de casos y esfuerzo: [`plan-de-pruebas.md`](plan-de-pruebas.md). Historias y riesgos: [`analisis-de-historias.md`](analisis-de-historias.md).
