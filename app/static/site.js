// Los enlaces "Escríbeme" son mailto: normales (funcionan sin JS); con JS
// abren un diálogo para elegir Gmail, Outlook, la app de correo o copiar.
//
// Vive en un archivo propio (y no en un <script> dentro de layout.html) para que la
// Content-Security-Policy pueda exigir `script-src 'self'` sin 'unsafe-inline' (QAP-21).
(function () {
  var dialog = document.getElementById("email-dialog");
  if (!dialog || typeof dialog.showModal !== "function") return;
  document.querySelectorAll("[data-email-dialog]").forEach(function (link) {
    link.addEventListener("click", function (event) {
      event.preventDefault();
      dialog.showModal();
    });
  });
  dialog.querySelector("[data-close]").addEventListener("click", function () { dialog.close(); });
  dialog.addEventListener("click", function (event) { if (event.target === dialog) dialog.close(); });
  var copyBtn = dialog.querySelector("[data-copy]");
  copyBtn.addEventListener("click", function () {
    var label = copyBtn.querySelector("span"), original = label.textContent;
    navigator.clipboard.writeText(copyBtn.dataset.copy).then(function () {
      label.textContent = copyBtn.dataset.copied;
      setTimeout(function () { label.textContent = original; }, 2000);
    });
  });
})();

// Formularios de los demos en vivo (QAP-18): al enviar, el botón se desactiva y avisa que está generando
// (la respuesta del proveedor puede tardar unos segundos). Sin JS el formulario funciona igual.
document.querySelectorAll("form[data-live-form]").forEach(function (form) {
  form.addEventListener("submit", function () {
    var button = form.querySelector("button[type=submit]");
    if (!button) return;
    button.disabled = true;
    button.textContent = form.dataset.busy || button.textContent;
  });
});

// Tras enviar un demo en vivo, la página se recarga con el resultado más abajo: se lleva la vista hasta él
// (el ancla de la URL no basta aquí porque el desplazamiento ocurre dentro del contenedor de la página).
(function () {
  var result = document.querySelector("[data-live-result]");
  if (result) result.scrollIntoView({ block: "start", behavior: "instant" });  // sin animación: la página acaba de cargar
})();
