# Reporte de cierre — Semana 13 (2026-10-10)

> Generado con Claude. Cada cifra sale de una consulta de hoy: Jira (`project = QAP`, conector oficial), la API pública de GitHub, la suite ejecutada en un entorno limpio y peticiones de solo lectura a producción. Lo que no pude comprobar está marcado como tal. Complementa a [`reporte-qe-semana-12.md`](reporte-qe-semana-12.md) y a los cuatro documentos de [`docs/qe/`](qe/).

## Resumen ejecutivo

**La semana 13 queda cerrada.** Jira: **20 de 21 tickets en Done**; el único abierto es QAP-16, la comparativa de modelos, que era opcional y no se hizo. Producción está sana y hoy tiene: demos de IA **en vivo con Groq**, tres casos de estudio nuevos (API, CI/CD y BDD), una puerta de pruebas antes de cada despliegue, la API de escritura y el login con pruebas y correcciones, y cookies y cabeceras de seguridad.

| | Hoy |
|---|---|
| Tickets del proyecto | 21 · **20 Done** · 1 To Do (opcional) |
| Pruebas automáticas | **470** (460 pasan, 10 omitidas a propósito), 0 fallan |
| CI desde el 2026-10-07 | 15 ejecuciones: **14 verdes** y 1 roja, **intencional** (el PR 8, una prueba rota a propósito para verificar la puerta) · 11 de 11 pushes a `main` en verde |
| Pull requests de la semana | 3 fusionados (9, 10 y 11) y 1 cerrado sin fusionar a propósito (8) |
| Producción | 8 URLs en 200, 6 de 6 cabeceras de seguridad, 3 formularios en vivo en `/demos` |

**Una desviación del plan que conviene tener presente:** el plan de estudio pedía demos con la API de Claude. Se implementó una capa **multi-proveedor** y el primer proveedor es **Groq** (QAP-11 y QAP-14), porque la API de Claude se factura aparte del plan Pro y Groq es el único cuya documentación respalda enviar texto de visitantes. Está documentado y es una decisión de Andres.

## Qué se entregó

| Ticket | Entregable | Evidencia |
|---|---|---|
| QAP-11, 12, 13, 14 | Enfoque de IA general (no una marca), 3 demos con 6 ejemplos pregenerados ES/EN, capa de proveedor intercambiable con límites, y Groq elegido leyendo sus páginas oficiales | Sitio en producción (7 al 9 de octubre) |
| QAP-17 | Prompts y limpieza de salida mejorados y **medidos tres veces** con la misma rúbrica: **14 → 21 → 21 de 30** | `docs/rubrica-medicion-ia.md` |
| QAP-15 | Estrategia de pruebas, plan (29 casos), reporte ejecutivo y análisis de 7 historias | `docs/qe/` |
| QAP-19 | El despliegue **ya no arranca si las pruebas fallan** | Run verde en `main` y run rojo en el PR 8 con `Deploy` omitido |
| QAP-20 | API y login con 98 pruebas, validación, 401 JSON, 415 y límite de intentos (429) | Humo contra PostgreSQL real en CI; 429 visto en producción |
| QAP-21 | Cookies `Secure`/`HttpOnly`/`SameSite=Lax`, cabeceras de seguridad y CSP en modo informe | Respuesta real de producción |
| QAP-18 | **Modo en vivo encendido**: formulario, avisos de privacidad y de borrador sin verificar, límites, respaldo a ejemplos | 3 demos reales contra Groq en 1,2-2,2 s; el texto enviado no aparece en los logs |
| QAP-9 | Casos de estudio de API, CI/CD y BDD, y 4 casos que ya caben en un móvil | 6 páginas en 200; 375 px de ancho |
| QAP-16 | **No se hizo** (opcional) | — |

## Lo que mostró la medición de la IA (QAP-17)

- **Sólido y repetible, porque se arregla en código:** formato limpio (de 8 negritas y 16 guiones raros a 0) y que **todo el código de API generado pase** contra la API real (antes 8 pasaban y 3 fallaban).
- **No mejoró de forma fiable con prompts:** no inventar reglas, separar lo no definido y diagnosticar la causa de un fallo. La diferencia entre la v2 y la v3 (21 y 21) es ruido con 6 respuestas y un muestreo.
- **Decisión tomada:** dejar de iterar prompts. En producción lo vimos: el demo de tests de API inventó una `BASE_URL = "http://localhost:8000"` que la especificación no traía. Por eso cada respuesta viva lleva la etiqueta del modelo y la advertencia de borrador sin verificar.
- **Sesgo declarado:** puntúa Claude con una rúbrica que escribió Claude.

## Hallazgos de calidad de la semana (todos corregidos)

