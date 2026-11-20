// The fields of Markdown (data-markdown-field): the bar of the formats, which the vendored
// markdown-toolbar-element runs, and the preview, which the site renders as the page will.
// Without JavaScript, the field is a plain text area.
(function () {
  "use strict";
  function connect(field) {
    var bar = field.querySelector("[data-markdown-bar]");
    var area = field.querySelector("textarea");
    var shown = field.querySelector("[data-markdown-shown]");
    var write = field.querySelector("[data-markdown-write]");
    var preview = field.querySelector("[data-markdown-preview]");
    var token = document.querySelector("input[name=csrfmiddlewaretoken]");
    function mode(previewing) {
      area.hidden = previewing;
      shown.hidden = !previewing;
      write.setAttribute("aria-pressed", String(!previewing));
      preview.setAttribute("aria-pressed", String(previewing));
    }
    write.addEventListener("click", function () { mode(false); area.focus(); });
    preview.addEventListener("click", function () {
      var body = new FormData();
      body.append("text", area.value);
      fetch(preview.dataset.markdownPreview, {
        method: "POST",
        body: body,
        credentials: "same-origin",
        headers: {"X-CSRFToken": token ? token.value : ""}
      })
        .then(function (answer) { return answer.ok ? answer.text() : ""; })
        .then(function (html) {
          shown.innerHTML = html;  // cleaned by the site (nh3)
          mode(true);
        })
        .catch(function () {});
    });
    // the menu Variables: a click inserts the variable where the cursor is, and closes it
    var menu = field.querySelector("[data-variables-menu]");
    if (menu) {
      menu.querySelectorAll("[data-variable]").forEach(function (item) {
        item.addEventListener("click", function () {
          var text = item.dataset.variable;
          var start = area.selectionStart === undefined ? area.value.length : area.selectionStart;
          var end = area.selectionEnd === undefined ? start : area.selectionEnd;
          area.value = area.value.slice(0, start) + text + area.value.slice(end);
          menu.open = false;
          mode(false);
          area.dispatchEvent(new Event("input", {bubbles: true}));  // as if typed
          area.focus();
          area.selectionStart = area.selectionEnd = start + text.length;
        });
      });
    }
    bar.hidden = false;
    field.dataset.markdownConnected = "";
  }
  document.querySelectorAll("[data-markdown-field]").forEach(connect);
}());
