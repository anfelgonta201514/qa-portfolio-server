# Análisis de historias de usuario — portafolio web

> QAP-15 · 2026-10-09. **Estas historias no existían escritas**: las reconstruí a partir de lo que el sitio hace hoy (código, pruebas y tickets de Jira). Los criterios de aceptación son **propuestos**, no requisitos originales: sirven para decidir qué probar y cuándo se da algo por terminado. Probabilidad (P) e impacto (I) en escala baja/media/alta, mi valoración, no un cálculo.

## Mapa de riesgos

| Historia | Riesgo principal | P | I | Cobertura hoy |
|---|---|---|---|---|
| HU-01 Ver el portafolio en mi idioma | Una página existe en un idioma y no en el otro | B | M | Parcial (solo `/demos`) |
| HU-02 Ver el estado real del CI | Mostrar "passing" cuando no lo es | M | **A** | ✅ 13 pruebas |
| HU-03 Revisar los demos de IA | Presentar un ejemplo como si fuera en vivo | B | **A** | ✅ 23 pruebas |
| HU-04 Entrar y salir del panel | Acceso por fuerza bruta | M | **A** | ✅ Límite de intentos y 51 pruebas del panel (QAP-20); cookies pendientes (QAP-21) |
| HU-05 Gestionar los proyectos | Entrada inválida causa error 500 o corrompe datos; escritura sin autorización | M | **A** | ✅ 47 pruebas de la API + validación (QAP-20); falta ejecutar el humo con PostgreSQL |
| HU-06 Desplegar sin miedo | Publicar con pruebas en rojo | **A** | **A** | ❌ (H1) |
| HU-07 Probar un demo en vivo *(QAP-18)* | Abuso de cuota, filtrado de datos, respuestas poco fiables | M | **A** | ✅ Capa de IA (162) + endpoint y formulario con 35 pruebas y 18 más de la configuración de despliegue (QAP-18, apagado hasta poner una clave); falta la verificación con la clave real en producción |

*Estado al 2026-10-09 tras QAP-20:* HU-04 y HU-05 pasaron de cobertura nula a probadas; HU-06 (la puerta de pruebas antes del deploy, QAP-19) sigue pendiente de verificarse en GitHub. Las filas de arriba conservan el análisis original, con la cobertura actualizada.

---

## HU-01 · Ver el portafolio en mi idioma

**Como** reclutador, **quiero** leer el sitio en español o inglés, **para** entenderlo sin traducir.

**Criterios de aceptación (propuestos)**
- Cada página existe en `/ruta` y `/en/ruta` y enlaza a su equivalente.
- Los textos vienen de `content.py`, nunca sueltos en las plantillas.
- Una ruta inexistente responde 404 sin mostrar trazas.

**Tipos de prueba:** humo de cada ruta (ES/EN), enlace entre idiomas, 404, prueba de paridad de claves entre idiomas (parcialmente hecha para los demos).
**Riesgos de diseño:** un texto nuevo agregado solo en un idioma; el caso de estudio de UI es la única página de proyecto (QAP-9 añadirá tres más).
**Definición de hecho:** las 8 rutas responden 200; ninguna clave existe en un idioma y falta en el otro; revisión manual en móvil.

## HU-02 · Ver el estado real del CI

**Como** reclutador, **quiero** que las insignias de cada proyecto reflejen su CI real, **para** no ser engañado.

**Criterios**
- Si GitHub no responde o el dato es viejo (más de 6 horas), muestra "sin datos", **nunca** "passing".
- Una ejecución cancelada no cuenta como fallo; una ejecución fallida sí.
- No frena el render de la página.

**Tipos de prueba:** unitarias de la evaluación de estados, de caché y de fallo de red (**hechas**).
**Riesgos:** un step con `continue-on-error` aparece como "success" y oculta un fallo (H8: aceptado y documentado); límite de 60 peticiones por hora de la API de GitHub sin autenticar (caché de 5 minutos).
**Definición de hecho:** cumplida para lo que cubre; añadir una verificación manual en producción de que el estado real coincide con la pestaña Actions.

## HU-03 · Revisar los demos de IA

**Como** reclutador, **quiero** ver ejemplos de IA aplicada a QA, **para** valorar cómo la usa su dueño, **sabiendo** cuáles son pregenerados.

**Criterios**
- Cada demo declara el modelo que lo generó y que **no** es en vivo.
- No existe un cuadro de texto que sugiera procesamiento en vivo.
- Todo el contenido se escapa (no se inyecta HTML).
- Los ejemplos de API se ejecutaron contra la API real (o lo declaran).

**Tipos de prueba:** contenido, escape de HTML, paridad ES/EN, ejecución de ejemplos (**hechas**, 23 pruebas).
**Riesgos:** que un ejemplo de casos de prueba salga de los criterios y no de la aplicación real (declarado en el README).
**Definición de hecho:** cumplida.