| | Hallazgo | Cómo se vio |
|---|---|---|
| H1 | El despliegue **no ejecutaba las pruebas** | Leyendo el único workflow |
| H2/H3 | La API daba 500 con datos incompletos y 302 (HTML) sin sesión | Cliente de pruebas de Flask |
| H4 | La API aceptaba cualquier tipo de contenido y la cookie no declaraba `SameSite` ni `Secure` | Cliente de pruebas + configuración |
| H5 | Un título largo se guardaba en SQLite pero PostgreSQL lo rechaza | **Confirmado en CI contra PostgreSQL real** |
| H6 | El login no tenía límite de intentos | Lectura del código |
| H7 | Sin cabeceras de seguridad | `curl -I` a producción |
| H9 | El botón de borrar metía el título del proyecto dentro de JavaScript y no habría pedido confirmación con una CSP estricta | Al preparar la CSP |
| — | La página de UI decía "8" escenarios con la leyenda "15 casos"; **cuatro casos de estudio medían 455-732 px en un móvil de 375**; el botón del formulario salía transparente | Solo se vieron **en un navegador real**, no con las pruebas |

Lección de proceso: las pruebas automáticas **no** veían varias de las cosas más visibles de esta semana. Lo del móvil, el botón y la cifra incorrecta salieron de abrir el sitio en un navegador.

## Cómo se probó (y qué se ha comprobado de las pruebas mismas)

- **De 215 a 470 pruebas** desde las 215 con las que cerró la sesión anterior (+255), repartidas en 15 archivos.
- Se plantaron **68 mutaciones** en el código nuevo (quitar una validación, una cabecera, un límite…) para comprobar que las pruebas las detectan: **las 68 caen**, pero **4 sobrevivieron al primer intento** (una advertencia que aparecía también en otra parte de la página, un enlace roto que solo se validaba por dominio…). Cada una acabó en una prueba reforzada.
- Errores propios corregidos: cifras mal contadas en comentarios de Jira (58 pruebas en lugar de 55; 21 mutaciones en lugar de 20) y el umbral de una prueba (esperaba 9 enlaces y eran 7). Los dos primeros ya estaban publicados en Jira y se corrigieron al releer; el tercero lo cazó la propia prueba.

## Riesgos y deuda abierta

**Seguridad y fiabilidad**
- **La CSP sigue en modo solo informe.** Falta mirar el panel con sesión iniciada antes de enforzarla.
- **No hay backup automático de PostgreSQL ni snapshot de Oracle** (están en el backlog de la semana 14). Hoy no existe copia de seguridad de la base: se podría reconstruir con el seed y recreando el usuario admin, pero eso no es un backup.
- El servidor llevaba ~90 días encendido (dato del 9 de octubre) y **el reinicio en frío (systemd) nunca se ha probado**.
- El límite de intentos de login y los de la IA **viven en memoria de un solo proceso**: se reinician con cada despliegue y no frenan ataques repartidos entre muchas direcciones.

**Modo en vivo**
- La **calidad de las respuestas es limitada** (ver arriba) y depende de un plan gratuito cuyos **límites reales de tu consola no se han verificado** (solo los de la documentación).
- **No hay traza de uso:** el servicio escribe una línea por llamada con los tokens, pero el logger de producción no está en nivel INFO, así que no aparece. Mejora opcional.
- **Concurrencia no probada bajo carga:** 4 hilos; si 4 personas generan a la vez, el resto espera hasta ~15 s.

**Contenido**
- La **traducción al inglés** de los tres casos de estudio no la ha revisado nadie.
- Las **cifras de los casos de estudio** son del 2026-10-10 y envejecen si cambia `qa-automation-portfolio`; las pruebas lo detectan solo en la máquina de Andres.
- La hipótesis de por qué el flujo de reserva fallaba en CI (el sitio de práctica limitando IPs de centros de datos) **sigue sin confirmarse**.

**Vigilar**
- `actions/checkout@v4` y `actions/setup-python@v5` usan Node 20 (en desuso) y `ubuntu-latest` pasa a Ubuntu 26 el **2026-10-19**: conviene mirar el primer run después de esa fecha.

## Decisiones de la semana

Groq como primer proveedor; los ejemplos pregenerados se quedan siempre como respaldo; el modo en vivo viene apagado y lo enciende Andres con una clave propia del servidor que nunca pasa por el chat; no seguir iterando prompts; las pruebas de integración usan SQLite más una pasada de humo contra PostgreSQL real; HSTS de 180 días sin `includeSubDomains` ni `preload` (no se deshace rápido); la CSP primero en modo informe; el límite de login es por dirección y no por usuario (para que nadie pueda dejar fuera al administrador); lo que Andres decide: cuándo un ticket pasa a Done.

## Semana 14 (lanzamiento): backlog actualizado

- ✅ **Ya hecho esta semana:** rate limiting en `/admin/login` (QAP-20).
- **Pendiente del plan:** backup automático de PostgreSQL (cron diario), snapshot semanal de Oracle desde la consola, validación con el prompt de "recruiter senior QA", y publicar en LinkedIn con la URL en el CV.
- **Pendiente del backlog del sitio** (`CONTEXT.md`, sección 3e): verificar que cada cifra del sitio sea defendible en entrevista, mantener `JOBS` sincronizado con el PDF del CV, sumar al portafolio lo de las semanas 8-12 (servidor, deploy automático, routines, MCP), y decidir qué hacer con el correo en texto plano.
- **Calidad:** enforzar la CSP, revisar la traducción de los casos de estudio, y valorar el log de uso del modo en vivo.
- **Opcional:** QAP-16, comparativa de modelos.
