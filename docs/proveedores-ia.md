# Elección del primer proveedor de IA en vivo (QAP-14)

**Leído el 2026-10-07 en páginas oficiales** (no en blogs). Los datos se extrajeron con una herramienta que lee y resume la página, así que **hay que confirmar a ojo los tres datos críticos** (tabla de límites, tarjeta de crédito y control de datos) al crear la cuenta. Los límites de los planes gratis cambian: cada afirmación de abajo vale "a esta fecha".

## Por qué importa tanto el uso de datos

Los visitantes del sitio podrían pegar un stack trace o una historia de usuario con datos reales. Si el plan gratis del proveedor usa esa entrada para mejorar sus modelos, o personas la leen, publicar el demo en vivo sería irresponsable con quien lo use.

## Comparativa

| | **Groq** | **Gemini API (Google)** | **OpenRouter** |
|---|---|---|---|
| Plan gratis | Sí ("Free Plan Limits") | Sí, en la mayoría de modelos Flash/Flash-Lite y 2.5 | Sí, modelos `:free` |
| Pide tarjeta | **La página no lo dice** | **La página no lo dice** | **La página no lo dice** |
| Límites gratis (oficiales) | `gpt-oss-120b`, `gpt-oss-20b` y `qwen3.8-27b`: **30 RPM, 1.000 RPD, 8.000 TPM, 200.000 TPD** | **No figuran en la página**: se ven en el panel de Google AI Studio; "no están garantizados" | **20 RPM y 50 RPD** con menos de USD 10 comprados; 1.000 RPD si se compraron ≥ USD 10 |
| Al pasarse del límite | HTTP 429 con cabecera `retry-after` | (no especificado en lo leído) | HTTP 429; con saldo negativo, 402 incluso en modelos gratis |
| Reinicio diario | No lo dice la página | A medianoche, hora del Pacífico | No lo dice |
| **¿Usa tus datos para entrenar?** | El **Acuerdo de Servicios** dice que Groq **no puede** usar Entradas ni Salidas para entrenar ni afinar modelos salvo permiso explícito del cliente | **Plan gratis: SÍ** ("Used to improve our products: Yes"); **personas pueden leer** entradas y salidas. Plan de pago: no | **No lo dice** para los modelos gratis. Hay un ajuste de cuenta para excluir proveedores que entrenan, pero no se sabe cuánto reduce los modelos gratis disponibles |
| Retención de datos | Por defecto **no retiene** los datos de inferencia (hasta 30 días solo para resolver incidencias o abuso). Se puede activar retención cero | Plan gratis: se usan para mejorar productos | No lo dice la política de OpenRouter en lo leído |
| Advertencia expresa | — | **"No envíes información sensible, confidencial o personal al servicio gratuito"** | — |
| Edad mínima | No lo dice | 18 años | No lo dice |

## Veredicto

- **Groq: es el único de los tres cuya documentación oficial respalda enviar texto escrito por visitantes.** Contrato que prohíbe entrenar con los datos, sin retención por defecto, y límites claros.
- **Gemini plan gratis: descartado para entradas de visitantes.** Sus propios términos dicen que se usa para mejorar productos, que personas pueden leerlo y que no se envíen datos sensibles. Sí es utilizable para tareas donde **las entradas las pongo yo y son públicas** (por ejemplo, la comparativa de modelos de QAP-16).
- **OpenRouter: descartado como primera opción.** Con 50 peticiones al día se agota con muy pocas visitas, subir a 1.000 exige comprar crédito, y no queda claro qué hacen con los datos los proveedores de los modelos gratis.

## Lo que NO está confirmado de Groq

1. ~~Si pide tarjeta de crédito para el plan gratis.~~ **Confirmado por Andres el 2026-10-09: no la pidió** al crear la cuenta (aunque ninguna página oficial lo decía).
2. **Si el Acuerdo de Servicios obliga igual a quienes usan el plan gratis.** La página no distingue planes.
3. **A qué hora se reinicia el tope diario.**
4. **Calidad real de los modelos** (`gpt-oss`, `qwen`) en estas tres tareas: hay que probarlo antes de activar. Son modelos abiertos; no tienen por qué igualar la calidad de los ejemplos pregenerados.
5. **Si los modelos razonan** y cuántos tokens extra gastan por llamada: afecta directamente al tope diario.
6. La política de privacidad de Groq **excluye** el contenido de la API ("Customer Data") y lo remite al Acuerdo de Servicios y al Anexo de Procesamiento de Datos; el Anexo no se leyó.

## Decisión

**Andres eligió Groq como primer proveedor en vivo (2026-10-07).** Gemini queda reservado, si acaso, para tareas donde las entradas son públicas y las pongo yo (comparativa de modelos, QAP-16).

## Cómo se integra Groq (documentación oficial, leída el 2026-10-07)

