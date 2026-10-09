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

## Resultados v2 (corrida del 2026-10-09, `results-v2-20261009-150750.json`)

Mismos criterios, mismo modelo, mismas 6 entradas. **Tres cambios a la vez** (prompts + limpieza en código + tope de salida de 1.200 a 1.600 tokens), así que no se puede atribuir la mejora a uno solo. Un solo muestreo de 6 respuestas: **una diferencia de uno o dos puntos no es concluyente**.

### Comprobaciones automáticas (`scripts/score_measure.py`)

| Medida | v1 | v2 |
|---|---|---|
| Negritas de markdown | 8 | 0 |
| Guiones no separables (U+2011) | 16 | 0 |
| Señales de invención (búsqueda de texto) | 10 | 3 |
| Tests de API contra la API real | 8 pasan, 3 fallan | 4 pasan, 0 fallan |
| Respuestas cortadas por el tope | 0 | **1** (API / booking, 1.600 de 1.600) |
| Tokens totales | 6.616 | 7.842 (+19 %) |

### Puntuación manual

| Respuesta | 1 | 2 | 3 | 4 | 5 | v1 | **v2** |
|---|---|---|---|---|---|---|---|
| Casos / reserva | 1 | 0 | 1 | 0 | 1 | 1 | **3** |
| Casos / login | 1 | 0 | 1 | 0 | 1 | 1 | **3** |
| Bugs / locator | 0 | 0 | 1 | 1 | 1 | 4 | **3** |
| Bugs / allure | 1 | 1 | 0 | 0 | 1 | 3 | **3** |
| API / auth | 1 | 1 | 1 | 1 | 1 | 3 | **5** |
| API / booking | 1 | 1 | 1 | 1 | 0 | 2 | **4** |
| **Total** | | | | | | **14** | **21 de 30** |

Justificación de lo que NO suma (y de lo que empeoró):
- **Reserva:** C2 el TC12 espera confirmación con entrada "hoy" y el TC09 un mensaje de "teléfono obligatorio", cosas que la historia no define; C4 el TC02 afirma que salida igual a entrada da error y a la vez lo pregunta en "Assumptions to confirm" (el mismo defecto que en v1). Cobertura (C1) justa: solo prueba salida *igual*, no *anterior*, y no prueba los valores válidos 11 y 21.
- **Login:** C2 los TC05 y TC06 esperan un mensaje de "campo obligatorio" que la historia no define; C4 afirma ese resultado sin preguntarlo (los casos de acceso sin sesión sí van con "o" y con pregunta).
- **Locator (EMPEORÓ, 4 → 3):** B1 ahora dice "Falta de elemento en la UI (producto)", cuando lo razonable es que el test es el equivocado (se llama "wrong_password"). B2 inventa que existe un mensaje "Contraseña incorrecta" (la app muestra "Invalid credentials"). Sí sube la sugerencia de `get_by_role("alert")`.
- **Allure:** B3 propone confirmar con `pytest --help | grep alluredir`, que falla con el mismo error (igual que en v1); B4 no nombra el flag exacto (`-p no:allure_pytest_bdd`) y su primer paso es buscar otro plugin.
- **API / booking:** A5 no suma porque la lista de "Unverified assumptions" degenera en un **bucle de repetición** (decenas de líneas "The API does not return any unexpected compatibility with…") y se corta en el tope; además afirma que "la API no requiere timeout" justo después de poner `timeout=5`. El aviso de "NOT EXECUTED" sí está.

### Lectura honesta

- **Mejoró de forma sólida (automático):** el formato (0 negritas, 0 guiones raros: mérito de la **limpieza en código**, no del prompt) y que **todo el código de API generado pasa** contra la API real, con datos únicos, timeouts y aviso de "no ejecutado".
- **Sin mejora donde más cuesta:** C2 y C4 (no inventar reglas y separar lo no definido) siguen en 0 en las dos historias de usuario. Las 10 → 3 "señales de invención" miden solo las frases concretas de v1; en v2 aparecen otras invenciones que esas búsquedas no cubren.
- **Empeoró o apareció de nuevo:**
  1. El diagnóstico del locator (B1/B2).
  2. **Una respuesta cortada en bucle** al subir el tope: tokens de más sin valor y un fallo que no existía en v1.
  3. **Menos tests de API:** auth pasó de 6 a 2 (todos pasan, pero cubre menos; la rúbrica no mide cobertura en API, así que esto no se ve en los puntos).
  4. **Encabezados en inglés** ("Test Cases", "Assumptions to confirm", "Steps", "Expected Result") en respuestas a entradas en español: la rúbrica no lo puntúa, pero un visitante lo notaría.
- **Conclusión:** 14 → 21 es una mejora real pero **moderada y desigual**, y buena parte (formato, A1) viene de la limpieza y de pedir solo dos tests, no de que el modelo "razone" mejor. Sesgo declarado: puntúa Claude, el mismo que escribió la rúbrica.

## Resultados v3 (corrida del 2026-10-09, `results-v3-20261009-152435.json`)

Mismos criterios, modelo y entradas. **Único cambio respecto a la v2:** tres reglas nuevas en los prompts (encabezados traducidos al idioma de salida; comprobar el test antes de culpar al producto y no citar textos que la traza no tenga; lista de supuestos de la API limitada a 6 líneas sin repetir). **Aviso de método:** esas reglas las escribí *después* de ver las respuestas de la v2, y la del diagnóstico de bugs nace de un fallo concreto de la v2 (el ejemplo del locator). La redacté en general, pero esa respuesta ya no es una medición "ciega".