## HU-04 · Entrar y salir del panel

**Como** administrador, **quiero** iniciar y cerrar sesión, **para** editar mi contenido sin que otros puedan.

**Criterios**
- Credenciales válidas llevan al panel; inválidas devuelven 401 con un mensaje que no revela qué campo falló.
- El formulario exige token CSRF.
- Toda ruta de `/admin/` sin sesión redirige al login.
- Tras varios intentos fallidos se frena el acceso *(no existe hoy, H6)*.
- La cookie de sesión es `HttpOnly`, `Secure` y `SameSite=Lax` *(hoy sin los dos últimos, H4)*.

**Tipos de prueba:** integración (login, CSRF, rutas protegidas, logout), seguridad (cookies, límite de intentos).
**Riesgos:** fuerza bruta contra una sola cuenta; cookie enviada por HTTP plano (mitigado por la redirección a HTTPS, pero no impedido).
**Definición de hecho:** TC-ADM-01…04, 07, 08 y TC-SEC-01 en verde; sin hallazgos Altos abiertos.

## HU-05 · Gestionar los proyectos

**Como** administrador, **quiero** crear, editar y borrar proyectos desde el panel o la API, **para** mantener el portafolio al día.

**Criterios**
- Lectura pública; escritura solo con sesión.
- Una petición incompleta o con tipos inválidos recibe 400 con un mensaje, **no** 500 *(hoy 500 con `title` ausente, H2)*.
- Los límites de la base (título de 120 caracteres) se validan antes de llegar a ella *(H5)*.
- Una escritura sin sesión recibe 401, no una redirección HTML *(hoy 302, H3)*.
- La API rechaza cuerpos que no son JSON *(hoy los acepta con cualquier `Content-Type`, H4)*.

**Tipos de prueba:** contrato de la API (códigos y cuerpos), pruebas negativas y de límites, autorización, pasada de humo contra PostgreSQL.
**Riesgos:** exenta de CSRF por diseño (lo justifica el comentario del código, pero depende de `SameSite`); SQLite es más permisivo que producción.
**Definición de hecho:** TC-API-01…10 y TC-ADM-05, 06 en verde; los fixes de H2, H3, H5 desplegados; un `GET` público siempre devuelve datos coherentes tras cualquier escritura.

## HU-06 · Desplegar sin miedo

**Como** dueño, **quiero** que cada cambio se publique solo **si** las pruebas pasan, **para** no romper el sitio sin enterarme.

**Criterios**
- Un push a `main` ejecuta las pruebas primero; si fallan, no se despliega *(no existe hoy, H1)*.
- El despliegue usa una clave dedicada restringida por *forced command* (**hecho**).
- Tras desplegar, un smoke test comprueba el sitio real por HTTPS (**hecho**, 2 de 5 URLs útiles).
- Nunca corren dos despliegues a la vez (**hecho**, `concurrency`).

**Tipos de prueba:** de la propia canalización (un test rojo bloquea; uno verde pasa), humo ampliado, verificación manual de la redirección HTTP → HTTPS.
**Riesgos:** publicar con pruebas en rojo; un smoke test que solo mira 2 URLs puede dar verde con `/admin/login` caído.
**Definición de hecho:** TC-DEP-01 y 02 en verde; un cambio con una prueba rota deliberada **no** se despliega (se prueba una vez en una rama).

## HU-07 · Probar un demo en vivo *(futura, QAP-18)*

**Como** visitante, **quiero** pegar mi propia historia, traza o especificación y recibir un borrador, **para** ver la IA aplicada a mi caso.

**Criterios (a confirmar antes de construir)**
- Etiqueta visible del modelo y advertencia de **"borrador sin verificar"** en cada respuesta.
- Límite por visitante y tope diario; ante cualquier fallo se muestra el ejemplo pregenerado, nunca un error.
- La entrada **no** se registra en el log ni se concatena al prompt del sistema.
- Se usa la IP de `X-Real-IP`, no `X-Forwarded-For`.
- Un solo proceso con hilos en Gunicorn: hoy una llamada lenta bloquearía todo el sitio.

**Tipos de prueba:** las 162 de la capa; pendientes: endpoint, formulario, advertencia visible, concurrencia con el servidor real, verificación en producción con una clave **de servidor distinta** de la de pruebas.
**Riesgos:** agotar la cuota gratuita; respuestas poco fiables (la medición mostró que en este modelo el razonamiento no mejora con prompts); abuso desde un solo origen.
**Definición de hecho:** todo lo anterior, más una prueba de que con el proveedor caído el sitio sigue respondiendo con los ejemplos.

---

## Qué recomiendo probar primero

1. **HU-06** — es lo de mayor impacto y de menor costo, y protege todo lo demás.
2. **HU-05 y HU-04** — son los únicos puntos de escritura y de acceso, y hoy no tienen pruebas.
3. **HU-07** — solo cuando se decida activarla, y con sus criterios confirmados.
