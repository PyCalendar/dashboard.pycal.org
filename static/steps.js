// The steps of the pull requests: move them in the bar by dragging them or with the arrows,
// without loading the page again; insert variables into the templates; make a filter a step
// on the tab Filters. Without JavaScript, the forms do the same with a new page.
(function () {
  "use strict";
  function token() {
    var field = document.querySelector("input[name=csrfmiddlewaretoken]");
    return field ? field.value : "";
  }
  function post(url, fields) {
    var body = new FormData();
    Object.keys(fields).forEach(function (key) { body.append(key, fields[key]); });
    return fetch(url, {
      method: "POST", body: body, credentials: "same-origin",
      headers: {"X-CSRFToken": token(), "Accept": "application/json"}
    }).then(function (answer) { return answer.ok ? answer : Promise.reject(answer); });
  }

  var bar = document.querySelector("[data-step-bar]");
  function renumber() {
    var items = bar.querySelectorAll("[data-step]");
    items.forEach(function (item, index) {
      var number = item.querySelector(".step-number");
      number.textContent = number.textContent.replace(/\d+/, String(index + 1));
      var left = item.querySelector("button[value=left]");
      var right = item.querySelector("button[value=right]");
      if (left) { left.disabled = index === 0; }
      if (right) { right.disabled = index === items.length - 1; }
    });
  }
  function moveTo(item, to) {
    var items = Array.prototype.slice.call(bar.querySelectorAll("[data-step]"));
    var from = items.indexOf(item);
    if (to === from || to < 0 || to >= items.length) { return; }
    post(item.dataset.move, {to: String(to)}).then(function () {
      items.splice(from, 1);
      items.splice(to, 0, item);
      items.forEach(function (each) { bar.appendChild(each); });
      renumber();
    }).catch(function () { window.location.reload(); });
  }
  if (bar) {
    var dragged = null;
    bar.querySelectorAll("[data-step][data-move]").forEach(function (item) {
      item.querySelectorAll("button[name=direction]").forEach(function (button) {
        button.addEventListener("click", function (event) {
          event.preventDefault();
          var items = Array.prototype.slice.call(bar.querySelectorAll("[data-step]"));
          moveTo(item, items.indexOf(item) + (button.value === "left" ? -1 : 1));
        });
      });
      item.addEventListener("dragstart", function (event) {
        dragged = item;
        event.dataTransfer.effectAllowed = "move";
        event.dataTransfer.setData("text/plain", item.dataset.step);
      });
      item.addEventListener("dragover", function (event) {
        if (dragged) { event.preventDefault(); item.classList.add("dragged-over"); }
      });
      item.addEventListener("dragleave", function () { item.classList.remove("dragged-over"); });
      item.addEventListener("drop", function (event) {
        event.preventDefault();
        item.classList.remove("dragged-over");
        if (!dragged || dragged === item) { return; }
        var items = Array.prototype.slice.call(bar.querySelectorAll("[data-step]"));
        moveTo(dragged, items.indexOf(item));
        dragged = null;
      });
    });
  }

  // a step saves itself while it is edited: a moment after typing, and when a field is left
  var form = document.querySelector("[data-edit-step]");
  if (form) {
    var button = form.querySelector("[data-save-step]");
    var status = form.querySelector("[data-save-status]");
    var timer = null;
    var saving = false;
    var again = false;
    var pending = false;  // a change waits to be saved
    var name = document.querySelector("[data-step-bar] .current .step-name");
    button.hidden = true;
    status.hidden = false;
    function show(state) {
      status.dataset.state = state;
      status.textContent = state === "saving" ? status.dataset.saving
        : state === "saved" ? "✓ " + status.dataset.saved : status.dataset.failed;
    }
    function save() {
      clearTimeout(timer);
      if (saving) { again = true; return; }
      saving = true;
      pending = false;
      show("saving");
      var body = new FormData(form);
      fetch(form.action, {
        method: "POST", body: body, credentials: "same-origin", keepalive: true,
        headers: {"X-CSRFToken": token(), "Accept": "application/json"}
      })
        .then(function (answer) { return answer.ok ? answer.json() : Promise.reject(answer); })
        .then(function (step) {
          if (name) { name.textContent = step.name; }
          var box = bar && bar.querySelector('[data-step="' + step.step + '"] .step-box');
          if (box && step.color) { box.style.setProperty("--step-color", step.color); }
          if (box && !step.color) { box.removeAttribute("style"); }  // its color, at once
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
    form.addEventListener("submit", function (event) { event.preventDefault(); save(); });
    window.addEventListener("pagehide", function () { if (pending) { save(); } });
  }

  // the tab Filters: a filter becomes a step without a new page
  document.querySelectorAll("form[data-make-step]").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      post(form.action, {filter: form.querySelector("[name=filter]").value})
        .then(function (answer) { return answer.json(); })
        .then(function (step) {
          var link = document.createElement("a");
          link.className = "button button-quiet";
          link.href = step.url;
          link.dataset.stepLink = "";
          link.textContent = form.dataset.madeText.replace("%(name)s", step.name);
          form.replaceWith(link);
        })
        .catch(function () { form.submit(); });
    });
  });
}());
