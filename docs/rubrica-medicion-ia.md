# Rúbrica para medir la calidad de los demos de IA en vivo (QAP-17)

**Escrita el 2026-10-09 ANTES de cambiar los prompts y de ver ninguna respuesta nueva**, para que los criterios no puedan ajustarse, ni siquiera sin querer, a lo que salga. La medición base (v1) ya existía y se puntuó con esta rúbrica antes de tocar nada.

## Qué se compara y qué se mantiene fijo

| | Línea base (v1) | Corrida nueva (v2) |
|---|---|---|
| Modelo | `openai/gpt-oss-20b` | igual |
| Esfuerzo de razonamiento | `low` | igual |
| Temperatura | 0,3 | igual |
| Las 6 entradas | las de `demo_content.py` (español) | las mismas |
| Prompts del sistema | originales | **mejorados** |
| Limpieza de la salida en código | no existía | **sí** (markdown, guiones y espacios raros) |
| Tope de salida | 1.200 tokens | **1.600 tokens** |

No se toca el modelo ni el esfuerzo de razonamiento. **Son tres cambios, no uno**, y hay que decirlo: los prompts, la limpieza en código y el tope de salida. El tope más alto solo debería afectar a los textos largos (evita cortes), no a la calidad; pero si la corrida nueva mejora, **no se puede atribuir todo a los prompts**. La limpieza en código arregla el formato (negritas y guiones) con independencia del modelo, así que la mejora de formato es mérito de la limpieza, no del prompt.

## Dos tipos de evidencia, y por qué los dos

**Comprobaciones automáticas** (`scripts/score_measure.py`): no dependen de mi juicio. Formato (negritas, guiones no separables), truncado, tokens, segundos, y para los tests de API, **ejecutar el código generado contra la API real**. Las "señales de invención" son búsquedas de texto sobre frases concretas que se sabe que no están en la entrada: son un indicio, no una prueba.

**Puntuación manual** (esta rúbrica): la hago leyendo cada respuesta completa. **Sesgo declarado: soy Claude puntuando a otro modelo, y la rúbrica la escribí yo.** Es subjetiva. Por eso cada punto lleva su justificación de una línea (se puede discutir) y por eso lo automático pesa más como evidencia.

## Criterios (0 o 1 por criterio, máximo 5 por respuesta)

### Casos de prueba (historias de usuario)
- **C1 Cobertura:** incluye todo lo que se deduce de los criterios de aceptación (reserva: teléfono por debajo, en ambos límites y por encima, salida igual o anterior a la entrada, correo inválido, obligatorios vacíos. Login: válido, inválido, vacío, acceso sin sesión, cerrar sesión).
- **C2 No inventa reglas:** ningún límite, regla o resultado esperado que no salga de la historia.
- **C3 No inventa textos:** ni etiquetas de botón ni mensajes literales de la interfaz; los describe de forma genérica.
- **C4 Separa lo no definido:** lo que la historia no define va como pregunta o suposición, **no** como resultado esperado.
- **C5 Formato limpio:** sin markdown, fechas con guiones ASCII, sin cortes.

### Diagnóstico de bugs (trazas)
- **B1 Causa y arreglo principal:** identifica bien la causa y el arreglo principal.
- **B2 Evidencia solo de la traza:** no afirma comportamiento de la aplicación que la traza no muestra.
- **B3 La verificación funciona:** los comandos o pasos de confirmación que propone sirven aun bajo el mismo fallo.
- **B4 Arreglo concreto y primero:** nombra el cambio exacto (flag, opción, ajuste) y lo pone antes que las alternativas.
- **B5 Formato limpio:** sin markdown ni cortes.

### Tests de API (especificación de un endpoint)
- **A1 Pasa contra la API real:** **todos** los tests pasan (resultado ejecutado, no opinión).
- **A2 No asume convenciones:** no afirma estados ni cuerpos que la especificación no dice.
- **A3 Datos únicos y timeouts:** cada test arma su dato único (si crea datos) y toda petición lleva timeout.
- **A4 Verifica el cuerpo:** no se queda solo en el código de estado.
- **A5 Declara lo no verificado:** dice claramente qué supuso y que el código no se ejecutó.

## Puntuación de la línea base (v1), con justificación

| Respuesta | C1/B1/A1 | 2 | 3 | 4 | 5 | Total |
|---|---|---|---|---|---|---|
| Casos / reserva | 1 | 0 | 0 | 0 | 0 | **1** |
| Casos / login | 1 | 0 | 0 | 0 | 0 | **1** |
| Bugs / locator | 1 | 0 | 1 | 1 | 1 | **4** |
| Bugs / allure | 1 | 1 | 0 | 0 | 1 | **3** |
| API / auth | 1 | 0 | 0 | 1 | 1 | **3** |
| API / booking | 0 | 0 | 0 | 1 | 1 | **2** |
| **Total** | | | | | | **14 de 30** |

Justificación punto por punto de lo que NO sumó:
- **Reserva:** C2 inventa una regla de formato de fecha (`Formato de fecha inválido`) que la historia no define; C3 inventa mensajes literales (`El nombre es obligatorio`) y el botón `Confirmar`; C4 pregunta por el formato de fecha pero además lo afirma como caso; C5 trae `**negrita**` y 16 guiones no separables (U+2011) dentro de las fechas.
- **Login:** C2 inventa "usuario de 256 caracteres (máximo permitido)" y "longitud mínima de contraseña", con resultado esperado; C3 inventa `Entrar`; C4 pregunta pero también afirma; C5 trae `**negrita**`.
- **Locator:** B2 afirma que el login fallido "redirige a la página de error", cosa que la aplicación no hace.
- **Allure:** B3 propone confirmar con `pytest --help`, que falla con el mismo error; B4 su primer arreglo es buscar `--alluredir` en `addopts` para quitarlo (no es el problema) y nunca nombra el flag exacto.
- **API / auth:** A2 afirma comportamiento no especificado (campos ausentes, cuerpo vacío, tipo de contenido); A3 no pone timeouts. **A1 sí suma: 6 de 6 pasan.**
- **API / booking:** **A1 no suma: 2 de 5 pasan** (espera 400 y la API da 500; espera 400 con fechas invertidas y la API las acepta; espera JSON en el 404 y no lo hay); A2 es la causa de eso; A3 usa datos fijos (`John Doe`) y no pone timeouts.

## Cómo se interpreta el resultado de la corrida nueva

- Se puntúa con los **mismos criterios, sin cambiarlos**, y se publica la tabla completa, incluidos los criterios en los que no mejore o empeore.
- Con 6 respuestas y un solo muestreo (el modelo no es determinista, aunque la temperatura es baja), **una diferencia de uno o dos puntos no es concluyente**. Lo que sí es sólido: lo medido por ejecución (A1) y lo automático.
- Si una mejora de prompt empeora otra cosa (por ejemplo, menos casos de prueba por ser más cauteloso), también se anota.
