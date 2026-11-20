// The tab PR Message: the preview follows the editor (the message as a pull request gets it,
// its Markdown, and how many get it); the tabs Message and Markdown switch the preview.
(function () {
  "use strict";
  var box = document.querySelector("[data-message-preview]");
  if (!box) { return; }
  var rendered = box.querySelector("[data-message-rendered]");
  var markdown = box.querySelector("[data-message-markdown]");
  var pull = box.querySelector("[data-message-pull]");
  var showRendered = box.querySelector("[data-show-rendered]");
  var showMarkdown = box.querySelector("[data-show-markdown]");
  function show(source) {
    rendered.hidden = source;
    markdown.hidden = !source;
    showRendered.setAttribute("aria-selected", String(!source));
    showMarkdown.setAttribute("aria-selected", String(source));
  }
  showRendered.addEventListener("click", function () { show(false); });
  showMarkdown.addEventListener("click", function () { show(true); });
  var form = document.querySelector("[data-message-form]");
  if (!form) { return; }
  var button = form.querySelector("[data-save-message]");
  var timer = null;
  function refresh() {
    fetch(form.dataset.preview, {
      method: "POST",
      body: new FormData(form),
      credentials: "same-origin",
      headers: {"Accept": "application/json"}
    })
      .then(function (answer) { return answer.ok ? answer.json() : Promise.reject(answer); })
      .then(function (found) {
        rendered.innerHTML = found.html;  // cleaned by the site (nh3)
        markdown.textContent = found.markdown;
        button.textContent = found.button;
        if (found.pull) { pull.textContent = pull.dataset.as.replace("%(pull)s", found.pull); }
      })
      .catch(function () {});
  }
  function later() { clearTimeout(timer); timer = setTimeout(refresh, 400); }
  form.addEventListener("input", later);
  form.addEventListener("change", later);
  form.addEventListener("click", function (event) {
    if (event.target.closest("markdown-toolbar, [data-variable]")) { later(); }
  });
}());
