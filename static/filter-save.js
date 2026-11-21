// A saved filter saves itself while it is edited, like a step: its name, its description and
// which conditions are in force, a moment after typing and when a switch changes. Without
// JavaScript, the button Save does the same with a new page.
(function () {
  "use strict";
  var form = document.querySelector("form[data-save-filter][data-autosave]");
  if (!form) { return; }
  var button = form.querySelector("button[name=save][value=this]");
  var status = form.querySelector("[data-save-status]");
  var token = form.querySelector("input[name=csrfmiddlewaretoken]");
  var timer = null;
  var saving = false;
  var again = false;
  var pending = false;  // a change waits to be saved
  var current = Promise.resolve();  // the last saving
  var leaving = false;  // saved as a new filter: nothing more is saved
  if (button) { button.hidden = true; }
  status.hidden = false;
  function show(state) {
    status.dataset.state = state;
    status.textContent = state === "saving" ? status.dataset.saving
      : state === "saved" ? "✓ " + status.dataset.saved
        : state === "taken" ? status.dataset.taken : status.dataset.failed;
  }
  function post(body) {
    return fetch(form.action || window.location.pathname, {
      method: "POST", body: body, credentials: "same-origin", keepalive: true,
      headers: {"X-CSRFToken": token ? token.value : "", "Accept": "application/json"}
    });
  }
  function save() {
    clearTimeout(timer);
    if (leaving) { return; }
    if (saving) { again = true; return; }
    saving = true;
    pending = false;
    show("saving");
    var body = new FormData(form);
    body.set("save", "this");
    changed = true;
    current = post(body)
      .then(function (answer) {
        if (answer.status === 409) { return {taken: true}; }
        return answer.ok ? answer.json() : Promise.reject(answer);
      })
      .then(function (found) {
        if (found.taken) { show("taken"); return; }
        if (!pending && !again) { show("saved"); }  // a newer change is not saved yet
      })
      .catch(function () { show("failed"); timer = setTimeout(save, 5000); })
      .finally(function () {
        saving = false;
        if (again) { again = false; save(); }
      });
  }
  function later() {  // a change waits a moment for more; it is not saved until then
    show("saving");
    pending = true;
    clearTimeout(timer);
    timer = setTimeout(save, 800);
  }
  form.addEventListener("input", later);
  form.addEventListener("change", save);
  form.addEventListener("click", function (event) {
    // the bar of the editor changes the text without an event of input
    if (event.target.closest("markdown-toolbar")) { later(); }
  });
  form.addEventListener("submit", function (event) {
    // Enter in a field saves this filter; the buttons of the conditions and Save as a new
    // filter go on to their pages
    if (!event.submitter || event.submitter === button) { event.preventDefault(); save(); }
  });
  // a new filter leaves the saved one as it was: what was saved while editing is undone first
  var original = document.querySelector("form[data-original-filter]");
  var changed = false;
  var asNew = form.querySelector("button[name=save][value=new]");
  if (asNew && original) {
    asNew.addEventListener("click", function (event) {
      if (!changed && !pending) { return; }
      event.preventDefault();
      clearTimeout(timer);
      pending = false;
      leaving = true;
      current.catch(function () {})
        .then(function () { return post(new FormData(original)); })
        .finally(function () {
          changed = false;
          form.requestSubmit(asNew);
        });
    });
  }
  window.addEventListener("pagehide", function () { if (pending) { save(); } });
}());
