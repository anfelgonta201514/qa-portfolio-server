# Reporte QE — Semana 12 (2026-10-06)

> Generado con Claude a partir de los tickets reales del proyecto Jira **QA Portfolio (QAP)**, leídos por el conector oficial de Atlassian. Las cifras salen de la consulta `project = QAP`, no de memoria.

## Resumen ejecutivo

El proyecto tiene **10 tickets**: **4 terminados (40 %)**, 2 en curso (uno en desarrollo, otro en revisión) y 4 por empezar. Todo lo terminado es infraestructura y automatización de las semanas 10-11 (deploy automático, dos routines de CI, rediseño del sitio). Lo pendiente se concentra en **calidad del contenido del sitio** y en **cerrar la deuda de la suite de tests**.

## Avance por estado

| Estado | Tickets | Qué hay |
|---|---|---|
| Done | 4 | QAP-2 deploy automático · QAP-3 review de PRs · QAP-4 routine nocturna de CI · QAP-5 rediseño del sitio |
| In Progress | 1 | QAP-6 este reporte |
| In Review | 1 | QAP-1 Bug de prueba del flujo falla → Jira → Slack |
| To Do | 4 | QAP-7 reforzar test negativo · QAP-8 badges de CI · QAP-9 casos de estudio · QAP-10 logs del servidor |

## Por tipo y prioridad

| Tipo | Cantidad | | Prioridad | Cantidad |
|---|---|---|---|---|
| Story | 5 | | High | 2 |
| Task | 3 | | Medium | 8 |
| Bug | 2 | | | |

## Hallazgos de calidad

1. **El test negativo de login (QAP-7) tiene una premisa desactualizada.** La suite documenta que la app no muestra ningún error ante credenciales inválidas, pero el aria snapshot de una falla real mostró `alert: Invalid credentials`. Es un hallazgo de la propia automatización: la verificación original o el comportamiento de la app cambió.
2. **El sitio puede mostrar información falsa (QAP-8).** Los badges "passing" de los 4 proyectos son texto fijo; si el CI se pone rojo, el portafolio seguiría diciendo "passing".
3. **El flujo de aviso funciona de punta a punta.** Una falla de Playwright se analizó, creó un Bug en Jira (QAP-1) y avisó a `#ci-alerts`. El análisis separó correctamente "suposición incorrecta del test" de "bug de la app".

## Riesgos

| Riesgo | Impacto | Mitigación propuesta |
|---|---|---|
| Badges de CI estáticos (QAP-8) | Credibilidad del portafolio ante un revisor | Leer el estado real por la API de GitHub, con caché |
| Review de PRs depende de un cron, no de un webhook | Hasta ~1 h de demora en recibir el comentario | Aceptado; el webhook nunca disparó (límite de plataforma) |
| Acceso a logs del servidor sin definir (QAP-10) | Una credencial de escritura podría llegar a un agente | Clave aparte, solo lectura, con forced command |
| Casos de estudio incompletos (QAP-9) | 3 de 4 proyectos sin detalle | Semana 13, con ayuda de Claude |

## Siguientes pasos

1. Cerrar QAP-6 tras revisar este reporte.
2. QAP-10: definir el acceso de solo lectura a los logs del servidor (pieza restante de la semana 12).
3. QAP-7 y QAP-8: pequeños, de alto valor, listos para tomar.
4. QAP-9: semana 13.

## Limitaciones de este reporte (importante)

- **No hay sprint:** el tablero es Kanban (`type: simple`) y no admite sprints, así que no hay velocidad ni burndown. El reporte usa una ventana de tiempo, no un sprint.
- **Las fechas no sirven para medir ritmo:** los 10 tickets se crearon el mismo día (2026-10-06). Los 4 "Done" representan trabajo hecho en semanas anteriores, registrado hoy. Por eso **no se calculan tiempos de ciclo ni rendimiento** y el 40 % de avance describe el estado del tablero, no una velocidad medida.
- Con tickets creados a lo largo de varias semanas, este mismo reporte pasaría a incluir tiempos de ciclo y tendencia.
