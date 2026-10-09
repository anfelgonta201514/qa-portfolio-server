// Confirmación antes de enviar un formulario que lleve data-confirm="mensaje" (hoy: borrar un proyecto).
//
// Antes era un atributo onsubmit="return confirm('¿Borrar {{ título }}?')": (1) una Content-Security-Policy sin
// 'unsafe-inline' lo bloquea, y entonces el formulario se enviaba SIN pedir confirmación; (2) el título del proyecto
// quedaba dentro de una cadena de JavaScript, así que un título con una comilla simple podía salirse de ella.
// Con data-confirm el texto es solo un atributo HTML (escapado por Jinja) y el código no cambia con el contenido (QAP-21).
document.addEventListener("submit", function (event) {
  var message = event.target.dataset && event.target.dataset.confirm;
  if (message && !window.confirm(message)) {
    event.preventDefault();
  }
});