### Comprobaciones automáticas (v2 → v3)

| Medida | v2 | v3 |
|---|---|---|
| Negritas / guiones no separables | 0 / 0 | 0 / 0 |
| Señales de invención (búsqueda de texto) | 3 | 4 |
| Tests de API contra la API real | 4 pasan, 0 fallan | 4 pasan, 0 fallan |
| Respuestas cortadas por el tope | 1 | **0** |
| Tokens totales | 7.842 | 7.344 (-6 %) |

### Puntuación manual

| Respuesta | 1 | 2 | 3 | 4 | 5 | v1 | v2 | **v3** |
|---|---|---|---|---|---|---|---|---|
| Casos / reserva | 1 | 0 | 1 | 1 | 1 | 1 | 3 | **4** |
| Casos / login | 1 | 0 | 1 | 0 | 1 | 1 | 3 | **3** |
| Bugs / locator | 0 | 0 | 1 | 1 | 0 | 4 | 3 | **2** |
| Bugs / allure | 1 | 1 | 0 | 0 | 0 | 3 | 3 | **2** |
| API / auth | 1 | 1 | 1 | 1 | 1 | 3 | 5 | **5** |
| API / booking | 1 | 1 | 1 | 1 | 1 | 2 | 4 | **5** |
| **Total** | | | | | | **14** | **21** | **21 de 30** |

Qué NO suma:
- **Reserva:** C2 el TN003 espera error para un correo "sin punto después del @", un límite del formato que la historia no define. Pero esta vez las preguntas van como preguntas y no se contradicen con ningún caso (C4 sube a 1).
- **Login:** C2 y C4 los TC005 y TC006 (longitud mínima y máxima del usuario "si aplica") son exactamente el tipo de invención de la v1: se escriben como casos con resultado esperado y además se preguntan en "Supuestos".
- **Locator:** B1 **sigue culpando al producto** ("el fallo parece provenir del producto") a pesar de la regla nueva; la alternativa correcta (el test espera algo que un login fallido no muestra) aparece como segunda opción condicionada. B2 repite "la página de error de login", una página que nada indica. B5 trae un bloque de código con triple acento grave.
- **Allure:** B3 vuelve a proponer `pytest --help | grep alluredir`; B4 no nombra el flag exacto y sugiere un parche en `conftest.py` que no resuelve el problema; B5 trae bloques con triple acento grave.

### Lectura honesta

- **Funcionó (2 de las 3 reglas):**
  1. *Idioma:* los encabezados salen en español ("Supuestos a confirmar", "Preguntas que deja la historia sin responder"; hay una errata del modelo, "Asumciones").
  2. *Bucle de supuestos:* API / booking pasó de 1.600 tokens cortados en repetición a 657 tokens con 6 supuestos sobrios. Sube de 4 a 5.
- **No funcionó (1 de 3):** el diagnóstico del locator. La regla está en el prompt (hay una prueba que lo verifica) y el modelo no la sigue. Con `gpt-oss-20b` en esfuerzo `low`, una instrucción de este tipo no basta.
- **El total no cambió: 21 → 21.** Lo que sube (reserva, booking) lo compensa lo que baja (locator, allure). Con un solo muestreo y 6 respuestas, **esto es ruido**: C2 y C4 de los casos de prueba cambian de una corrida a otra sin que cambie el prompt que las gobierna. No se puede afirmar que la v3 sea mejor que la v2, solo que arregló dos defectos concretos y observables.
- **Hallazgo nuevo:** `clean_output` quita `**` y `#` pero **no los bloques de código con triple acento grave** en las respuestas de prosa (bugs). El prompt los prohíbe y el modelo los usa igual. Es un arreglo determinista en código (no depende del modelo) que no se ha hecho.
- **Evolución global:** v1 14 → v2 21 → v3 21. La mejora sólida y repetible viene de lo que se arregla **en código** (formato) y de pedir poco (tests de API cortos y ejecutables). Lo que depende de que el modelo razone bien (no inventar reglas, diagnosticar causa y arreglo) **no mejora de forma fiable con prompts** en este modelo.
- **Implicación para QAP-18:** el modo en vivo debe seguir mostrando la advertencia de "borrador sin verificar" y la etiqueta del modelo; no hay base para afirmar que los diagnósticos o los casos de prueba sean fiables.

### Seguimiento: limpieza de acentos graves y cercos de código (hecha tras la v3)

`clean_output` ahora quita, **solo en las respuestas de prosa** (casos de prueba y bugs), las líneas de cerco ``` y los acentos graves sueltos, conservando el contenido y su sangría; en los tests de API no toca nada. Se comprobó con 4 pruebas nuevas, con una prueba de mutación (sin las dos líneas nuevas fallan 3 pruebas) y sobre las respuestas reales de la v3: 8 y 38 acentos graves antes, 0 después.

**No se re-puntúa la v3:** la tabla de arriba se queda como se midió. Pero la parte de formato (B5) de las dos respuestas de bugs, que perdió el punto por esos bloques, **habría sumado con esta limpieza** (21 → 23 con la misma lectura). Es mérito del código, no del modelo, y no cambia que el diagnóstico (B1, B3, B4) siga sin mejorar.
