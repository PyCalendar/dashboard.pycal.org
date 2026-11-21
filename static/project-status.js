// The overview of a project while it updates: every 10 seconds, the box Updating is read again
// and replaced, not the whole page; when the update is done, the box shows a check mark and the
// numbers of the repositories are replaced once. Without JavaScript, the page reloads itself.
(function () {
  "use strict";
  var SECONDS = 10;
  var box = document.querySelector("[data-live-status]");
  if (!box || box.dataset.status !== "updating") { return; }
  function later() { setTimeout(poll, SECONDS * 1000); }
  function poll() {
    fetch(window.location.href, {credentials: "same-origin", headers: {"Accept": "text/html"}})
      .then(function (answer) { return answer.ok ? answer.text() : Promise.reject(answer); })
      .then(function (html) {
        var page = new DOMParser().parseFromString(html, "text/html");
        var fresh = page.querySelector("[data-live-status]");
        var shown = document.querySelector("[data-live-status]");
        if (!fresh || !shown) { later(); return; }
        if (fresh.dataset.status === "updating") {
          shown.replaceWith(fresh);
          later();
          return;
        }
        fresh.setAttribute("data-update-done", "");  // the check mark
        shown.replaceWith(fresh);
        document.querySelectorAll("[data-after-update]").forEach(function (old) {
          var name = old.getAttribute("data-after-update");
          var found = page.querySelector('[data-after-update="' + name + '"]');
          if (found) { old.replaceWith(found); }
        });
      })
      .catch(later);
  }
  later();
}());
