// The scope of the message (the last page of editing it): the button counts the pull requests
// that get the message while the switches change; without JavaScript, the button Count does.
(function () {
  "use strict";
  var form = document.querySelector("[data-message-form]");
  if (!form) { return; }
  var button = form.querySelector("[data-save-message]");
  var count = form.querySelector("[data-count]");
  if (count) { count.hidden = true; }
  var timer = null;
  function refresh() {
    var body = new FormData(form);
    fetch(form.dataset.preview, {
      method: "POST",
      body: body,
      credentials: "same-origin",
      headers: {"Accept": "application/json"}
    })
      .then(function (answer) { return answer.ok ? answer.json() : Promise.reject(answer); })
      .then(function (found) { button.textContent = found.button; })
      .catch(function () {});
  }
  function later() { clearTimeout(timer); timer = setTimeout(refresh, 300); }
  form.addEventListener("input", later);
  form.addEventListener("change", later);
}());
