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

1. **Si pide tarjeta de crédito para el plan gratis.** Ninguna página consultada lo dice. Se sabrá al crear la cuenta.
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

## Capacidad estimada con el plan gratis de Groq (estimación, no medición)

El límite que manda no es el de peticiones, sino el de **tokens por día: 200.000**.

- Una llamada típica consume entrada (hasta ~4.000 caracteres ≈ 1.000-1.300 tokens, más el prompt del sistema) y salida (hasta 1.200 tokens): del orden de **2.500 tokens** en el peor caso razonable → **~80 llamadas al día**. Si el modelo gasta tokens razonando, serían menos.
- El límite de **8.000 tokens por minuto** permite **~3 llamadas por minuto** entre todos los visitantes. Un pico de visitas simultáneas recibiría 429, y la capa ya responde con el ejemplo pregenerado.
- Por eso el tope diario por defecto de la capa (`AI_DAILY_CAP=100`) es **demasiado alto** para este plan: conviene empezar en **60** y ajustar con el consumo real que registre la respuesta del proveedor.

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