| Aspecto | Qué dice la documentación |
|---|---|
| Endpoint | `POST https://api.groq.com/openai/v1/chat/completions` |
| Autenticación | `Authorization: Bearer <clave>` |
| Tope de salida | `max_completion_tokens` (`max_tokens` está **obsoleto**) |
| Texto de la respuesta | `choices[0].message.content` |
| Tokens usados | `usage.prompt_tokens`, `usage.completion_tokens`, `usage.total_tokens` |
| Cuota agotada | HTTP `429` con cabecera `retry-after` |
| Otros errores | `400/401/403/404/413/422/424/498/499` y `500/502/503`; cuerpo `{"error": {"message", "type"}}` |
| Modelos `gpt-oss-20b` / `120b` | **Razonan.** `reasoning_effort`: `low`, `medium` (por defecto) o `high`. `include_reasoning` (por defecto `true`) devuelve el razonamiento en `message.reasoning` |
| Razonamiento y tope | La página **no dice** si los tokens de razonamiento cuentan contra el tope de salida, y advierte que el valor por defecto "puede ser bajo" para razonamientos largos |

`GroqProvider` pide `reasoning_effort: low` e `include_reasoning: false` para los modelos `openai/gpt-oss-*` (para no gastar tokens ni ancho de banda en un razonamiento que no se muestra). **No se probó contra el servicio real**: si el razonamiento consume el tope, `content` llegaría vacío y la capa respondería con el ejemplo pregenerado.

## Hallazgo de la primera llamada real (2026-10-09): 403 de Cloudflare

La primera prueba contra Groq con una clave real devolvió **HTTP 403**. La documentación dice que un 403 significa "permisos insuficientes", pero **la clave no tenía nada que ver**: Groq está detrás de Cloudflare, que bloquea con un 403 (`error code: 1010`) las peticiones que se anuncian con el `User-Agent` por defecto de la librería estándar de Python (`Python-urllib/3.x`), **antes de mirar la clave**.

Se comprobó sin usar la clave real, enviando una clave falsa de dos formas: sin `User-Agent` propio → 403 `error code: 1010`; con uno propio → 401 `Invalid API Key` (el servidor sí llegó a evaluar la clave). Corregido enviando `User-Agent: qa-portfolio-server/1.0`.

**Qué enseña:** 112 pruebas de la capa pasaban en verde y el código no funcionaba con el servicio real. Las pruebas con respuestas simuladas escritas desde la documentación solo pueden comprobar lo que la documentación dice; este requisito (Cloudflare) no está en ella. Por eso la prueba `groq_live` existe y por eso se declaró desde el principio que lo simulado no equivale a lo real.

**Segunda lección:** la decisión de no propagar nunca el cuerpo del error (para no filtrar lo que escribió el visitante) **tapó la causa**: el mensaje solo decía "HTTP 403". Ahora el error conserva solo diagnósticos inofensivos: el `code` y el `type` de Groq si son identificadores cortos (p. ej. `invalid_api_key`) o el código de bloqueo de Cloudflare (`cloudflare 1010`); el texto libre del `message` sigue sin propagarse jamás.

## Medición real con las entradas de los demos (2026-10-09)

Se pasaron las 6 entradas reales de los demos (en español) por el servicio real, con los prompts, el tope de salida (1.200) y el timeout de producción, usando `openai/gpt-oss-20b` en el plan gratis. La respuesta completa de cada una quedó en `.groq-measure/results.json`, que Git ignora.

| Demo / ejemplo | Segundos | Tokens entrada | Tokens salida |
|---|---|---|---|
| Casos de prueba / reserva | 1,72 | 308 | **1.181** |
| Casos de prueba / login | 1,55 | 298 | 916 |
| Bugs / locator | 0,74 | 331 | 417 |
| Bugs / allure | 1,03 | 359 | 387 |
| Tests de API / auth | 1,19 | 274 | 751 |
| Tests de API / booking | 1,54 | 318 | 1.076 |

**6 de 6 respuestas en vivo, ninguna vacía ni en respaldo.** Latencia de 0,74 a 1,72 s. Promedio por llamada: 315 tokens de entrada y 788 de salida (**1.103 en total**); el máximo medido fue 1.489. Esto confirma que el razonamiento cuenta dentro de los tokens de salida (la primera prueba pequeña ya lo sugería) y que con esfuerzo `low` es poco.

**Capacidad con datos reales:** al promedio medido caben **~180 llamadas al día** de las 200.000 tokens; con el máximo medido, ~134. Pero las entradas de estos ejemplos son cortas (274-359 tokens contando el prompt del sistema). Con la entrada máxima permitida (4.000 caracteres, ~1.100 tokens) y la salida máxima, el peor caso es ~2.450 tokens: ~80 al día. **El tope diario debe fijarse sobre el peor caso, no sobre el promedio.**

**Riesgo de truncado:** una respuesta usó **1.181 de los 1.200 tokens** permitidos. Con una historia más larga la respuesta se cortaría a media frase o a media línea de código, y hoy el servicio no lo detecta (no se lee `finish_reason`).

