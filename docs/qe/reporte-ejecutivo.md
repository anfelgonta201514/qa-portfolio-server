# Reporte ejecutivo de calidad — portafolio web

> QAP-15 · 2026-10-09 · Para lectores no técnicos. Las cifras salen de ejecutar las pruebas, consultar Jira y abrir el sitio hoy; nada está tomado de memoria. El detalle técnico está en la [estrategia](estrategia-de-pruebas.md) y el [plan de pruebas](plan-de-pruebas.md).

> **Actualización (QAP-19 y QAP-20, mismo día):** se añadió la puerta de pruebas antes de publicar (pendiente de verificarse en GitHub) y se probaron y corrigieron la interfaz de edición y el acceso al panel (98 pruebas nuevas, límite de intentos de acceso). Las cifras de abajo son las del análisis original; quedan por confirmar en producción tras el próximo despliegue.

## En una frase

**El sitio funciona y lo nuevo está bien protegido, pero hay una brecha importante: nada impide publicar un cambio que rompa las pruebas, y la parte que permite editar el contenido no tiene ninguna prueba automática.**

**Semáforo: ámbar.** Ningún problema es visible para un visitante hoy; los riesgos son de "qué pasa el día que algo falle".

## Estado de un vistazo

| | Hoy | Comentario |
|---|---|---|
| Sitio público (`andresqe.duckdns.org`) | 🟢 Responde | 5 páginas revisadas hoy, todas correctas, en menos de un segundo (una sola medición por página) |
| Pruebas automáticas | 🟢 225 en total: 222 pasan, 3 omitidas a propósito, 0 fallan | Las omitidas gastan cuota de servicios externos y se activan a mano |
| Honestidad del contenido | 🟢 | Las insignias del CI muestran el estado real; los demos de IA dicen que no son en vivo |
| Protección de la edición del contenido | 🟡 | Funciona, pero sin pruebas automáticas y con puntos débiles (ver abajo) |
| Control antes de publicar | 🔴 | Hoy se publica sin ejecutar las pruebas |
| Proyecto (Jira) | 🟢 | 18 tareas: 10 terminadas, 4 en revisión, 1 en curso, 3 por empezar |

## Qué significa para el negocio

El sitio es la carta de presentación profesional de su dueño. Lo que más pesa no es que "se caiga", sino que **muestre algo falso o que alguien ajeno cambie su contenido**. Esto ya se corrigió una vez (las insignias eran texto fijo) y hoy refleja el estado real.

## Los tres riesgos principales

1. **Se puede publicar un error sin que nadie se entere** *(alto)*. El proceso que publica el sitio no ejecuta las 225 pruebas primero. Hoy depende de que quien publica se acuerde de correrlas. *Remedio:* hacer que la publicación espere a las pruebas (1-2 horas de trabajo).
2. **El formulario y la interfaz de edición no tienen pruebas** *(medio)*. Al explorarlos encontré que una petición incompleta a la interfaz de programación produce un error interno en vez de un mensaje claro, y que no hay límite de intentos de acceso. No encontré un fallo que abra el sitio a terceros, pero tampoco hay una red de seguridad si un cambio futuro lo hiciera. *Remedio:* pruebas y correcciones (6 a 8 horas).
3. **Faltan protecciones estándar del navegador** *(medio)*. El sitio no envía varias cabeceras de seguridad habituales y las cookies de sesión no declaran todas sus restricciones. Es una práctica recomendada, no una vulnerabilidad demostrada. *Remedio:* 2 a 3 horas.

## Qué no sabemos

- Cómo se comporta con **muchos visitantes a la vez**: no se probó, a propósito, para no arriesgar el servidor.
- Si dos problemas del formulario también ocurren en la **base de datos real** (la exploración usó una base más permisiva): quedan marcados para confirmar.
- La **calidad del modo en vivo de IA** no se puede afirmar todavía: está apagado, y la medición mostró mejoras sólidas en el formato, pero no una mejora fiable en el razonamiento (ver `docs/rubrica-medicion-ia.md`).

## Qué se necesita decidir

| Decisión | Recomendación |
|---|---|
| ¿Bloquear la publicación si las pruebas fallan? | **Sí**, es lo de mayor valor y menor costo |
| ¿Invertir ~21-31 horas en cerrar la brecha completa? | Hacer solo las dos primeras etapas (~10 a 14 horas); el resto cuando se active el modo en vivo |
| ¿Activar ya el modo en vivo de IA? | **No** hasta tener la advertencia de "borrador sin verificar" y la puerta de pruebas |

## Cómo se obtuvieron estas cifras

Pruebas ejecutadas en un entorno limpio con las dependencias del proyecto; consulta de Jira (proyecto QAP) por el conector oficial; revisión del sitio con peticiones reales a producción, solo de lectura. **Las horas son estimaciones**, no mediciones.
