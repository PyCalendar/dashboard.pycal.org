// The editor of the message saves the edited message while it is written: a moment after
// typing, and when the field is left. Apply then says Applied, in green, when the edited
// message is the current one. Without JavaScript, Save and Apply do the same with a new page.
(function () {
  "use strict";
  var form = document.querySelector("form[data-message-editor]");
  if (!form) { return; }
  var status = form.querySelector("[data-save-status]");
  var save = form.querySelector("[data-save-draft]");
  var apply = document.querySelector("[data-apply]");
  var token = form.querySelector("input[name=csrfmiddlewaretoken]");
  var timer = null;
  var saving = false;
  var again = false;
  if (save) { save.hidden = true; }
  status.hidden = false;
  function show(state) {
    status.dataset.state = state;
    status.textContent = state === "saving" ? status.dataset.saving
      : state === "saved" ? "✓ " + status.dataset.saved : status.dataset.failed;
  }
  function applied(yes) {  // the button Apply, or Applied in green
    if (!apply) { return; }
    apply.disabled = yes;
    apply.classList.toggle("button-success", yes);
    apply.toggleAttribute("data-applied", yes);
    apply.textContent = yes ? "✓ " + apply.dataset.appliedText : apply.dataset.applyText;
  }
  function send(leave) {
    clearTimeout(timer);
    if (saving) { again = true; return; }
    saving = true;
    show("saving");
    fetch(form.action || window.location.pathname, {
      method: "POST", body: new FormData(form), credentials: "same-origin", keepalive: leave === true,
      headers: {"X-CSRFToken": token ? token.value : "", "Accept": "application/json"}
    })
      .then(function (answer) { return answer.ok ? answer.json() : Promise.reject(answer); })
      .then(function (found) { show("saved"); applied(found.applied); })
      .catch(function () { show("failed"); timer = setTimeout(send, 5000); })
      .finally(function () {
        saving = false;
        if (again) { again = false; send(); }
      });
  }
  function later() {
    show("saving");
    applied(false);
    clearTimeout(timer);
    timer = setTimeout(send, 800);
  }
  form.addEventListener("input", later);
  form.addEventListener("change", send);
  form.addEventListener("click", function (event) {
    if (event.target.closest("markdown-toolbar")) { later(); }
  });
  form.addEventListener("submit", function (event) { event.preventDefault(); send(); });
  if (apply) {  // the latest text is saved before it is applied
    apply.form.addEventListener("submit", function (event) {
      if (!timer && !saving) { return; }
      event.preventDefault();
      clearTimeout(timer);
      var field = document.createElement("input");
      field.type = "hidden";
      field.name = "template";
      field.value = form.querySelector("[name=template]").value;
      apply.form.appendChild(field);
      apply.form.submit();
    });
  }
  window.addEventListener("pagehide", function () { if (timer) { send(true); } });
  form.dataset.autosaving = "";  // ready
}());