### Calidad: leí las 6 respuestas completas

**Lo que hace bien:** estructura útil y en español correcto, cobertura de casos amplia (12 casos para la reserva, con los valores límite de 10/11/21/22 caracteres del teléfono, que es lo importante), preguntas de aclaración pertinentes, y para tests de API reconoce que "200 con credenciales inválidas" es un comportamiento inusual y lo prueba por el cuerpo.

**Lo que hace mal, y es el hallazgo principal: inventa lo que la entrada no dice y lo presenta como si lo dijera.**
- *Casos de prueba, login:* añade "longitud máxima de usuario: 256 caracteres (máximo permitido)" y "longitud mínima de contraseña" con resultado esperado concreto. **La historia no define ninguno de esos límites.** Además inventa textos de interfaz ("Entrar", "Cerrar sesión") y mensajes de error literales.
- *Bugs, locator:* acierta que el error está en el test, pero afirma que un login fallido "redirige a la página de error", cosa que la app no hace.
- *Bugs, Allure:* acierta la causa de fondo, pero su primer paso es buscar `--alluredir` en `addopts` para borrarlo (no es el problema) y recomienda confirmar con `pytest --help`, **un comando que fallaría con el mismo error**, porque pytest revienta antes de llegar a la ayuda. Tampoco llega a nombrar la solución que usamos (`-p no:allure_pytest_bdd`).
- *Tests de API:* **el código generado se ejecutó contra la API real**.
  - `POST /auth`: **6 de 6 pasan**, porque la especificación ya avisaba del comportamiento raro.
  - `POST /booking`: **3 de 5 fallan**, por asumir convenciones REST que esta API no cumple: espera 400 y la API devuelve **500** si falta un campo, espera 400 con fechas invertidas y la API las **acepta** (200), y espera un cuerpo JSON en el 404 y no lo hay. Es exactamente la trampa que advierte el `CLAUDE.md` de `qa-automation-portfolio`: no asumir el comportamiento "correcto" sin verificarlo. El modelo dejó un comentario de ambigüedades que cubre parte de esto, pero aun así afirmó el 400 sin avisar. Además usó datos fijos ("John Doe"), no únicos.

**Defectos de formato:** los casos de prueba traen markdown (`**negrita**`) aunque el prompt pedía texto plano, y el ejemplo de la reserva trae **16 guiones no separables (U+2011) dentro de las fechas** (`2026‑10‑15`): copiadas a un test no son fechas válidas.

### Conclusión

`gpt-oss-20b` en el plan gratis es **rápido, fiable y útil como borrador**, pero **no se debe presentar como un resultado verificado**. La diferencia con los ejemplos pregenerados es concreta y medible: aquellos se revisaron y el código de API se ejecutó contra la API real antes de publicarlo; esto no. Eso es justo lo que el sitio debe decir en el modo en vivo.

## Capacidad estimada con el plan gratis de Groq (estimación previa a la medición)

El límite que manda no es el de peticiones, sino el de **tokens por día: 200.000**.

- Una llamada típica consume entrada (hasta ~4.000 caracteres ≈ 1.000-1.300 tokens, más el prompt del sistema) y salida (hasta 1.200 tokens): del orden de **2.500 tokens** en el peor caso razonable → **~80 llamadas al día**. Si el modelo gasta tokens razonando, serían menos.
- El límite de **8.000 tokens por minuto** permite **~3 llamadas por minuto** entre todos los visitantes. Un pico de visitas simultáneas recibiría 429, y la capa ya responde con el ejemplo pregenerado.
- **Actualización tras la medición real** (ver arriba): el promedio resultó ser 1.103 tokens por llamada, menos que esta estimación; este cálculo sigue valiendo como **peor caso**. Con `AI_MAX_OUTPUT_TOKENS=1600` el peor caso es ~2.900 tokens por llamada: **`AI_DAILY_CAP=70`**.

## Fuentes (todas oficiales)

- Groq, límites: https://console.groq.com/docs/rate-limits
- Groq, datos: https://console.groq.com/docs/your-data
- Groq, política de uso aceptable: https://console.groq.com/docs/legal/ai-policy
- Groq, política de privacidad: https://groq.com/privacy-policy
- Groq, Acuerdo de Servicios: https://console.groq.com/docs/legal/services-agreement
- Gemini, precios: https://ai.google.dev/gemini-api/docs/pricing
- Gemini, límites: https://ai.google.dev/gemini-api/docs/rate-limits
- Gemini, términos: https://ai.google.dev/gemini-api/terms
- OpenRouter, límites: https://openrouter.ai/docs/api-reference/limits
- OpenRouter, registro de peticiones: https://openrouter.ai/docs/guides/privacy/logging

La página de precios de Groq (`groq.com/pricing`) devolvió la portada, no los precios: **no se consultó**.
