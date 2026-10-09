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
